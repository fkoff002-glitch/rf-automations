# GitHub Push Steps - For H:\RF-Automation

## ✅ Your Structure is Ready!

You have:
- ✅ `backend/` folder
- ✅ `frontend/` folder

## 🚀 Step-by-Step Commands to Push to GitHub

### Step 1: Navigate to Your Folder (You're already here!)
```bash
cd H:\RF-Automation
```

### Step 2: Initialize Git Repository
```bash
git init
```

### Step 3: Add All Files
```bash
git add .
```

### Step 4: Create First Commit
```bash
git commit -m "Initial commit: RF Automation System - Backend + Frontend"
```

### Step 5: Create Repository on GitHub Website

1. **Open browser and go to:**
   https://github.com/new

2. **Fill in:**
   - Repository name: `rf-automation` (or `RF-Automation`)
   - Description: `RF Automation System - Backend (FastAPI) + Frontend (GitHub Pages)`
   - Choose: **Public** or **Private**
   - **DO NOT** check "Add a README file"
   - **DO NOT** check "Add .gitignore"
   - **DO NOT** choose a license
   - Click **"Create repository"**

### Step 6: Connect to GitHub and Push

After creating the repository on GitHub, run:

```bash
# Add remote repository
git remote add origin https://github.com/fkoff002-glitch/rf-automation.git

# Set branch name to main
git branch -M main

# Push to GitHub (you'll be asked for credentials)
git push -u origin main
```

**When asked for credentials:**
- **Username:** `fkoff002-glitch`
- **Password:** Use a **Personal Access Token** (not your password)
  - Create token: https://github.com/settings/tokens
  - Click "Generate new token (classic)"
  - Select scope: `repo` (full control)
  - Copy the token and use it as password

### Step 7: Enable GitHub Pages

1. **Go to your repository:**
   https://github.com/fkoff002-glitch/rf-automation/settings/pages

2. **Settings:**
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/frontend** (select from dropdown)
   - Click **Save**

3. **Your frontend will be at:**
   https://fkoff002-glitch.github.io/rf-automation/

## 🎯 Quick Command Summary (Copy & Paste)

```bash
cd H:\RF-Automation
git init
git add .
git commit -m "Initial commit: RF Automation System"
git remote add origin https://github.com/fkoff002-glitch/rf-automation.git
git branch -M main
git push -u origin main
```

## ✅ Verification Checklist

After pushing:

- [ ] Go to: https://github.com/fkoff002-glitch/rf-automation
- [ ] Verify you see `backend/` and `frontend/` folders
- [ ] Enable GitHub Pages (Settings → Pages)
- [ ] Test frontend URL: https://fkoff002-glitch.github.io/rf-automation/
- [ ] Update `backend/.env` with CORS settings
- [ ] Update `frontend/app.js` with backend API URL

## 🔐 Next Steps After GitHub Push

1. **Configure Backend:**
   ```bash
   cd H:\RF-Automation\backend
   # Copy .env.example to .env and configure it
   # Set SECRET_KEY, CORS_ORIGINS, etc.
   ```

2. **Start Backend:**
   ```bash
   cd H:\RF-Automation\backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python scripts\init_db.py
   python -m app.main
   ```

3. **Update Frontend API URL:**
   - Edit `frontend/app.js`
   - Change `API_BASE` to your backend server URL

## 📚 Full Documentation

See other files in this folder:
- `START_HERE.md` - Quick reference
- `COMPLETE_SETUP.md` - Complete setup guide
- `DEPLOYMENT.md` - Deployment details
