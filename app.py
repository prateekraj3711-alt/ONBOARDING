"""
Slack Bot Onboarding Email Service

A production-ready Flask app that responds to Slack bot mentions and sends onboarding emails.

Usage: @onboarding-bot John Doe john@example.com

Deployment Instructions for Render:
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following environment variables in Render dashboard:
   - GMAIL_USER: your Gmail address
   - GMAIL_PASS: your Gmail app password (not your regular password)
   - SLACK_BOT_TOKEN: your Slack bot token (starts with xoxb-)
   - SLACK_SIGNING_SECRET: your Slack app's signing secret
   - PORT: 5000 (or let Render auto-assign)
4. Set Build Command: pip install -r requirements.txt
5. Set Start Command: python app.py
6. Deploy!

Author: AI Assistant
Version: 1.0.0
"""

import os
import re
import hmac
import hashlib
import time
import threading
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import json

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASS = os.getenv('GMAIL_PASS')
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
PORT = int(os.getenv('PORT', 5000))

# Validate required environment variables
if not all([GMAIL_USER, GMAIL_PASS, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET]):
    raise ValueError("Missing required environment variables. Please check GMAIL_USER, GMAIL_PASS, SLACK_BOT_TOKEN, and SLACK_SIGNING_SECRET")

# SMTP connection pool for better concurrency handling
smtp_lock = threading.Lock()


