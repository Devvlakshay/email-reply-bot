import imaplib
import smtplib
import email
import os
from email.message import EmailMessage
from email.utils import parseaddr
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from email.header import decode_header

load_dotenv()

# Initialize MCP
mcp = FastMCP("Gmail_Server")

def clean_text(text):
    if not text: return ""
    return text.strip()

def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            # Get text/plain parts only, ignore attachments
            if content_type == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                try:
                    body = part.get_payload(decode=True).decode()
                except: pass
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except: pass
    return body

@mcp.tool()
def fetch_unread_email() -> str:
    """Fetches the latest unread email from Inbox."""
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_pass = os.getenv("IMAP_PASS")

    if not imap_pass:
        return "Error: IMAP Credentials missing in .env"

    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        mail.select("inbox")

        # Search for UNSEEN emails
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            return "No unread emails found."

        # Fetch the most recent one
        latest_id = email_ids[-1]
        status, msg_data = mail.fetch(latest_id, "(RFC822)")
        
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Extract Sender
        from_header = msg["From"]
        sender_name, sender_email = parseaddr(from_header)

        # Extract Subject
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")

        # Extract Body
        body = get_email_body(msg)

        mail.close()
        mail.logout()

        # Return structured string for the Bot to parse
        return f"SENDER: {sender_email}\nSUBJECT: {subject}\nBODY: {clean_text(body)}"

    except Exception as e:
        return f"Error fetching email: {str(e)}"

@mcp.tool()
def send_email_reply(to_email: str, subject: str, body: str) -> str:
    """Sends a reply via SMTP."""
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    user = os.getenv("IMAP_USER")
    password = os.getenv("IMAP_PASS")

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        
        return f"Successfully sent email to {to_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

if __name__ == "__main__":
    mcp.run()