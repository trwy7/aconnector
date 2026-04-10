import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from app import app, logger

emailids = {}
emailconfig = {
    "server": os.environ.get("EMAIL_HOST", "smtp.gmail.com"),
    "port": os.environ.get("EMAIL_PORT", 587),
    "username": os.environ.get("EMAIL_USERNAME"),
    "password": os.environ.get("EMAIL_PASSWORD"),
    "from": os.environ.get("EMAIL_FROM"),
}

def send(email, subject, content):
    logger.info("[email] Sending email to %s with subject %s", email, subject)
    if not emailconfig['password']:
        logger.warning("[email] No email account was provided, email to '%s' with subject '%s': %s", email, subject, content)
        return False
    msg = MIMEMultipart() # This part cannot be tested without an email server, so we skip it when testing
    msg['From'] = f"{app.config['NAME']} <{emailconfig['from']}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(content, 'plain'))
    with smtplib.SMTP(emailconfig["server"], emailconfig["port"]) as server:
        server.starttls()
        server.login(emailconfig["username"], emailconfig["password"])
        server.sendmail(emailconfig["from"], email, msg.as_string())
    logger.info("[email] Email sent.")
    return True