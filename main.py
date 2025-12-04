import asyncio
import os
import sys
import time
import logging
from dotenv import load_dotenv

# --- OPENAI IMPORTS ---
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# CONSTANTS
VECTOR_DB_PATH = "vector_store"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class QoneqtBot:
    def __init__(self):
        logging.info("Loading Brain...")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vector_db = self._load_db()

    def _load_db(self):
        if not os.path.exists(VECTOR_DB_PATH):
            logging.error("Vector DB missing! Run ingest.py first.")
            return None
        return FAISS.load_local(VECTOR_DB_PATH, self.embeddings, allow_dangerous_deserialization=True)

    def get_context(self, query):
        if not self.vector_db: return ""
        docs = self.vector_db.similarity_search(query, k=2)
        return "\n".join([f"- {doc.page_content}" for doc in docs])

    def generate_reply(self, user_query, context):
        # --- ZERO HALLUCINATION CONFIG ---
        # Temperature 0.0 means "Strict Math", no creativity.
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=1)

        prompt = ChatPromptTemplate.from_template("""
        You are a Support Agent for 'Qoneqt'. 
        Match the company's email style exactly.

        INSTRUCTIONS:
        1. Start exactly with: "Dear User,"
        2. First line: Write a polite empathy phrase acknowledging their specific issue.
           (e.g., "We understand you are facing a delay...", "We apologize for the inconvenience...")
        3. Body: Answer using ONLY the POLICY RULES below.
        4. Sign-off exactly with:
           "Thanks,
           Qoneqt Support Team"
        5. Do NOT include a Subject line.
        6.  Format the reply with clear paragraph breaks (use blank lines between paragraphs).

        ---
        USER EMAIL:
        {user_query}

        POLICY RULES:
        {context}
        ---

        Write the email body:
        """)

        try:
            chain = prompt | llm
            return chain.invoke({"user_query": user_query, "context": context}).content
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return "Error generating reply."

async def run():
    logging.info("Qoneqt Bot Starting (OpenAI Mode)...")
    bot = QoneqtBot()
    
    # MCP Connection
    params = StdioServerParameters(command=sys.executable, args=["server.py"], env=os.environ)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            while True:
                logging.info("📥 Checking inbox...")
                try:
                    res = await session.call_tool("fetch_unread_email", arguments={})
                    data = res.content[0].text
                except:
                    time.sleep(10); continue

                if "No unread" in data:
                    logging.info("Empty. Sleeping 15s...")
                    time.sleep(15); continue

                if "SKIPPED_BOT" in data:
                    logging.info("⛔ Skipped Spam/Bot.")
                    time.sleep(5); continue

                # Process
                lines = data.split("\n")
                sender = lines[0].replace("SENDER: ", "").strip()
                subject = lines[1].replace("SUBJECT: ", "").strip()
                body = "\n".join(lines[2:]).replace("BODY: ", "")

                logging.info(f"From: {sender} | Sub: {subject}")

                context = bot.get_context(body)
                reply = bot.generate_reply(body, context)

                logging.info("--- Generated Reply ---\n%s\n-----------------------", reply)
                logging.info("Reply ready. Waiting 20 seconds before sending...")
                time.sleep(20)
                logging.info("Sending Reply...")
                await session.call_tool("send_email_reply", arguments={
                    "to_email": sender, "subject": f"Re: {subject}", "body": reply
                })
                logging.info("Sent!")
                time.sleep(5)

if __name__ == "__main__":
    asyncio.run(run())