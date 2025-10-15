# Slack Onboarding Email Service

A production-ready Flask application that integrates with Slack slash commands to automatically send onboarding emails via Gmail SMTP.

## 🚀 Features

- **Slack Integration**: Handles `/onboard` slash command
- **Multi-User Support**: Handles multiple concurrent users simultaneously
- **Email Automation**: Sends personalized onboarding emails via Gmail SMTP
- **Security**: Verifies Slack requests using signing secrets
- **Unlimited Usage**: No rate limiting - users can send as many emails as needed
- **User Tracking**: Comprehensive logging with user context
- **Thread-Safe**: Thread-safe SMTP connections for concurrent requests
- **Error Handling**: Comprehensive error handling and user feedback
- **Health Monitoring**: Built-in health check endpoint
- **Production Ready**: Optimized for deployment on Render, Heroku, or similar platforms

## 📋 Prerequisites

1. **Gmail Account** with 2FA enabled
2. **Slack App** with slash command configured
3. **Python 3.7+**

## 🛠️ Setup Instructions

### 1. Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Click on "App passwords"
4. Generate a new app password for "Mail"
5. Copy the 16-character password (you'll need this for `GMAIL_PASS`)

### 2. Slack App Configuration

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use existing one
3. Go to "Slash Commands" and create a new command:
   - Command: `/onboard`
   - Request URL: `https://your-app-url.com/onboard`
   - Short Description: `Send onboarding email to new team member`
   - Usage Hint: `John Doe john@example.com`
4. Go to "Basic Information" and copy the "Signing Secret"

### 3. Environment Variables

Copy `env.example` to `.env` and fill in your values:

```bash
cp env.example .env
```

Edit `.env` with your actual values:

```env
GMAIL_USER=youremail@gmail.com
GMAIL_PASS=your16characterapppassword
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
PORT=5000
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python app.py
```

The app will start on `http://localhost:5000`

## 🚀 Deployment to Render

### Step 1: Prepare Your Repository

1. Push your code to a GitHub repository
2. Make sure all files are committed:
   - `app.py`
   - `requirements.txt`
   - `env.example`

### Step 2: Deploy on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `slack-onboarding-service`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: `Free` (or upgrade as needed)

### Step 3: Set Environment Variables

In the Render dashboard, go to "Environment" and add:

```
GMAIL_USER=youremail@gmail.com
GMAIL_PASS=your16characterapppassword
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
```

### Step 4: Update Slack App

1. Go back to your Slack app settings
2. Update the Request URL to your Render app URL:
   `https://your-app-name.onrender.com/onboard`
3. Save changes

## 📱 Usage

### Slack Command

Use the slash command in any Slack channel:

```
/onboard John Doe john@example.com
```

### Expected Response

**Success:**
```
✅ Onboarding email sent to John Doe (john@example.com) by @alice
```

**Error Examples:**
```
❌ Invalid format. Please use: /onboard John Doe john@example.com
❌ Invalid email format: invalid-email
❌ Failed to send email to John Doe (john@example.com). Please try again or contact support.
```

## 🔧 API Endpoints

### POST `/onboard`
Handles Slack slash command requests.

**Headers:**
- `X-Slack-Request-Timestamp`: Request timestamp
- `X-Slack-Signature`: Request signature

**Form Data:**
- `token`: Slack verification token
- `user_name`: Slack username
- `command`: Command name (`/onboard`)
- `text`: Command text (`"John Doe john@example.com"`)

### GET `/health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "ok"
}
```


## 🛡️ Security Features

- **Slack Request Verification**: Validates requests using HMAC signatures
- **Timestamp Validation**: Prevents replay attacks (5-minute window)
- **Email Validation**: Validates email format before sending
- **Thread-Safe Operations**: Secure concurrent request handling
- **User Context Logging**: Track all actions with user attribution
- **Error Handling**: Secure error messages without exposing internals

## 🐛 Troubleshooting

### Common Issues

1. **"Unauthorized request" error**
   - Check that `SLACK_SIGNING_SECRET` is correct
   - Verify the Slack app's signing secret matches

2. **"Failed to send email" error**
   - Verify `GMAIL_USER` and `GMAIL_PASS` are correct
   - Ensure you're using an app password, not your regular Gmail password
   - Check that 2FA is enabled on your Google account

3. **"Invalid email format" error**
   - Ensure the email address is properly formatted
   - Check that there are no extra spaces or characters

### Testing Locally

You can test the health endpoint:

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "ok"}
```

## 📝 Email Template

The onboarding email sent to new team members:

```
Subject: Welcome to [Your Company Name]!

Hi {name},

Welcome aboard! We're thrilled to have you with us.

Feel free to reach out if you need any help getting started.

Best,
The Team
```

## 🔄 Customization

### Modify Email Template

Edit the `send_email()` function in `app.py` to customize the email content:

```python
# Email body
body = f"""Hi {name},

Your custom welcome message here.

Best,
Your Team"""
```

### Change Company Name

Update the email subject in the `send_email()` function:

```python
msg['Subject'] = "Welcome to Your Company Name!"
```

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in your deployment platform
3. Create an issue in the repository
