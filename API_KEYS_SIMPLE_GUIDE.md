# API Keys - Simple Guide (For Humans)

## 🎯 The Basics

**What are API keys?**
- Like a password that lets you use the API
- You need one to upload documents, check jobs, etc.

---

## 🔑 Two Ways to Create Keys

### Method 1: Admin Creates (You)
**When:** You're the admin, creating keys for users

**How:**
1. Go to Railway → Variables → Get your `ADMIN_TOKEN`
2. Use curl or the GUI:
   ```
   POST /admin/api-keys?name=Key+Name
   Header: X-Admin-Token: YOUR_ADMIN_TOKEN
   ```
3. Give the key to the user

**Result:** User gets a key like `dp_abc123...`

---

### Method 2: User Creates (Using dev_123)
**When:** You want to create more keys for yourself

**How:**
1. Make sure you're logged in with `dev_123` (or any existing key)
2. Go to `/api-keys` page in dashboard
3. Click "+ Create Key"
4. Enter a name
5. Copy the new key (only shown once!)

**Result:** You get a new key like `dp_xyz789...`

---

## 📱 Using the Dashboard

### Step 1: Log In
- Go to dashboard
- Enter your API key (`dev_123` or a `dp_xxx` key)
- Click Continue

### Step 2: Manage Keys
- Click "🔑 API Keys" in header
- See your keys
- Create new ones
- Revoke/activate as needed

---

## 🎭 Admin Mode vs Normal Mode

### Normal Mode (Default)
- **What you see:** Your tenant's keys only
- **Uses:** Your API key (`dev_123` or `dp_xxx`)
- **Who uses:** Regular users

### Admin Mode
- **What you see:** ALL keys (all tenants)
- **Uses:** `ADMIN_TOKEN` (from Railway)
- **Who uses:** You (the admin)

**To enable:** Enter `ADMIN_TOKEN` → Click "Enable"

---

## 🔄 The Flow

```
┌─────────────────────────────────────┐
│ You (Admin)                         │
│   ↓                                 │
│ Create first key with ADMIN_TOKEN   │
│   ↓                                 │
│ Give key to User                    │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│ User                                 │
│   ↓                                 │
│ Uses key to access dashboard/API    │
│   ↓                                 │
│ Can create more keys (using key)    │
└─────────────────────────────────────┘
```

---

## 💡 Quick Reference

| What | How | Where |
|------|-----|-------|
| **Create first key** | Use `ADMIN_TOKEN` | `/admin/api-keys` |
| **Create more keys** | Use existing API key | `/v1/api-keys/` or GUI |
| **View your keys** | Use your API key | `/api-keys` page |
| **View all keys** | Use `ADMIN_TOKEN` | `/api-keys` page (admin mode) |
| **Use API** | Send key in header | All `/v1/*` endpoints |

---

## 🚨 Common Questions

**Q: Do I need to log in?**  
A: No traditional login. Just enter your API key in the dashboard.

**Q: Can I use `dev_123` to create keys?**  
A: Yes! That's the design. Use `dev_123` to create database-backed keys.

**Q: What's the difference between `dev_123` and `dp_xxx` keys?**  
A: 
- `dev_123` = Old style (env variable, can't revoke)
- `dp_xxx` = New style (database, can revoke/manage)

**Q: When do I use Admin Mode?**  
A: When you want to see/manage keys for ALL tenants (not just yours).

**Q: Where do I get ADMIN_TOKEN?**  
A: Railway dashboard → Your project → Variables → `ADMIN_TOKEN`

---

## ✅ Checklist

- [ ] Set `ADMIN_TOKEN` in Railway
- [ ] Create first key using admin endpoint
- [ ] Give key to user
- [ ] User can create more keys using their key
- [ ] User can manage keys in dashboard

---

## 🎓 Take Your Time

This is complex! It's totally normal to need time to understand. The key concepts:

1. **Admin creates first key** → Uses `ADMIN_TOKEN`
2. **User gets key** → Uses it everywhere
3. **User can create more** → Uses their existing key
4. **Admin mode** → See everything (optional)

That's it! Everything else is just details. 😊

