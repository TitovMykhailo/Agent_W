"""
gmail.py - send email and check replies through Gmail
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import CONFIG


def _gmail_credentials() -> tuple[str, str]:
    address = CONFIG.get("GMAIL_ADDRESS", "").strip()
    # Gmail displays app passwords in groups of 4 characters, but SMTP/IMAP
    # requires one continuous 16-character password.
    app_password = "".join(CONFIG.get("GMAIL_APP_PASSWORD", "").split())
    return address, app_password


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email through Gmail SMTP."""
    gmail_address, app_password = _gmail_credentials()
    try:
        msg = MIMEMultipart()
        msg["From"]    = gmail_address
        msg["To"]      = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, app_password)
            server.send_message(msg)

        print(f"   ✅ Email sent → {to_address}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(
            f"   ❌ Email failed → {to_address}: Gmail auth failed. "
            "Check GMAIL_ADDRESS and a current 16-character App Password."
        )
        return False
    except Exception as e:
        print(f"   ❌ Email failed → {to_address}: {e}")
        return False


def check_replies() -> list:
    """Check the inbox and return unread messages."""
    replies = []
    gmail_address, app_password = _gmail_credentials()
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_address, app_password)
        mail.select("INBOX")

        _, data = mail.search(None, "UNSEEN")
        for num in data[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            replies.append({
                "from":    msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "date":    msg.get("Date", ""),
            })

        print(f"   📨 Replies found: {len(replies)}")
    except imaplib.IMAP4.error:
        print(
            "   ⚠️  IMAP auth failed. Check GMAIL_ADDRESS and a current "
            "16-character Gmail App Password. Google revokes app passwords "
            "after account password changes."
        )
    except Exception as e:
        print(f"   ⚠️  IMAP error: {e}")
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass
    return replies
