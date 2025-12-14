# 🚀 Render Deployment Guide - InFollow V2

## ✅ **Pre-Deployment Checklist**

Your project is **READY FOR RENDER**! All necessary files are in place:

- ✅ `Procfile` - Gunicorn configuration for production
- ✅ `runtime.txt` - Python 3.11.7 specified
- ✅ `requirements.txt` - All dependencies including gunicorn
- ✅ `.gitignore` - Database and sessions excluded
- ✅ `config.py` - Environment variable support
- ✅ `app.py` - Production-ready Flask app

---

## 📋 **Step-by-Step Deployment**

### **1. Create New Web Service on Render**

1. Go to https://render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select repository: **`VarsityPlug0/InFollow_V2`**
5. Click **"Connect"**

---

### **2. Configure Web Service**

**Basic Settings:**
```
Name:              infollow-v2
Region:            Choose closest to your users
Branch:            main
Runtime:           Python 3
Build Command:     pip install -r requirements.txt
Start Command:     gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:$PORT app:app
```

**Instance Type:**
- **Free Tier**: Fine for testing (spins down after inactivity)
- **Starter**: $7/month (always on, better for production)

---

### **3. Set Environment Variables**

Click **"Environment"** → **"Add Environment Variable"**

**Required Variables:**

| Key | Value | Description |
|-----|-------|-------------|
| `SECRET_KEY` | `your-random-secret-key-here` | Flask session security |
| `ADMIN_PASSWORD` | `your-admin-password` | Admin dashboard access |
| `PYTHON_VERSION` | `3.11.7` | Python runtime version |

**Generate a SECRET_KEY:**
```python
import secrets
print(secrets.token_hex(32))
# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

### **4. Create the Service**

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the app using the `Procfile` command

---

### **5. Monitor Deployment**

Watch the **Logs** tab for:

```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: gevent
[INFO] Booting worker with pid: 1
```

✅ **Success!** Your app is live!

---

## 🌐 **Access Your Application**

Your app will be available at:
```
https://infollow-v2.onrender.com
```
(Replace with your actual Render URL)

### **Test These Endpoints:**

1. **Homepage**: `https://your-app.onrender.com/`
2. **Login**: `https://your-app.onrender.com/login`
3. **Admin**: `https://your-app.onrender.com/admin`
4. **Dashboard**: `https://your-app.onrender.com/dashboard`

---

## 🗄️ **Database & Sessions**

### **SQLite Database**
- Stored in Render's ephemeral filesystem
- **Persists** between deploys
- **Resets** if service is deleted

### **Instagram Sessions**
- Stored in `sessions/` folder
- Auto-created on first use
- Persists login state for donated accounts

---

## 🔧 **Production Configuration**

### **Automatic Settings (Already Configured)**

1. **Gunicorn with Gevent**
   - Async worker for WebSocket support
   - Handles Socket.IO real-time updates
   - Single worker (optimal for free tier)

2. **Environment-Based Config**
   ```python
   SECRET_KEY = os.environ.get('SECRET_KEY')
   ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
   ```

3. **Port Binding**
   ```
   --bind 0.0.0.0:$PORT
   ```
   Render automatically provides $PORT

---

## 📊 **Post-Deployment Setup**

### **1. Add Initial Donor Accounts**

1. Go to `https://your-app.onrender.com/admin`
2. Login with your ADMIN_PASSWORD
3. Use "Add Donor Account" to bootstrap the workforce
4. Add 3-5 accounts to get started

### **2. Test the Flow**

1. Visit homepage
2. Sign up with test email
3. Donate an account
4. Use credits to boost a target
5. Verify followers are delivered

### **3. Monitor System**

Admin dashboard shows:
- Total accounts in pool
- Targets boosted
- Action logs
- System health

---

## ⚠️ **Important Notes**

### **Free Tier Limitations**

1. **Spin Down**: After 15 minutes of inactivity
   - First request after spin-down takes ~30 seconds
   - Subsequent requests are fast

2. **750 Hours/Month**: Free tier limit
   - Enough for testing/demos
   - Upgrade to Starter for production

3. **Ephemeral Storage**: 
   - Database persists between deploys
   - Gets reset if service deleted
   - Backup important data externally

### **Instagram Rate Limits**

- Render's IP may be shared
- Instagram may rate-limit follows
- Use delays between actions (already implemented)
- Monitor for "challenge required" errors

---

## 🔄 **Updating Your App**

### **Deploy New Changes:**

```bash
# Make changes locally
git add .
git commit -m "Update description"
git push origin main
```

Render will **automatically deploy** on push!

### **Manual Deploy:**
1. Go to Render dashboard
2. Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## 🐛 **Troubleshooting**

### **App Won't Start**

**Check Logs for:**
```
ModuleNotFoundError: No module named 'X'
```
**Solution**: Add missing package to `requirements.txt`

---

### **Database Errors**

**Error**: `OperationalError: no such table`

**Solution**: Database not initialized. Render will create it on first run.

---

### **WebSocket Issues**

**Error**: Socket.IO not connecting

**Check**:
- Gunicorn using `gevent` worker ✅
- `gevent-websocket` in requirements ✅
- Client connecting to correct URL

---

### **Admin Can't Login**

**Check**:
- `ADMIN_PASSWORD` environment variable set
- Using correct password
- Check logs for authentication errors

---

## 📈 **Scaling & Performance**

### **When to Upgrade**

**Free Tier** → **Starter ($7/month)**:
- Need 24/7 uptime
- Getting regular traffic
- Want faster response times

**Starter** → **Standard ($25/month)**:
- High traffic volume
- Need more workers
- Better performance

### **Optimization Tips**

1. **Database Cleanup**
   - Periodically remove old used accounts
   - Archive completed targets
   - Keep action logs under control

2. **Session Management**
   - Old Instagram sessions auto-expire
   - Clean `sessions/` folder occasionally

3. **Monitor Logs**
   - Watch for Instagram errors
   - Track follow success rate
   - Monitor workforce depletion

---

## ✅ **Deployment Checklist**

Before going live:

- [ ] Environment variables set (SECRET_KEY, ADMIN_PASSWORD)
- [ ] Repository connected to Render
- [ ] Build successful (check logs)
- [ ] App accessible at Render URL
- [ ] Admin login works
- [ ] Can add donor accounts
- [ ] Test user signup/login
- [ ] Test follower delivery
- [ ] WebSocket real-time updates working
- [ ] Dashboard shows correct data

---

## 🎯 **Next Steps**

1. **Deploy Now**: Push to GitHub → Auto-deploys to Render
2. **Test Everything**: Run through complete user flow
3. **Bootstrap Workforce**: Add initial donor accounts
4. **Monitor**: Watch logs for any issues
5. **Scale**: Upgrade tier when needed

---

## 📞 **Support Resources**

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Community**: https://community.render.com

---

## 🚀 **You're Ready to Deploy!**

All files are configured and pushed to GitHub. Just:

1. Go to Render.com
2. Create new Web Service
3. Connect your repo
4. Set environment variables
5. Deploy!

**Your Instagram Follower Barter System will be live in minutes!** 🎉

---

## 🔐 **Security Reminder**

- Never commit `.env` files
- Use strong SECRET_KEY
- Change default ADMIN_PASSWORD
- Monitor for suspicious activity
- Regularly update dependencies

**Happy Deploying!** 🚀
