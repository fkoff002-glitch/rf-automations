# Fix Authentication Issue

## Problem
You're authenticated as `shsakib0002` but need to push to `fkoff002-glitch` repository.

## Solutions

### Option 1: Use Personal Access Token (Recommended)

1. **Update remote URL with credentials:**
   ```bash
   git remote set-url origin https://fkoff002-glitch@github.com/fkoff002-glitch/rf-automations.git
   ```

2. **Push again:**
   ```bash
   git push -u origin main
   ```

3. **When asked for password:**
   - Use a Personal Access Token (not password)
   - Create token: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scope: `repo` (full control)
   - Copy token and paste as password

### Option 2: Use GitHub Credential Manager

1. **Clear stored credentials:**
   ```bash
   git credential-manager-core erase
   ```
   Or on Windows:
   ```bash
   cmdkey /list
   cmdkey /delete:git:https://github.com
   ```

2. **Push again:**
   ```bash
   git push -u origin main
   ```

3. **When prompted, use:**
   - Username: `fkoff002-glitch`
   - Password: Personal Access Token

### Option 3: Use SSH (Alternative)

1. **Switch to SSH:**
   ```bash
   git remote set-url origin git@github.com:fkoff002-glitch/rf-automations.git
   ```

2. **Push:**
   ```bash
   git push -u origin main
   ```
   (Requires SSH keys set up)

## Quick Fix Commands (Try These First)

```bash
# Update remote with correct username
git remote set-url origin https://fkoff002-glitch@github.com/fkoff002-glitch/rf-automations.git

# Push again
git push -u origin main
```

When prompted:
- Username: `fkoff002-glitch`
- Password: **Personal Access Token** (from https://github.com/settings/tokens)
