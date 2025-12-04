import json
import os
# Use Community version for stability
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

DATA_FILE = "knowledge_base.json"
DB_PATH = "vector_store"

def build_brain():
    if not os.path.exists(DATA_FILE):
        print("❌ Error: Run prepare_data.py first.")
        return

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    documents = []
    for entry in data:
        # Context for search: Topic + Full Text
        text = f"Topic: {entry['topic']}\nFull Template: {entry['reply']}"
        doc = Document(page_content=text, metadata={"reply": entry['reply']})
        documents.append(doc)

    print("🧠 Embedding data (CPU Local)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(DB_PATH)
    print(f"✅ Brain saved to '{DB_PATH}'")

if __name__ == "__main__":
    build_brain()