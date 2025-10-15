"""
Slack Webhook Onboarding Email Service

A simplified Flask app that receives webhook data from Slack and sends onboarding emails.

Deployment Instructions for Render:
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following environment variables in Render dashboard:
   - GMAIL_USER: your Gmail address
   - GMAIL_PASS: your Gmail app password (not your regular password)
   - PORT: 5000 (or let Render auto-assign)
4. Set Build Command: pip install -r requirements.txt
5. Set Start Command: python webhook_app.py
6. Deploy!

Author: AI Assistant
Version: 2.0.0 - Webhook Version
"""

import os
import re
import threading
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
PORT = int(os.getenv('PORT', 5000))

# Validate required environment variables
if not all([GMAIL_USER, GMAIL_PASS]):
    raise ValueError("Missing required environment variables. Please check GMAIL_USER and GMAIL_PASS")

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


def parse_name_email(text):
    """
    Parse the text parameter to extract name and email.
    Expected format: "John Doe john@example.com"
    
    Args:
        text (str): The text from webhook
        
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


def send_email(name, email):
    """
    Send onboarding email via Gmail SMTP.
    
    Args:
        name (str): Recipient's name
        email (str): Recipient's email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
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


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok"})


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle webhook requests from Slack.
    Expects JSON data with 'text' field containing "name email"
    """
    try:
        log_request("WEBHOOK_RECEIVED", f"Headers: {dict(request.headers)}")
        
        # Get JSON data
        data = request.get_json()
        log_request("WEBHOOK_DATA", f"Data: {data}")
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Extract text from webhook data
        text = data.get('text', '')
        if not text:
            return jsonify({"error": "No text field in webhook data"}), 400
        
        # Parse name and email from text
        name, email = parse_name_email(text)
        
        if not name or not email:
            log_request("INVALID_FORMAT", f"Text: {text}")
            return jsonify({"error": "Invalid format. Expected: 'John Doe john@example.com'"}), 400
        
        # Validate email format
        if not validate_email_format(email):
            log_request("INVALID_EMAIL", f"Email: {email}")
            return jsonify({"error": f"Invalid email format: {email}"}), 400
        
        # Send onboarding email
        if send_email(name, email):
            success_message = f"✅ Onboarding email sent to {name} ({email})"
            log_request("WEBHOOK_SUCCESS", f"Email sent to {name} ({email})")
            return jsonify({"message": success_message})
        else:
            log_request("WEBHOOK_FAILED", f"Email send failed for {name} ({email})")
            return jsonify({"error": f"Failed to send email to {name} ({email})"}), 500
            
    except Exception as e:
        log_request("WEBHOOK_ERROR", f"Error: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/test', methods=['POST'])
def test_webhook():
    """
    Test endpoint for webhook functionality.
    """
    try:
        data = request.get_json()
        return jsonify({
            "status": "success",
            "received_data": data,
            "message": "Webhook endpoint is working!"
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
    print("🚀 Starting Slack Webhook Onboarding Email Service")
    print("=" * 60)
    print(f"📧 Gmail User: {GMAIL_USER}")
    print(f"🌐 Port: {PORT}")
    print(f"👥 Multi-user support: ✅ Enabled")
    print(f"🔄 Unlimited requests: ✅ No rate limiting")
    print(f"📊 Monitoring: ✅ /health endpoint")
    print(f"🔒 Thread-safe SMTP: ✅ Enabled")
    print("=" * 60)
    print("Ready to handle webhook requests!")
    print("=" * 60)
    
    # Debug environment variables
    print("DEBUG: Environment variables check:")
    print(f"DEBUG: GMAIL_USER set: {bool(GMAIL_USER)}")
    print(f"DEBUG: GMAIL_PASS set: {bool(GMAIL_PASS)}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=True, threaded=True)
