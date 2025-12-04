import imaplib
import smtplib
import email
import os
from email.message import EmailMessage
from email.utils import parseaddr
from email.header import decode_header
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("Gmail_Server")

# SECURITY: Blocklist
BLOCKED_KEYWORDS = ["subscribe", "newsletter", "alert", "security", "marketing"]
BLOCKED_SENDERS = ["no-reply", "noreply", "mailer-daemon", "postmaster", "bounce"]

def clean_text(text):
    return text.strip() if text else ""

def is_safe(msg, sender, subject):
    # 1. Block Sender Patterns
    if any(b in sender.lower() for b in BLOCKED_SENDERS): return False
    # 2. Block Subject Keywords
    if any(b in subject.lower() for b in BLOCKED_KEYWORDS): return False
    # 3. Block Auto-Replies
    if "auto-generated" in msg.get("Auto-Submitted", "").lower(): return False
    return True

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                try: return part.get_payload(decode=True).decode()
                except: pass
    else:
        try: return msg.get_payload(decode=True).decode()
        except: pass
    return ""

@mcp.tool()
def fetch_unread_email() -> str:
    host, user, pwd = os.getenv("IMAP_HOST"), os.getenv("IMAP_USER"), os.getenv("IMAP_PASS")
    if not pwd: return "Error: Missing credentials"

    try:
        mail = imaplib.IMAP4_SSL(host)
        mail.login(user, pwd)
        mail.select("inbox")
        
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()
        if not email_ids: return "No unread emails"

        latest_id = email_ids[-1]
        _, msg_data = mail.fetch(latest_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        # Parse Info
        from_hdr = msg["From"]
        _, sender_email = parseaddr(from_hdr)
        
        subj_hdr = msg["Subject"] or ""
        decoded_list = decode_header(subj_hdr)
        subject = "".join([str(t[0].decode(t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0]) for t in decoded_list])

        # SECURITY CHECK
        if not is_safe(msg, sender_email, subject):
            return f"SKIPPED_BOT: {sender_email}"

        body = get_body(msg)
        mail.close()
        mail.logout()

        return f"SENDER: {sender_email}\nSUBJECT: {subject}\nBODY: {clean_text(body)}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def send_email_reply(to_email: str, subject: str, body: str) -> str:
    smtp_host = "smtp.gmail.com"
    user, pwd = os.getenv("IMAP_USER"), os.getenv("IMAP_PASS")

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        msg["Auto-Submitted"] = "auto-replied" # Marks as bot

        server = smtplib.SMTP(smtp_host, 587)
        server.starttls()
        server.login(user, pwd)
        server.send_message(msg)
        server.quit()
        return f"Sent to {to_email}"
    except Exception as e:
        return f"Failed: {e}"

if __name__ == "__main__":
    mcp.run()