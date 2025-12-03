import json
import os
import shutil
# Using the stable Community version for HuggingFace
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Configuration
DATA_SOURCE = "knowledge_base.json"
DB_PATH = "vector_store"

def ingest_data():
    if not os.path.exists(DATA_SOURCE):
        print(f"Error: {DATA_SOURCE} not found. Run prepare_data.py first.")
        return

    print("🔄 Loading knowledge base...")
    with open(DATA_SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for entry in data:
        # We combine Topic + Reply so the search finds the right context
        text_content = f"Topic: {entry['topic']}\nFull Email: {entry['reply']}"
        doc = Document(page_content=text_content, metadata={"reply": entry['reply']})
        documents.append(doc)

    print(f" Embedding {len(documents)} records (running locally)...")
    
    # Initialize Local Embeddings (Free, No API limit)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Create and Save Vector DB
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(DB_PATH)
    
    print(f"Success: Vector Database saved to '{DB_PATH}/'")

if __name__ == "__main__":
    ingest_data()