"""
Slack Bot Onboarding Email Service - With Complete SpringVerify Links

A production-ready Flask app that responds to Slack bot mentions and sends onboarding emails.
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
    raise ValueError("Missing required environment variables")

# SMTP connection pool for better concurrency handling
smtp_lock = threading.Lock()

# Track processed events to prevent duplicates
processed_events = set()
event_lock = threading.Lock()


def log_request(action, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Action: {action} | {details}")


def verify_slack_request(request_data, timestamp, signature):
    if not all([request_data, timestamp, signature]):
        return False
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > 300:
        return False
    sig_basestring = f"v0:{timestamp}:{request_data}"
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def parse_slack_message(text):
    if not text or not text.strip():
        return None, None, None, None, None, None, None
    
    mention_pattern = r'<@[A-Z0-9]+>\s*'
    clean_text = re.sub(mention_pattern, '', text).strip()
    
    workflow_pattern = r'Customer:\s*([^\n\r]+)'
    customer_match = re.search(workflow_pattern, clean_text, re.IGNORECASE)
    
    if customer_match:
        customer_line = customer_match.group(1).strip()
        customer_name = None
        customer_email = None
        
        mailto_pattern = r'<mailto:([^|>]+)\|[^>]+>'
        mailto_match = re.search(mailto_pattern, customer_line)
        if mailto_match:
            customer_email = mailto_match.group(1)
            name_part = re.sub(mailto_pattern, '', customer_line).strip()
            customer_name = name_part.replace(' -', '').strip()
        else:
            customer_name = customer_line
        
        csm_pattern = r'CSM:\s*([^\n\r]+)'
        csm_match = re.search(csm_pattern, clean_text, re.IGNORECASE)
        csm = csm_match.group(1).strip() if csm_match else None
        
        csa_pattern = r'CSA:\s*([^\n\r]+)'
        csa_match = re.search(csa_pattern, clean_text, re.IGNORECASE)
        csa = csa_match.group(1).strip() if csa_match else None
        
        date_pattern = r'Date[^:]*:\s*([^\n\r]+)'
        date_match = re.search(date_pattern, clean_text, re.IGNORECASE)
        date = date_match.group(1).strip() if date_match else None
        
        granola_pattern = r'Granola[^:]*:\s*([^\n\r]+)'
        granola_match = re.search(granola_pattern, clean_text, re.IGNORECASE)
        granola = granola_match.group(1).strip() if granola_match else None
        
        return customer_name, customer_email, None, csm, csa, date, granola
    
    mailto_pattern = r'<mailto:([^|>]+)\|[^>]+>'
    mailto_match = re.search(mailto_pattern, clean_text)
    
    if mailto_match:
        email = mailto_match.group(1)
        remaining_text = re.sub(mailto_pattern, '', clean_text).strip()
        parts = remaining_text.split()
        if len(parts) >= 1:
            name = parts[0] if len(parts) == 1 else ' '.join(parts[:-1])
            package = parts[-1] if len(parts) > 1 else None
        else:
            name = None
            package = None
        return name, email, package, None, None, None, None
    
    parts = clean_text.split()
    if len(parts) < 2:
        return None, None, None, None, None, None, None
    
    email = None
    email_index = -1
    for i, part in enumerate(parts):
        if '@' in part and '.' in part:
            email = part
            email_index = i
            break
    
    if not email:
        return None, None, None, None, None, None, None
    
    name_parts = parts[:email_index]
    package_parts = parts[email_index + 1:]
    name = ' '.join(name_parts) if name_parts else None
    package = ' '.join(package_parts) if package_parts else None
    
    return name, email, package, None, None, None, None


def validate_email_format(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def send_email(name, email, package=None, customer=None, csm=None, csa=None, date=None, granola=None):
    try:
        log_request("SENDING_EMAIL", f"To: {name} ({email}), Package: {package}")
        print(f"DEBUG: Starting email send to {name} ({email}), Package: {package}")

        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Welcome to SpringWorks"

        greeting_name = customer if customer else name
        csm_name = csm if csm else "Derishti"
        csm_email = "derishti.dogra@springworks.in"
        csm_phone = "+919501291354"
        csa_name = csa if csa else "Derishti Dogra"
        csa_email = "derishti.dogra@springworks.in"
        csa_phone = "+919501291354"
        package_info = f"Custom Verifier 1: {package}" if package else "Custom Verifier 1:"
        date_info = f"\nOnboarding Date: {date}" if date else ""
        granola_info = f"\nGranola Link: {granola}" if granola else ""

        body = f"""Hello {greeting_name},<br><br>

It was great connecting with you earlier today! Welcome Aboard ✨<br><br>

Please meet your Customer Success Manager {csm_name}, who will be your main point of contact moving forward. {csm_name}, will handhold you through the further process, and you can always reach out to her and the support team for any queries. She is looped into this email for your convenience.<br><br>

Here's a quick summary of our discussion earlier FYR:<br><br>

