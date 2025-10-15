# 🔧 Slack Bot Setup Guide

Complete step-by-step guide to set up your Slack bot for the onboarding email service.

## 🎯 **What We're Building:**

A Slack bot that responds to mentions and sends onboarding emails:
- **User mentions bot**: `@onboarding-bot John Doe john@example.com`
- **Bot processes data** and sends email via Gmail SMTP
- **Bot responds** with success/error message

## 🚀 **Step 1: Create Slack App**

### 1.1 Go to Slack API Dashboard
1. Visit [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter app details:
   - **App Name**: `Onboarding Email Bot`
   - **Pick a workspace**: Select your workspace
5. Click **"Create App"**

### 1.2 Configure Basic Information
1. In your app dashboard, go to **"Basic Information"**
2. Note down the **"Signing Secret"** (you'll need this for `SLACK_SIGNING_SECRET`)

## 🤖 **Step 2: Configure Bot User**

### 2.1 Add Bot User
1. Go to **"Bot"** in the left sidebar
2. Click **"Add Bot User"**
3. Configure the bot:
   - **Display Name**: `Onboarding Bot`
   - **Default Username**: `onboarding-bot`
   - **Always Show My Bot as Online**: ✅ Yes
4. Click **"Add Bot User"**

### 2.2 Set OAuth Scopes
1. Go to **"OAuth & Permissions"**
2. Scroll down to **"Scopes"**
3. Add these **Bot Token Scopes**:
   - `app_mentions:read` (to see when bot is mentioned)
   - `chat:write` (to send messages)
   - `channels:read` (to read channel info)

### 2.3 Install Bot to Workspace
1. Scroll up to **"OAuth Tokens for Your Workspace"**
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

## 📡 **Step 3: Set Up Event Subscriptions**

### 3.1 Enable Events
1. Go to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to **ON**

### 3.2 Set Request URL
1. In the **"Request URL"** field, enter:
   ```
   https://your-app-name.onrender.com/events
   ```
   (Replace `your-app-name` with your actual Render app name)

2. Click **"Save Changes"**

### 3.3 Subscribe to Bot Events
1. Scroll down to **"Subscribe to bot events"**
2. Click **"Add Bot User Event"**
3. Add: `app_mention`
4. Click **"Save Changes"**

## 🔐 **Step 4: Get Your Credentials**

### 4.1 Bot Token
From **"OAuth & Permissions"**:
- Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)
- This goes in `SLACK_BOT_TOKEN`

### 4.2 Signing Secret
From **"Basic Information"**:
- Copy the **"Signing Secret"**
- This goes in `SLACK_SIGNING_SECRET`

## 🚀 **Step 5: Deploy Your App**

### 5.1 Update Environment Variables in Render
Add these to your Render environment variables:

```
GMAIL_USER=youremail@gmail.com
GMAIL_PASS=your16characterapppassword
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
PORT=10000
```

### 5.2 Deploy
1. Push your code to GitHub
2. Render will auto-deploy
3. Wait for deployment to complete

## 🧪 **Step 6: Test Your Bot**

### 6.1 Test in Slack
1. Go to any channel in your workspace
2. Type: `@onboarding-bot John Doe john@example.com`
3. The bot should respond with a success message

### 6.2 Check Logs
1. Go to Render dashboard
2. Check the logs for bot activity
3. Look for mention events and email sending

## 🎯 **Expected Flow:**

1. **User types**: `@onboarding-bot John Doe john@example.com`
2. **Slack sends event** to your Flask app
3. **App processes data** and sends email
4. **Bot responds**: `✅ Onboarding email sent to John Doe (john@example.com)`

## 🚨 **Troubleshooting:**

### Bot Not Responding
- Check that the bot is installed in your workspace
- Verify the Request URL is correct in Event Subscriptions
- Check Render logs for errors

### URL Verification Failed
- Make sure your app is deployed and running
- Check that the `/events` endpoint is working
- Verify environment variables are set correctly

### Email Not Sending
- Check Gmail credentials in environment variables
- Verify 2FA is enabled on your Google account
- Check SMTP connection in logs

## ✅ **Success Checklist:**

- [ ] Slack app created
- [ ] Bot user added
- [ ] OAuth scopes configured
- [ ] Bot installed to workspace
- [ ] Event subscriptions enabled
- [ ] Request URL set correctly
- [ ] Environment variables configured
- [ ] App deployed to Render
- [ ] Bot responds to mentions
- [ ] Emails are being sent

## 🎉 **You're Done!**

Your Slack bot is now ready to send onboarding emails! Users can simply mention the bot with a name and email, and it will automatically send a welcome email.

---

**Need help?** Check the troubleshooting section or review the logs in your Render dashboard.
