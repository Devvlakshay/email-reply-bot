import json
import re
import os

INPUT_FILE = "emails.txt"
OUTPUT_FILE = "knowledge_base.json"

def clean_text(text):
    return text.strip()

def extract_topic(full_email):
    """Extracts the middle part of the email as the search topic."""
    lines = full_email.split('\n')
    core_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove generic greetings/sign-offs to find the unique content
        if (not stripped or "Dear User" in stripped or "Thanks," in stripped or "Qoneqt Support Team" in stripped or "*" in stripped):
            continue
        core_lines.append(stripped)
    return " ".join(core_lines)

def process_data():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Split by separator (10+ stars)
    blocks = re.split(r'\*{10,}', raw_content)
    knowledge_base = []

    for block in blocks:
        clean_block = clean_text(block)
        if len(clean_block) < 10: continue

        entry = {
            "topic": extract_topic(clean_block),
            "reply": clean_block
        }
        knowledge_base.append(entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=4)
    
    print(f"✅ Processed {len(knowledge_base)} templates into {OUTPUT_FILE}")

if __name__ == "__main__":
    process_data()