<strong>Support and Escalations:</strong><br>
• Primary POC Support: For any queries please reach out to <a href="mailto:cs@springverify.com">cs@springverify.com</a>/ 08047190155/ WhatsApp: 8971814318<br>
• Secondary POC(CSA): {csa_name}, <a href="mailto:{csa_email}">{csa_email}</a>, {csa_phone}<br>
• CSM contact details: {csm_name}, <a href="mailto:{csm_email}">{csm_email}</a>, {csm_phone}<br>
• Escalation Matrix: Soumabrata - Head of Customer Success, <a href="mailto:soumabrata.chatterjee@springworks.in">soumabrata.chatterjee@springworks.in</a><br><br>

<strong>Package Details:</strong><br>
• {package_info}<br>
&nbsp;&nbsp;&nbsp;&nbsp;◦ Identity Check<br>
&nbsp;&nbsp;&nbsp;&nbsp;◦ Court Check<br>
&nbsp;&nbsp;&nbsp;&nbsp;◦ Employment Check (Last 2){date_info}{granola_info}<br><br>

<strong>Points to note</strong><br>
• For any queries related to the dashboard, you can refer to our knowledge base from here: <a href="https://support.springworks.in/portal/en/kb/springverify/client-knowledge-base">SpringVerify knowledge base</a><br>
• The consent letter will be signed by the candidate digitally as a part of the BGV form sent.<br>
• Please check <a href="https://docs.google.com/spreadsheets/d/1uKXkkTKONgk2heg9BqzkKg1ycnv-PPcNkGSlNQCS1Bc/edit?gid=0#gid=0">this sheet</a> to check the format for uploading candidates in bulk.<br>
• You can share <a href="https://springworks.fleeq.io/l/ko1qgfu036-7ehmd3znyo">this step-by-step guide</a> with candidates which will help them in filling the form more easily.<br>
• For digital address verification, candidates can refer to <a href="https://support.springworks.in/portal/en/kb/articles/dav-digital-address-verification-guidelines-and-faq">this tutorial</a> to understand the process.<br>
• All the insufficiency related communication will be made to the candidate directly keeping you marked in cc.<br><br>

<strong>Documents Required</strong><br>
• ID - PAN / Voter ID / DL (PAN preferable)<br>
• Address & Court - Aadhaar / Passport / Voter ID / DL<br>
• Employment - Experience Letter / Relieving Letter<br>
• Education - Degree certificate, Marksheets<br>
&nbsp;&nbsp;&nbsp;&nbsp;(A comprehensive list of all acceptable documents can be found <a href="https://docs.google.com/document/d/12-IeWLhL_bIxqNxZODbymi6_mIBhkd0ouhY0sNX_4jY/edit?tab=t.0#heading=h.d6rqdchpcvka">here</a> for your reference)<br><br>

<strong>TAT</strong><br>
• ID - 1 working day<br>
• Address - 2-14 working days (Depending upon the candidate)<br>
• Court Verification - 1-2 working days<br>
• Education/Employment and Reference - 7-14 working days<br>
• World Check - 2-3 working days<br>
&nbsp;&nbsp;&nbsp;&nbsp;(Please note that Insufficiency/ On hold days are not included in the overall TAT)<br><br>

• For Education and Employment Verifications there may be additional charges depending on the university/company we reach out to. It would be collected after your approval and the payment receipt will be added to the report shared.<br>
• For International Verifications, there will be a standard charge of INR 1500 applied for each International check.<br>
• For Current Employment, the candidate can mention in the BGV form directly that they are still working there. Once they specify it, the verification automatically goes on hold until the candidate/you confirm us that they've left the organization effectively, so we can reach out to them for the employment verification.<br><br>

<strong>Few important Links for your reference.</strong><br>
• <a href="https://support.springworks.in/portal/en/kb/springverify/client-knowledge-base">Knowledge Base Document link</a><br>
• <a href="https://support.springworks.in/portal/en/kb/articles/check-wise-status-definition-and-color-codes">Check wise statuses - Definition and Color codes Link</a><br>
• <a href="https://springworks.fleeq.io/l/ko1qgfu036-7ehmd3znyo">Step-By-Step guide for candidates</a><br><br>

Hope this helps. Please let me know if you have any questions and I'll be happy to help!<br><br>