def log_request(action, details=""):
    """
    Log request with timestamp for tracking.
    
    Args:
        action (str): Action being performed
        details (str): Additional details
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Action: {action} | {details}")


def verify_slack_request(request_data, timestamp, signature):
    """
    Verify that the request is actually from Slack using the signing secret.
    """
    if not all([request_data, timestamp, signature]):
        return False
    
    # Check if timestamp is within 5 minutes (300 seconds) to prevent replay attacks
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > 300:
        return False
    
    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{request_data}"
    
    # Create the expected signature
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


def parse_name_email(text):
    """
    Parse the text parameter to extract name and email.
    Handles both plain text and Slack's mailto format.
    """
    if not text or not text.strip():
        return None, None
    
    # Remove bot mention from text first
    mention_pattern = r'<@[A-Z0-9]+>\s*'
    clean_text = re.sub(mention_pattern, '', text).strip()
    
    # Handle Slack's mailto format: <mailto:email@domain.com|email@domain.com>
    mailto_pattern = r'<mailto:([^|>]+)\|[^>]+>'
    mailto_match = re.search(mailto_pattern, clean_text)
    
    if mailto_match:
        email = mailto_match.group(1)
        # Remove the mailto part to get the name
        name_text = re.sub(mailto_pattern, '', clean_text).strip()
        name = name_text if name_text else None
        return name, email
    
    # Fallback to original parsing for plain text
    parts = clean_text.split()
    
    if len(parts) < 2:
        return None, None
    
    # Find the email (last part that looks like an email)
    email = None
    name_parts = []
    
    for part in reversed(parts):
        if '@' in part and '.' in part:
            email = part
            break
        name_parts.insert(0, part)
    
    if not email:
        return None, None
    
    name = ' '.join(name_parts) if name_parts else None
    
    return name, email


def validate_email_format(email):
    """
    Validate email format using email-validator library.
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def send_email(name, email):
    """
    Send onboarding email via Gmail SMTP.
    """
    try:
        log_request("SENDING_EMAIL", f"To: {name} ({email})")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Welcome to [Your Company Name]!"
        
        # Email body
        body = f"""Hi {name},

Welcome aboard! We're thrilled to have you with us.

Feel free to reach out if you need any help getting started.

Best,
The Team"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Use thread-safe SMTP connection
        with smtp_lock:
            # Connect to Gmail SMTP server
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()  # Enable TLS encryption
            server.login(GMAIL_USER, GMAIL_PASS)
            
            # Send email
            text = msg.as_string()
            server.sendmail(GMAIL_USER, email, text)
            server.quit()
        
        log_request("EMAIL_SENT_SUCCESS", f"To: {name} ({email})")
        return True
        
    except Exception as e:
        log_request("EMAIL_SEND_FAILED", f"Error: {str(e)} | To: {name} ({email})")
        return False


def send_slack_message(channel, text):
    """
    Send a message to a Slack channel.
    """
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "channel": channel,
            "text": text
        }
        
        response = requests.post(url, headers=headers, json=data)
        log_request("SLACK_MESSAGE_SENT", f"Channel: {channel}, Response: {response.status_code}")
        return response.status_code == 200
        
    except Exception as e:
        log_request("SLACK_MESSAGE_FAILED", f"Error: {str(e)}")
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok"})


@app.route('/events', methods=['POST'])
def events():
    """
    Handle Slack events (mentions, messages, etc.).
    """
    try:
        # Get request data
        request_data = request.get_data(as_text=True)
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')
        
        # Verify Slack request
        if not verify_slack_request(request_data, timestamp, signature):
            log_request("UNAUTHORIZED_REQUEST", "Invalid signature")
            return jsonify({"error": "Unauthorized"}), 401
        
        # Parse JSON data
        data = request.get_json()
        log_request("EVENT_RECEIVED", f"Data: {data}")
        
        # Handle URL verification challenge
        if data.get('type') == 'url_verification':
            return jsonify({"challenge": data.get('challenge')})
        
        # Handle app mention events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            
            if event.get('type') == 'app_mention':
                # Extract text from the mention
                text = event.get('text', '')
                channel = event.get('channel')
                user = event.get('user')
                
                log_request("BOT_MENTIONED", f"Text: {text}, User: {user}, Channel: {channel}")
                
                # Parse name and email (mention removal is handled in parse_name_email)
                name, email = parse_name_email(text)
                
                if not name or not email:
                    response_text = "❌ Invalid format. Please use: `@onboarding-bot John Doe john@example.com`"
                    send_slack_message(channel, response_text)
                    return jsonify({"status": "ok"})
                
                # Validate email format
                if not validate_email_format(email):
                    response_text = f"❌ Invalid email format: {email}"
                    send_slack_message(channel, response_text)
                    return jsonify({"status": "ok"})
                
                # Send onboarding email
                if send_email(name, email):
                    response_text = f"✅ Onboarding email sent to {name} ({email})"
                    send_slack_message(channel, response_text)
                else:
                    response_text = f"❌ Failed to send email to {name} ({email}). Please try again or contact support."
                    send_slack_message(channel, response_text)
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        log_request("EVENT_ERROR", f"Error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/test', methods=['POST'])
def test_bot():
    """
    Test endpoint for bot functionality.
    """
    try:
        data = request.get_json()
        return jsonify({
            "status": "success",
            "received_data": data,
            "message": "Bot endpoint is working!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Starting Slack Bot Onboarding Email Service")
    print("=" * 60)
    print(f"📧 Gmail User: {GMAIL_USER}")
    print(f"🤖 Slack Bot Token: {'*' * len(SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else 'Not set'}")
    print(f"🔐 Slack Signing Secret: {'*' * len(SLACK_SIGNING_SECRET) if SLACK_SIGNING_SECRET else 'Not set'}")
    print(f"🌐 Port: {PORT}")
    print(f"👥 Multi-user support: ✅ Enabled")
    print(f"🔄 Unlimited requests: ✅ No rate limiting")
    print(f"📊 Monitoring: ✅ /health endpoint")
    print(f"🔒 Thread-safe SMTP: ✅ Enabled")
    print("=" * 60)
    print("Ready to handle bot mentions!")
    print("=" * 60)
    
    # Debug environment variables
    print("DEBUG: Environment variables check:")
    print(f"DEBUG: GMAIL_USER set: {bool(GMAIL_USER)}")
    print(f"DEBUG: GMAIL_PASS set: {bool(GMAIL_PASS)}")
    print(f"DEBUG: SLACK_BOT_TOKEN set: {bool(SLACK_BOT_TOKEN)}")
    print(f"DEBUG: SLACK_SIGNING_SECRET set: {bool(SLACK_SIGNING_SECRET)}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=True, threaded=True)
