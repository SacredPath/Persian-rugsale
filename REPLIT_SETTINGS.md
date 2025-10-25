# 🛑 Stop Replit From Editing Your Files

## Why Replit Edits Files

| Feature | What It Does | How to Disable |
|---------|--------------|----------------|
| **Ghostwriter AI** | Auto-completes code, suggests fixes | Settings → AI → Turn OFF |
| **Auto-Format** | Formats code on save | Settings → Editor → Format on save OFF |
| **Line Endings** | Converts CRLF ↔ LF | Use `.editorconfig` (already added) |
| **Agents** | AI rewrites code | Don't use "Create with Agent" |
| **Package Manager** | Updates requirements.txt | Manual control only |

---

## ⚙️ Recommended Settings

### 1. Disable Ghostwriter
```
Profile (top right) → Settings → AI
❌ Enable Ghostwriter
❌ Auto-complete
❌ Code suggestions
```

### 2. Disable Auto-Formatting
```
Settings (gear icon) → Editor
❌ Format on save
❌ Auto-format
```

### 3. Use `.editorconfig`
✅ Already added to project root
- Prevents auto-formatting
- Fixes line ending issues
- Preserves indentation

---

## 🔧 Git Workflow on Replit

### Before Making Changes:
```bash
git pull origin main
```

### Check What Changed:
```bash
git status
git diff
```

### Revert Unwanted Changes:
```bash
# Revert specific file
git checkout -- main.py

# Revert all changes
git reset --hard HEAD
```

### Commit Your Changes:
```bash
git add .
git commit -m "Your message"
git push origin main
```

---

## ⚠️ Common Replit Changes

| Change Type | Safe? | Action |
|-------------|-------|--------|
| Line endings (CRLF → LF) | ✅ Safe | Ignore or commit |
| Whitespace | ✅ Safe | Ignore or commit |
| Added imports | ⚠️ Check | Review before commit |
| Logic changes | ❌ Unsafe | Revert immediately |

---

## 🎯 Best Practices

1. **Use GitHub as source of truth**
   - Always pull before editing
   - Review diffs before pushing

2. **Disable aggressive features**
   - Turn off Ghostwriter
   - Turn off auto-format

3. **Run `git status` often**
   - See what changed
   - Catch unwanted edits early

4. **Test after Replit changes**
   - Run bot to verify
   - Revert if broken

---

## 🚨 If Replit Breaks Your Code

```bash
# Option 1: Revert to last commit
git reset --hard HEAD

# Option 2: Pull from GitHub
git fetch origin
git reset --hard origin/main

# Option 3: Revert specific file
git checkout HEAD -- main.py
```

Then disable the auto-edit features!

---

## ✅ Current Protection

Your project now has:
- ✅ `.editorconfig` (prevents auto-formatting)
- ✅ `.gitignore` (protects sensitive files)
- ✅ Git version control (easy revert)

**Recommendation:** Still disable Ghostwriter and auto-format in Replit settings!

