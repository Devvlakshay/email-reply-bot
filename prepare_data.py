import json
import re
import os

# Configuration
INPUT_FILE = "emails.txt"
OUTPUT_FILE = "knowledge_base.json"

def clean_text(text):
    """Removes extra whitespace."""
    return text.strip()

def extract_topic_from_body(full_email):
    """
    Extracts the middle part of the email (removing greeting/sign-off)
    to serve as the search topic.
    """
    lines = full_email.split('\n')
    core_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Filter out generic greetings and sign-offs to find the "Meat" of the email
        if (not stripped or 
            "Dear User" in stripped or 
            "Thanks," in stripped or 
            "Qoneqt Support Team" in stripped or 
            "*" in stripped):
            continue
        core_lines.append(stripped)
    
    return " ".join(core_lines)

def process_raw_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: '{INPUT_FILE}' not found. Please create it and paste your emails.")
        return

    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Split emails by the separator line (10 or more stars)
    email_blocks = re.split(r'\*{10,}', raw_content)

    knowledge_base = []

    for block in email_blocks:
        clean_block = clean_text(block)
        
        # Skip empty blocks (often happens at start/end of file)
        if len(clean_block) < 10:
            continue

        # Create a search topic automatically
        topic = extract_topic_from_body(clean_block)
        
        entry = {
            "topic": topic,      # RAG searches this
            "reply": clean_block # AI reads this style
        }
        
        knowledge_base.append(entry)

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=4)

    print(f"Processed {len(knowledge_base)} emails.")
    print(f"Saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    process_raw_data()