Regards!<br>
Panchalee Roy<br>
Ph : 9742089120<br>
<a href="https://docs.google.com/forms/d/e/1FAIpQLSe4bdGfyvw-cTyjzvqkzh8SJjzsvpkSDTXyeVhg7-yNHtGD3g/viewform">Give us Feedback!</a><br>
Customer Onboarding Specialist at SpringVerify | Springworks"""

        msg.attach(MIMEText(body, 'html'))
        print(f"DEBUG: Email message created")

        smtp_configs = [
            {'host': 'smtp.gmail.com', 'port': 465, 'use_ssl': True, 'use_tls': False},
            {'host': 'smtp.gmail.com', 'port': 587, 'use_ssl': False, 'use_tls': True},
            {'host': 'smtp.gmail.com', 'port': 25, 'use_ssl': False, 'use_tls': True},
        ]

        for config in smtp_configs:
            try:
                print(f"DEBUG: Trying {config['host']}:{config['port']}")
                with smtp_lock:
                    if config['use_ssl']:
                        server = smtplib.SMTP_SSL(config['host'], config['port'])
                    else:
                        server = smtplib.SMTP(config['host'], config['port'])
                        if config['use_tls']:
                            server.starttls()
                    
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.sendmail(GMAIL_USER, email, msg.as_string())
                    server.quit()
                    log_request("EMAIL_SENT_SUCCESS", f"To: {name} ({email})")
                    return True
            except Exception as e:
                print(f"DEBUG: Failed with {config['host']}:{config['port']} - {str(e)}")
                continue

        log_request("EMAIL_SEND_FAILED", f"All SMTP configs failed | To: {name} ({email})")
        return False

    except Exception as e:
        log_request("EMAIL_SEND_FAILED", f"Error: {str(e)} | To: {name} ({email})")
        return False


def send_standard_onboarding_email():
    try:
        default_name = "New Member"
        default_email = "hr@springworks.in"
        default_package = "Standard Package"
        
        log_request("SENDING_STANDARD_EMAIL", f"To: {default_name} ({default_email})")
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = default_email
        msg['Subject'] = "Welcome to SpringWorks - New Member Onboarded"

        body = f"""Hello Team,

A new member has been successfully onboarded! Welcome Aboard✨ 

For detailed information, please refer to our knowledge base: https://support.springworks.in/portal/en/kb/springverify/client-knowledge-base

Package: {default_package}

Best regards,
SpringVerify Team"""

        msg.attach(MIMEText(body, 'plain'))
        
        smtp_configs = [
            {'host': 'smtp.gmail.com', 'port': 465, 'use_ssl': True, 'use_tls': False},
            {'host': 'smtp.gmail.com', 'port': 587, 'use_ssl': False, 'use_tls': True},
        ]

        for config in smtp_configs:
            try:
                with smtp_lock:
                    if config['use_ssl']:
                        server = smtplib.SMTP_SSL(config['host'], config['port'])
                    else:
                        server = smtplib.SMTP(config['host'], config['port'])
                        if config['use_tls']:
                            server.starttls()
                    
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.sendmail(GMAIL_USER, default_email, msg.as_string())
                    server.quit()
                    return True
            except:
                continue
        return False
    except:
        return False


def send_slack_message(channel, text):
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {"channel": channel, "text": text}
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except:
        return False


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})


@app.route('/events', methods=['POST'])
def events():
    try:
        request_data = request.get_data(as_text=True)
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')

        if not verify_slack_request(request_data, timestamp, signature):
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        
        if data.get('type') == 'url_verification':
            return jsonify({"challenge": data.get('challenge')})

        if data.get('type') == 'event_callback':
            event = data.get('event', {})

            if event.get('type') == 'app_mention':
                text = event.get('text', '')
                channel = event.get('channel')
                user = event.get('user')
                event_ts = event.get('ts')

                event_id = f"{channel}_{user}_{event_ts}_{hash(text)}"

                with event_lock:
                    if event_id in processed_events:
                        return jsonify({"status": "ok"})
                    processed_events.add(event_id)
                    if len(processed_events) > 100:
                        processed_events.clear()

                log_request("BOT_MENTIONED", f"Text: {text}")
                print(f"DEBUG: Raw text: '{text}'")

                if "- onboarded" in text.lower() or "onboarded" in text.lower():
                    if send_standard_onboarding_email():
                        send_slack_message(channel, "✅ Standard onboarding email sent!")
                    else:
                        send_slack_message(channel, "❌ Failed to send email.")
                    return jsonify({"status": "ok"})

                customer_name, customer_email, package, csm, csa, date, granola = parse_slack_message(text)
                print(f"DEBUG: Parsed - Customer: '{customer_name}', Email: '{customer_email}'")

                if customer_name:
                    if customer_email:
                        if not validate_email_format(customer_email):
                            send_slack_message(channel, f"❌ Invalid email: {customer_email}")
                            return jsonify({"status": "ok"})

                        if send_email(customer_name, customer_email, package, customer_name, csm, csa, date, granola):
                            send_slack_message(channel, f"✅ Email sent to {customer_name} ({customer_email})!")
                        else:
                            send_slack_message(channel, f"❌ Failed to send email to {customer_name}.")
                        return jsonify({"status": "ok"})
                    else:
                        send_slack_message(channel, f"✅ Workflow details extracted for {customer_name}!\n\nCSM: {csm}\nCSA: {csa}\nDate: {date}\n\nPlease provide email.")
                        return jsonify({"status": "ok"})

                send_slack_message(channel, "❌ Invalid format. Use: `@onboarding-bot - onboarded` or paste workflow details")
                return jsonify({"status": "ok"})

        return jsonify({"status": "ok"})

    except Exception as e:
        log_request("EVENT_ERROR", f"Error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Slack Bot Onboarding Email Service - READY")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=True, threaded=True)
