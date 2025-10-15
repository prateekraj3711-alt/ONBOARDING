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

# Track processed events to prevent duplicates
processed_events = set()
event_lock = threading.Lock()


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


def parse_slack_message(text):
    """
    Parse the text parameter to extract name, email, and package details.
    Handles both plain text and Slack's mailto format.
    Expected format: @bot John Doe john@example.com Premium Package
    """
    if not text or not text.strip():
        return None, None, None
    
    # Remove bot mention from text first
    mention_pattern = r'<@[A-Z0-9]+>\s*'
    clean_text = re.sub(mention_pattern, '', text).strip()
    
    # Handle Slack's mailto format: <mailto:email@domain.com|email@domain.com>
    mailto_pattern = r'<mailto:([^|>]+)\|[^>]+>'
    mailto_match = re.search(mailto_pattern, clean_text)
    
    if mailto_match:
        email = mailto_match.group(1)
        # Remove the mailto part to get the remaining text
        remaining_text = re.sub(mailto_pattern, '', clean_text).strip()
        
        # Split remaining text to get name and package
        parts = remaining_text.split()
        if len(parts) >= 1:
            # First part(s) are the name, rest is package
            name = parts[0] if len(parts) == 1 else ' '.join(parts[:-1])
            package = parts[-1] if len(parts) > 1 else None
        else:
            name = None
            package = None
        
        return name, email, package
    
    # Fallback to original parsing for plain text
    parts = clean_text.split()
    
    if len(parts) < 2:
        return None, None, None
    
    # Find the email (part that looks like an email)
    email = None
    email_index = -1
    
    for i, part in enumerate(parts):
        if '@' in part and '.' in part:
            email = part
            email_index = i
            break
    
    if not email:
        return None, None, None
    
    # Everything before email is name, everything after is package
    name_parts = parts[:email_index]
    package_parts = parts[email_index + 1:]
    
    name = ' '.join(name_parts) if name_parts else None
    package = ' '.join(package_parts) if package_parts else None
    
    return name, email, package


def validate_email_format(email):
    """
    Validate email format using email-validator library.
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def send_email(name, email, package=None):
    """
    Send onboarding email via Gmail SMTP with multiple port attempts.
    """
    try:
        log_request("SENDING_EMAIL", f"To: {name} ({email}), Package: {package}")
        print(f"DEBUG: Starting email send to {name} ({email}), Package: {package}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Welcome to SpringWorks"
        
        # Email body
        body = f"""Hi {name},

Welcome aboard! We're thrilled to have you with us.

{f"Your package ({package}) is active!" if package else "Your account is now active!"}

Feel free to reach out if you need any help getting started.

Best,
The Team"""
        
        msg.attach(MIMEText(body, 'plain'))
        print(f"DEBUG: Email message created")
        
        # Try different SMTP configurations
        smtp_configs = [
            {'host': 'smtp.gmail.com', 'port': 465, 'use_ssl': True, 'use_tls': False},
            {'host': 'smtp.gmail.com', 'port': 587, 'use_ssl': False, 'use_tls': True},
            {'host': 'smtp.gmail.com', 'port': 25, 'use_ssl': False, 'use_tls': True},
        ]
        
        for config in smtp_configs:
            try:
                print(f"DEBUG: Trying {config['host']}:{config['port']} (SSL: {config['use_ssl']}, TLS: {config['use_tls']})")
                
                with smtp_lock:
                    if config['use_ssl']:
                        # Use SSL
                        server = smtplib.SMTP_SSL(config['host'], config['port'])
                        print(f"DEBUG: SSL connection established")
                    else:
                        # Use TLS
                        server = smtplib.SMTP(config['host'], config['port'])
                        print(f"DEBUG: SMTP connection established")
                        
                        if config['use_tls']:
                            server.starttls()
                            print(f"DEBUG: TLS started")
                    
                    print(f"DEBUG: Attempting login with user: {GMAIL_USER}")
                    server.login(GMAIL_USER, GMAIL_PASS)
                    print(f"DEBUG: Login successful")
                    
                    # Send email
                    text = msg.as_string()
                    print(f"DEBUG: Sending email...")
                    server.sendmail(GMAIL_USER, email, text)
                    print(f"DEBUG: Email sent successfully")
                    
                    server.quit()
                    print(f"DEBUG: SMTP connection closed")
                    
                    log_request("EMAIL_SENT_SUCCESS", f"To: {name} ({email})")
                    return True
                    
            except Exception as e:
                print(f"DEBUG: Failed with {config['host']}:{config['port']} - {str(e)}")
                continue
        
        # If all configurations failed
        error_msg = "All SMTP configurations failed"
        log_request("EMAIL_SEND_FAILED", f"Error: {error_msg} | To: {name} ({email})")
        print(f"DEBUG: {error_msg}")
        return False
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        log_request("EMAIL_SEND_FAILED", f"Error: {error_msg} | To: {name} ({email})")
        print(f"DEBUG: {error_msg}")
        return False


def send_standard_onboarding_email():
    """
    Send a standard onboarding email to a default recipient.
    """
    try:
        # You can customize these default values
        default_name = "New Team Member"
        default_email = "hr@springworks.in"  # Change this to your HR email
        default_package = "Standard Package"
        
        log_request("SENDING_STANDARD_EMAIL", f"To: {default_name} ({default_email})")
        print(f"DEBUG: Starting standard email send to {default_name} ({default_email})")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = default_email
        msg['Subject'] = "Welcome to SpringWorks - New Team Member Onboarded"
        
        # Email body
        body = f"""Hi Team,

