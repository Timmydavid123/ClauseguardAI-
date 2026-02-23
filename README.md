# ⚖️ ClauseGuard — AI Contract Risk Analyzer
> Django + Docker | Auth + Google OAuth | AI Chat | Risk Review | History

---

## 🚀 Quick Start with Docker

```bash
# 1. Clone and enter project
cd clauseguard

# 2. Copy env file
cp .env.example .env

# 3. Add your API key to .env
# AI_API_KEY=sk-ant-your-key-here

# 4. Build and run
docker-compose up --build
```

Visit → **http://localhost:8000**

---

## 🔑 Getting Google OAuth Credentials

1. Go to **https://console.cloud.google.com**
2. Create a new project (or select existing)
3. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**
   - Fill in App name: `ClauseGuard`
   - Add your email as support email
   - Save
4. Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth Client ID**
   - Application type: **Web application**
   - Name: `ClauseGuard`
   - Authorized redirect URIs — add:
     ```
     http://localhost:8000/social-auth/complete/google-oauth2/
     ```
   - Click **Create**
5. Copy **Client ID** and **Client Secret**
6. Add to your `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id-here
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   ```
7. Restart Docker: `docker-compose restart`

---

## 📁 Project Structure

```
clauseguard/
├── analyzer/                  # Main app
│   ├── templates/analyzer/    # Upload, Results, History pages
│   ├── static/analyzer/       # CSS + JS
│   ├── models.py              # Contract + Risk models
│   ├── views.py               # All analyzer views
│   ├── services.py            # AI + PDF logic
│   └── urls.py
├── accounts/                  # Auth app
│   ├── templates/accounts/    # Login + Signup pages
│   └── views.py
├── chat/                      # Chat app
│   ├── models.py              # ChatMessage model
│   └── views.py               # AI chat endpoint
├── clauseguard/               # Django config
│   ├── settings.py
│   └── urls.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🌐 URLs

| URL | Description |
|-----|-------------|
| `/` | Upload page |
| `/history/` | All past analyses |
| `/results/<id>/` | Analysis results + chat |
| `/accounts/login/` | Login |
| `/accounts/signup/` | Register |

---

## ⚠️ Disclaimer
ClauseGuard is not a substitute for professional legal advice.
