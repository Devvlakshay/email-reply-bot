import asyncio
import os
import sys
import time
import logging
from dotenv import load_dotenv

# Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

load_dotenv()

# Settings
VECTOR_DB_PATH = "vector_store"
MODEL_NAME = "gemini-2.5-flash-lite"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class QoneqtSupportBot:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vector_db = self._load_vector_db()

    def _load_vector_db(self):
        if not os.path.exists(VECTOR_DB_PATH):
            logging.error("Vector DB not found. Did you run ingest.py?")
            return None
        return FAISS.load_local(VECTOR_DB_PATH, self.embeddings, allow_dangerous_deserialization=True)

    def get_relevant_policy(self, query_text):
        if not self.vector_db: return ""
        try:
            # RAG Search
            docs = self.vector_db.similarity_search(query_text, k=2)
            return "\n".join([f"- {doc.page_content}" for doc in docs])
        except Exception as e:
            logging.error(f"RAG Error: {e}")
            return ""

    def generate_email_reply(self, user_query, policy_context):
        llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.3)
        
        # STRICT FORMATTING PROMPT
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
            response = chain.invoke({"user_query": user_query, "context": policy_context})
            return response.content
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return "Error generating reply."

async def run_bot_service():
    logging.info("Starting Qoneqt Support Bot...")
    bot = QoneqtSupportBot()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        env=os.environ
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logging.info("Connected to Gmail via MCP.")

            while True:
                logging.info("Checking inbox...")
                
                # 1. Fetch Email
                try:
                    result = await session.call_tool("fetch_unread_email", arguments={})
                    email_data = result.content[0].text
                except Exception as e:
                    logging.error(f"Connection lost: {e}")
                    time.sleep(10)
                    continue

                if "No unread emails" in email_data:
                    logging.info("Inbox empty. Sleeping for 15s...")
                    time.sleep(15)
                    continue

                # 2. Parse Email
                try:
                    lines = email_data.split("\n")
                    sender = lines[0].replace("SENDER: ", "").strip()
                    subject = lines[1].replace("SUBJECT: ", "").strip()
                    body_content = "\n".join(lines[2:]).replace("BODY: ", "")
                    logging.info(f"New Email from: {sender} | Subject: {subject}")
                except:
                    logging.warning("Skipping email due to parse error.")
                    continue

                policy_context = bot.get_relevant_policy(body_content)
                reply_body = bot.generate_email_reply(body_content, policy_context)

                logging.info("Draft generated. Sending...")

                # 4. Send Reply
                send_result = await session.call_tool(
                    "send_email_reply",
                    arguments={
                        "to_email": sender,
                        "subject": f"Re: {subject}",
                        "body": reply_body
                    }
                )
                
                logging.info(f"Result: {send_result.content[0].text}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot_service())
    except KeyboardInterrupt:
        logging.info("Bot stopped.")