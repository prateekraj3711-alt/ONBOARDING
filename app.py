"""
Slack Onboarding Email Service

A production-ready Flask app that handles Slack slash commands and sends onboarding emails via Gmail SMTP.

Deployment Instructions for Render:
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following environment variables in Render dashboard:
   - GMAIL_USER: your Gmail address
   - GMAIL_PASS: your Gmail app password (not your regular password)
   - SLACK_SIGNING_SECRET: your Slack app's signing secret
   - PORT: 5000 (or let Render auto-assign)
4. Set Build Command: pip install -r requirements.txt
5. Set Start Command: python app.py
6. Deploy!

For Gmail App Password:
- Enable 2FA on your Google account
- Go to Google Account > Security > App passwords
- Generate a new app password for "Mail"
- Use this password (not your regular Gmail password) for GMAIL_PASS

Author: AI Assistant
Version: 1.0.0
"""

import os
import re
import hmac
import hashlib
import time
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from urllib.parse import parse_qs

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASS = os.getenv('GMAIL_PASS')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
PORT = int(os.getenv('PORT', 5000))

# Validate required environment variables
if not all([GMAIL_USER, GMAIL_PASS, SLACK_SIGNING_SECRET]):
    raise ValueError("Missing required environment variables. Please check GMAIL_USER, GMAIL_PASS, and SLACK_SIGNING_SECRET")

# SMTP connection pool for better concurrency handling
smtp_lock = threading.Lock()


def log_request(user_name, action, details=""):
    """
    Log request with timestamp and user context for better tracking.
    
    Args:
        user_name (str): Slack username
        action (str): Action being performed
        details (str): Additional details
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] User: {user_name} | Action: {action} | {details}")


def verify_slack_request(request_data, timestamp, signature):
    """
    Verify that the request is actually from Slack using the signing secret.
    
    Args:
        request_data (str): The raw request body
        timestamp (str): The X-Slack-Request-Timestamp header
        signature (str): The X-Slack-Signature header
        
    Returns:
        bool: True if the request is verified, False otherwise
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
    Expected format: "John Doe john@example.com"
    
    Args:
        text (str): The text from Slack command
        
    Returns:
        tuple: (name, email) or (None, None) if parsing fails
    """
    if not text or not text.strip():
        return None, None
    
    # Remove extra whitespace and split
    parts = text.strip().split()
    
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
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def send_email(name, email, user_name="unknown"):
    """
    Send onboarding email via Gmail SMTP with improved concurrency handling.
    
    Args:
        name (str): Recipient's name
        email (str): Recipient's email address
        user_name (str): Slack username for logging
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        log_request(user_name, "SENDING_EMAIL", f"To: {name} ({email})")
        
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
        
        log_request(user_name, "EMAIL_SENT_SUCCESS", f"To: {name} ({email})")
        return True
        
    except Exception as e:
        log_request(user_name, "EMAIL_SEND_FAILED", f"Error: {str(e)} | To: {name} ({email})")
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok"})


@app.route('/onboard', methods=['POST'])
def onboard():
    """
    Handle Slack slash command for onboarding.
    Expects form data with 'text' parameter containing "name email"
    Supports multiple concurrent users with unlimited requests per user.
    """
    user_name = "unknown"
    try:
        # Get request data
        request_data = request.get_data(as_text=True)
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')
        
        # Verify Slack request
        if not verify_slack_request(request_data, timestamp, signature):
            log_request("unknown", "UNAUTHORIZED_REQUEST", "Invalid signature")
            return jsonify({
                "response_type": "ephemeral",
                "text": "❌ Unauthorized request. Please contact your administrator."
            }), 401
        
        # Parse form data
        form_data = parse_qs(request_data)
        
        # Extract required fields
        token = form_data.get('token', [''])[0]
        user_name = form_data.get('user_name', [''])[0]
        command = form_data.get('command', [''])[0]
        text = form_data.get('text', [''])[0]
        
        # Log the incoming request
        log_request(user_name, "ONBOARD_REQUEST", f"Command: {command}, Text: {text}")
        
        # Validate required fields
        if not all([token, user_name, command, text]):
            log_request(user_name, "MISSING_PARAMETERS", "Required fields missing")
            return jsonify({
                "response_type": "ephemeral",
                "text": "❌ Missing required parameters. Usage: `/onboard John Doe john@example.com`"
            }), 400
        
        # Parse name and email from text
        name, email = parse_name_email(text)
        
        if not name or not email:
            log_request(user_name, "INVALID_FORMAT", f"Text: {text}")
            return jsonify({
                "response_type": "ephemeral",
                "text": "❌ Invalid format. Please use: `/onboard John Doe john@example.com`"
            }), 400
        
        # Validate email format
        if not validate_email_format(email):
            log_request(user_name, "INVALID_EMAIL", f"Email: {email}")
            return jsonify({
                "response_type": "ephemeral",
                "text": f"❌ Invalid email format: {email}"
            }), 400
        
        # Send onboarding email
        if send_email(name, email, user_name):
            success_message = f"✅ Onboarding email sent to {name} ({email}) by @{user_name}"
            log_request(user_name, "ONBOARD_SUCCESS", f"Email sent to {name} ({email})")
            return jsonify({
                "response_type": "in_channel",
                "text": success_message
            })
        else:
            log_request(user_name, "ONBOARD_FAILED", f"Email send failed for {name} ({email})")
            return jsonify({
                "response_type": "ephemeral",
                "text": f"❌ Failed to send email to {name} ({email}). Please try again or contact support."
            }), 500
            
    except Exception as e:
        log_request(user_name, "UNEXPECTED_ERROR", f"Error: {str(e)}")
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ An unexpected error occurred. Please try again or contact support."
        }), 500


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
    print("🚀 Starting Slack Onboarding Email Service")
    print("=" * 60)
    print(f"📧 Gmail User: {GMAIL_USER}")
    print(f"🔐 Slack Signing Secret: {'*' * len(SLACK_SIGNING_SECRET) if SLACK_SIGNING_SECRET else 'Not set'}")
    print(f"🌐 Port: {PORT}")
    print(f"👥 Multi-user support: ✅ Enabled")
    print(f"🔄 Unlimited requests: ✅ No rate limiting")
    print(f"📊 Monitoring: ✅ /health endpoint")
    print(f"🔒 Thread-safe SMTP: ✅ Enabled")
    print("=" * 60)
    print("Ready to handle multiple concurrent users!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
