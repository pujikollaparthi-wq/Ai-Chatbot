# Deployment Guide: GitHub & Render

Entire AI Chatbot Enterprise Platform ni GitHub loki push chesi Render lo deploy cheyadaniki complete steps:

---

## 1. Project lo Ready Chesina Configuration Files
Deployment kosam already project lo kinda files setup chesam:
1. **`.gitignore`**: Virtual environment (`.venv`), SQLite database (`db.sqlite3`), sensitive `.env` files Git loki vellakunda exclude cheyabadindi.
2. **`requirements.txt`**: Production WSGI server `gunicorn` mariyu static files kosam `whitenoise` add cheyabadindi.
3. **`enterprise_platform/settings.py`**:
   - `whitenoise.middleware.WhiteNoiseMiddleware` add ayindi.
   - `STATICFILES_STORAGE` mariyu `CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']` configure cheyabadindi.
4. **`Procfile`**: Render web process kosam `web: gunicorn enterprise_platform.wsgi:application` create cheyabadindi.
5. **`build.sh`**: Render build time lo packages install chesi, migrations mariyu static files collect cheyadaniki script create cheyabadindi.
6. **Local Git Commit**: Project clean ga `main` branch lo commit ayi undi.

---

## 2. GitHub loki Push Chese Vidhanam

1. **GitHub lo New Repository Create Cheyandi**:
   - [GitHub New Repository](https://github.com/new) open cheyandi.
   - **Repository Name**: e.g., `ai-chatbot-platform` (or your preferred name).
   - Visibility: **Public** or **Private**.
   - *"Initialize this repository with a README"* checkbox ni **UNCHECK** cheyandi (empty repo ga create cheyandi).
   - Click **Create repository**.

2. **Repository URL ni Link chesi Push Cheyandi**:
   VS Code terminal lo (project path `AI CHATBOT` lo) kinda commands run cheyandi (replace `YOUR-USERNAME` and `REPO-NAME`):
   ```bash
   git remote add origin https://github.com/<YOUR-USERNAME>/<REPO-NAME>.git
   git push -u origin main
   ```
   *(GitHub credentials / token adigithe login credentials enter cheyandi)*.

---

## 3. Render.com lo Deploy Chese Vidhanam

1. **Render.com ki Login avvandi**:
   - [render.com](https://render.com) open chesi మీ GitHub account tho **Sign in** avvandi.

2. **Create Web Service**:
   - Render Dashboard lo **New +** button click chesi **Web Service** select cheyandi.
   - **Build and deploy from a Git repository** option click chesi **Next** click cheyandi.
   - మీ GitHub repository (`ai-chatbot-platform`) ni select chesi **Connect** click cheyandi.

3. **Configure Web Service Settings**:
   - **Name**: `ai-chatbot-enterprise` (or any unique name)
   - **Region**: Singapore / Frankfurt (or default)
   - **Branch**: `main`
   - **Root Directory**: *(Empty ga vadileyandi)*
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     chmod +x build.sh && ./build.sh
     ```
   - **Start Command**:
     ```bash
     gunicorn enterprise_platform.wsgi:application
     ```
   - **Instance Type**: `Free`

4. **Environment Variables Add Cheyandi (Crucial)**:
   Same page lo kinda **Environment Variables** section lo kindavi add cheyandi:
   - `DEBUG`: `False`
   - `SECRET_KEY`: *(Any long random secret string, e.g., `django-prod-render-secure-key-993847`)*
   - `ALLOWED_HOSTS`: `*`
   - `GEMINI_API_KEY`: *(మీ Google Gemini API Key)*
   - `OPENAI_API_KEY`: *(మీ OpenAI API Key - optional)*

5. **Deploy**:
   - Click **Deploy Web Service**.
   - Render logs lo build progress kanipisthundi. Once completed, Render meeku live URL istundi (e.g., `https://ai-chatbot-enterprise.onrender.com`).
   - Aa URL open chesthe live lo మీ Enterprise AI Chatbot Platform work avthundi!
