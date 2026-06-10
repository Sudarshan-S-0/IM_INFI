import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

def send_gmail_notification(config: dict, subject: str, body_text: str, is_html: bool = False) -> bool:
    """Sends a notification email via SMTP/Gmail."""
    gmail_settings = config.get("gmail_settings", {})
    if not gmail_settings.get("enabled", False):
        logger.info("Gmail notifier is disabled.")
        return False
        
    import os
    smtp_server = gmail_settings.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(gmail_settings.get("smtp_port", 587))
    sender = os.environ.get("SENDER_EMAIL", gmail_settings.get("sender_email"))
    password = os.environ.get("SENDER_PASSWORD", gmail_settings.get("sender_password"))
    receiver = os.environ.get("RECEIVER_EMAIL", gmail_settings.get("receiver_email"))
    
    if not sender or sender == "YOUR_EMAIL@gmail.com" or not password or password == "YOUR_APP_PASSWORD" or not receiver or receiver == "RECIPIENT_EMAIL@gmail.com":
        logger.warning("Gmail SMTP credentials not set up. Skipping email notification.")
        return False
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    
    mime_type = "html" if is_html else "plain"
    msg.attach(MIMEText(body_text, mime_type))
    
    try:
        logger.info(f"Sending email notification to {receiver} via {smtp_server}:{smtp_port}")
        # Connect to server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()  # Upgrade connection to secure TLS
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        logger.info("Email notification sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False