A new team member has been successfully onboarded!

Welcome aboard! We're thrilled to have them with us.

Their package ({default_package}) is active!

Please ensure they have access to all necessary systems and resources.

Best,
The SpringWorks Team"""
        
        msg.attach(MIMEText(body, 'plain'))
        print(f"DEBUG: Standard email message created")
        
        # Try different SMTP configurations
        smtp_configs = [
            {'host': 'smtp.gmail.com', 'port': 465, 'use_ssl': True, 'use_tls': False},
            {'host': 'smtp.gmail.com', 'port': 587, 'use_ssl': False, 'use_tls': True},
            {'host': 'smtp.gmail.com', 'port': 25, 'use_ssl': False, 'use_tls': True},
        ]
        
        for config in smtp_configs:
            try:
                print(f"DEBUG: Trying {config['host']}:{config['port']} (SSL: {config['use_ssl']}, TLS: {config['use_tls']})")
                
                with smtp_lock:
                    if config['use_ssl']:
                        # Use SSL
                        server = smtplib.SMTP_SSL(config['host'], config['port'])
                        print(f"DEBUG: SSL connection established")
                    else:
                        # Use TLS
                        server = smtplib.SMTP(config['host'], config['port'])
                        print(f"DEBUG: SMTP connection established")
                        
                        if config['use_tls']:
                            server.starttls()
                            print(f"DEBUG: TLS started")
                    
                    print(f"DEBUG: Attempting login with user: {GMAIL_USER}")
                    server.login(GMAIL_USER, GMAIL_PASS)
                    print(f"DEBUG: Login successful")
                    
                    # Send email
                    text = msg.as_string()
                    print(f"DEBUG: Sending standard email...")
                    server.sendmail(GMAIL_USER, default_email, text)
                    print(f"DEBUG: Standard email sent successfully")
                    
                    server.quit()
                    print(f"DEBUG: SMTP connection closed")
                    
                    log_request("STANDARD_EMAIL_SENT_SUCCESS", f"To: {default_name} ({default_email})")
                    return True
                    
            except Exception as e:
                print(f"DEBUG: Failed with {config['host']}:{config['port']} - {str(e)}")
                continue
        
        # If all configurations failed
        error_msg = "All SMTP configurations failed for standard email"
        log_request("STANDARD_EMAIL_SEND_FAILED", f"Error: {error_msg} | To: {default_name} ({default_email})")
        print(f"DEBUG: {error_msg}")
        return False
        
    except Exception as e:
        error_msg = f"Unexpected error in standard email: {str(e)}"
        log_request("STANDARD_EMAIL_SEND_FAILED", f"Error: {error_msg} | To: {default_name} ({default_email})")
        print(f"DEBUG: {error_msg}")
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
                event_ts = event.get('ts')  # Slack timestamp for uniqueness
                
                # Create unique event identifier
                event_id = f"{channel}_{user}_{event_ts}_{hash(text)}"
                
                # Check for duplicate events
                with event_lock:
                    if event_id in processed_events:
                        log_request("DUPLICATE_EVENT_IGNORED", f"Event ID: {event_id}")
                        return jsonify({"status": "ok"})
                    processed_events.add(event_id)
                    
                    # Clean up old events (keep only last 100)
                    if len(processed_events) > 100:
                        processed_events.clear()
                
                log_request("BOT_MENTIONED", f"Text: {text}, User: {user}, Channel: {channel}")
                print(f"DEBUG: Raw text received: '{text}'")
                
                # Check for simple onboard command
                if "- onboarded" in text.lower() or "onboarded" in text.lower():
                    # Send standard onboarding email
                    if send_standard_onboarding_email():
                        response_text = "✅ Standard onboarding email sent to the team!"
                        send_slack_message(channel, response_text)
                    else:
                        response_text = "❌ Failed to send onboarding email. Please try again or contact support."
                        send_slack_message(channel, response_text)
                    return jsonify({"status": "ok"})
                
                # Parse name, email, and package details for custom messages
                name, email, package = parse_slack_message(text)
                print(f"DEBUG: Parsed - Name: '{name}', Email: '{email}', Package: '{package}'")
                
                if not name or not email:
                    response_text = "❌ Invalid format. Please use: `@onboarding-bot - onboarded` or `@onboarding-bot John Doe john@example.com Premium Package`"
                    send_slack_message(channel, response_text)
                    return jsonify({"status": "ok"})
                
                # Validate email format
                if not validate_email_format(email):
                    response_text = f"❌ Invalid email format: {email}"
                    send_slack_message(channel, response_text)
                    return jsonify({"status": "ok"})
                
                # Send onboarding email
                if send_email(name, email, package):
                    package_text = f" with {package} package" if package else ""
                    response_text = f"✅ Onboarding email sent to {name} ({email}){package_text}"
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
