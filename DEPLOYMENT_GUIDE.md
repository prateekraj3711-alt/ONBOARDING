# 🚀 Deployment Guide

Complete guide to deploy your Slack Bot Onboarding Email Service to Render.

## 📋 Prerequisites

1. **GitHub Account** (free)
2. **Render Account** (free tier available)
3. **Gmail Account** with 2FA enabled
4. **Slack App** configured (see SLACK_SETUP_GUIDE.md)

## 🗂️ Step 1: Prepare Your Repository

### 1.1 Create GitHub Repository
1. Go to [GitHub.com](https://github.com) and sign in
2. Click **"New repository"** (green button)
3. Fill in details:
   - **Repository name**: `slack-onboarding-service`
   - **Description**: `Slack bot for onboarding emails`
   - **Visibility**: Public (free Render tier requires public repos)
4. Click **"Create repository"**

### 1.2 Upload Your Code
You have several options:

#### Option A: Using GitHub Desktop (Easiest)
1. Download [GitHub Desktop](https://desktop.github.com/)
2. Clone your repository
3. Copy all files from `slack-onboarding-service/` folder into the repository folder
4. Commit and push

#### Option B: Using Git Command Line
```bash
# Navigate to your project folder
cd slack-onboarding-service

# Initialize git repository
git init

# Add your files
git add .

# Commit
git commit -m "Initial commit: Slack onboarding bot service"

# Add remote repository
git remote add origin https://github.com/yourusername/slack-onboarding-service.git

# Push to GitHub
git push -u origin main
```

#### Option C: Direct Upload via GitHub Web
1. Go to your repository on GitHub
2. Click **"uploading an existing file"**
3. Drag and drop all files from `slack-onboarding-service/` folder
4. Add commit message and commit

## 🌐 Step 2: Set Up Render Account

### 2.1 Create Render Account
1. Go to [render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Sign up with your GitHub account (recommended)
4. Authorize Render to access your GitHub repositories

### 2.2 Connect GitHub (if not done during signup)
1. In Render dashboard, go to **"Account Settings"**
2. Click **"Connect GitHub"**
3. Authorize Render to access your repositories

## 🚀 Step 3: Deploy Your App

### 3.1 Create New Web Service
1. In Render dashboard, click **"New +"**
2. Select **"Web Service"**
3. Connect your repository:
   - Click **"Connect account"** if not connected
   - Find and select your `slack-onboarding-service` repository
   - Click **"Connect"**

### 3.2 Configure Your Service
Fill in the service configuration:

```
Name: slack-onboarding-service
Environment: Python 3
Region: Oregon (US West) or Frankfurt (EU)
Branch: main
Root Directory: (leave empty)
Build Command: pip install -r requirements.txt
Start Command: python app.py
```

### 3.3 Set Environment Variables
Click **"Advanced"** and add these environment variables:

```
GMAIL_USER = your-email@gmail.com
GMAIL_PASS = your16characterapppassword
SLACK_BOT_TOKEN = xoxb-your-bot-token-here
SLACK_SIGNING_SECRET = your_slack_signing_secret_here
PORT = 10000
```

**Important Notes:**
- Replace the values with your actual credentials
- `PORT` should be `10000` for Render (they'll override this)
- Don't include quotes around the values

### 3.4 Deploy
1. Click **"Create Web Service"**
2. Render will start building and deploying your app
3. This process takes 2-5 minutes

## 📊 Step 4: Monitor Deployment

### 4.1 Watch the Build Process
You'll see logs like:
```
==> Cloning from https://github.com/yourusername/slack-onboarding-service.git
==> Using Python version specified in runtime.txt
==> Installing pip
==> Installing dependencies from requirements.txt
==> Build completed successfully
==> Starting service with 'python app.py'
```

### 4.2 Check for Errors
If you see errors, common issues are:
- **Missing environment variables**: Make sure all are set
- **Wrong Python version**: Render uses Python 3.7+ by default
- **Import errors**: Check your requirements.txt

### 4.3 Get Your App URL
Once deployed, you'll get a URL like:
```
https://slack-onboarding-service.onrender.com
```

## 🧪 Step 5: Test Your Deployment

### 5.1 Test Health Endpoint
Open your browser and go to:
```
https://your-app-name.onrender.com/health
```

You should see:
```json
{"status": "ok"}
```

### 5.2 Check Logs
1. In Render dashboard, go to your service
2. Click **"Logs"** tab
3. You should see startup messages like:
```
🤖 Starting Slack Bot Onboarding Email Service
📧 Gmail User: your-email@gmail.com
🤖 Slack Bot Token: ****************
🔐 Slack Signing Secret: ****************
🌐 Port: 10000
👥 Multi-user support: ✅ Enabled
🔄 Unlimited requests: ✅ No rate limiting
📊 Monitoring: ✅ /health endpoint
🔒 Thread-safe SMTP: ✅ Enabled
Ready to handle bot mentions!
```

## 🔧 Step 6: Configure Slack Integration

### 6.1 Update Slack App
1. Go to your Slack app dashboard
2. Navigate to **"Event Subscriptions"**
3. Update the **Request URL** to:
   ```
   https://your-app-name.onrender.com/events
   ```
4. Click **"Save Changes"**

### 6.2 Test Slack Bot
In Slack, mention your bot:
```
@onboarding-bot Test User test@example.com
```

## 🛠️ Step 7: Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Build failed"
**Solutions:**
- Check your `requirements.txt` has all dependencies
- Ensure Python version compatibility
- Check build logs for specific errors

#### Issue 2: "Service failed to start"
**Solutions:**
- Verify all environment variables are set
- Check that `PORT` is set to `10000`
- Review startup logs for errors

#### Issue 3: "Health check failed"
**Solutions:**
- Ensure your app is listening on the correct port
- Check that the `/health` endpoint is working
- Verify the app started successfully

#### Issue 4: "Email sending failed"
**Solutions:**
- Double-check Gmail credentials
- Ensure you're using an app password (16 characters)
- Verify 2FA is enabled on your Google account

#### Issue 5: "Bot not responding"
**Solutions:**
- Check that the bot is installed in your workspace
- Verify the Request URL in Slack app settings
- Check Render logs for event processing

### Debugging Commands

#### Check Environment Variables
Your app logs will show:
```
DEBUG: Environment variables check:
DEBUG: GMAIL_USER set: True
DEBUG: GMAIL_PASS set: True
DEBUG: SLACK_BOT_TOKEN set: True
DEBUG: SLACK_SIGNING_SECRET set: True
```

#### Test SMTP Connection
Check the logs for SMTP connection messages:
```
[2024-10-15 12:30:00] Action: SENDING_EMAIL | To: John Doe (john@example.com)
[2024-10-15 12:30:01] Action: EMAIL_SENT_SUCCESS | To: John Doe (john@example.com)
```

## 📈 Step 8: Production Optimizations

### 8.1 Enable Auto-Deploy
1. In Render dashboard, go to your service
2. Go to **"Settings"**
3. Enable **"Auto-Deploy"** from main branch
4. Now every push to main will auto-deploy

### 8.2 Set Up Monitoring
1. Go to **"Monitoring"** tab
2. Set up alerts for:
   - Service downtime
   - High error rates
   - Memory usage

### 8.3 Custom Domain (Optional)
1. Go to **"Settings"** → **"Custom Domains"**
2. Add your domain
3. Update DNS records as instructed

## 💰 Step 9: Render Pricing

### Free Tier Limitations:
- **750 hours/month** (enough for most use cases)
- **Public repositories only**
- **Sleeps after 15 minutes** of inactivity
- **512MB RAM**

### Paid Plans:
- **Starter**: $7/month - Always on, private repos
- **Standard**: $25/month - More resources, better performance

## 🎉 Success!

Your app is now deployed and ready! You should have:

✅ **Deployed Flask app** on Render  
✅ **Working health endpoint**  
✅ **Environment variables** configured  
✅ **Slack bot integration** ready  
✅ **Email functionality** working  

## 🔄 Next Steps

1. **Test the complete flow** with Slack
2. **Set up monitoring** and alerts
3. **Configure custom domain** (if needed)
4. **Set up auto-deploy** for future updates
5. **Add more features** as needed

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Render logs in the dashboard
3. Test individual components (health endpoint, SMTP)
4. Verify all environment variables are correct

---

**Your app URL will be**: `https://your-app-name.onrender.com`

**Health check**: `https://your-app-name.onrender.com/health`

**Slack bot endpoint**: `https://your-app-name.onrender.com/events`
