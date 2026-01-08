# Push to GitHub Repository

## Your Repository: https://github.com/fkoff002-glitch/rf-automations

## 🚀 Quick Push Commands

**You're currently at: H:\RF-Automation**

### Step 1: Initialize Git (if not done)
```bash
git init
git add .
git commit -m "Initial commit: RF Automation System - Backend + Frontend"
```

### Step 2: Connect to Your Repository
```bash
git remote add origin https://github.com/fkoff002-glitch/rf-automations.git
```

(If you get "remote already exists" error, use: `git remote set-url origin https://github.com/fkoff002-glitch/rf-automations.git`)

### Step 3: Push to GitHub
```bash
git branch -M main
git push -u origin main
```

**When asked for credentials:**
- **Username:** `fkoff002-glitch`
- **Password:** Use **Personal Access Token** (not password)
  - Create token: https://github.com/settings/tokens
  - Click "Generate new token (classic)"
  - Select scope: `repo` (full control)
  - Copy token and use as password

### Step 4: Verify on GitHub
Go to: https://github.com/fkoff002-glitch/rf-automations

You should see:
- ✅ `backend/` folder
- ✅ `frontend/` folder
- ✅ All documentation files

### Step 5: Enable GitHub Pages (For Frontend)

1. Go to: https://github.com/fkoff002-glitch/rf-automations/settings/pages
2. Source: **Deploy from a branch**
3. Branch: **main**
4. Folder: **/frontend**
5. Click **Save**

Your frontend will be at: **https://fkoff002-glitch.github.io/rf-automations/**

## 📋 All Commands at Once (Copy & Paste)

```bash
cd H:\RF-Automation
git init
git add .
git commit -m "Initial commit: RF Automation System"
git remote add origin https://github.com/fkoff002-glitch/rf-automations.git
git branch -M main
git push -u origin main
```

## ✅ After Pushing

1. **Update Frontend API URL:**
   - Edit `frontend/app.js`
   - Change `API_BASE` to your backend server URL

2. **Update Backend CORS:**
   - Edit `backend/.env`
   - Add: `CORS_ORIGINS=["https://fkoff002-glitch.github.io","http://localhost:8080"]`

3. **Restart Backend:**
   ```bash
   cd H:\RF-Automation\backend
   python -m app.main
   ```

## 🎯 Done!

After pushing, your code will be live at: https://github.com/fkoff002-glitch/rf-automations
