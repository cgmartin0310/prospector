# Quick Deploy to Render

## 1. Push to GitHub

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial Prospector deployment"

# Add your GitHub repository
git remote add origin https://github.com/YOURUSERNAME/prospector.git
git branch -M main
git push -u origin main
```

## 2. Deploy on Render

1. Go to https://render.com and sign in
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Use these settings:

**Basic Settings:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

**Environment Variables:**
```
OPENAI_API_KEY=sk-your-actual-key-here
FLASK_ENV=production
```

5. Click "Create Web Service"

## 3. Optional: Add Database

For persistent data across deployments:

1. Create PostgreSQL database on Render
2. Add `DATABASE_URL` environment variable to your web service

## 4. Test

Your app will be live at: `https://your-service-name.onrender.com`

## Quick Test Checklist

- [ ] App loads without errors
- [ ] Can create new search
- [ ] States dropdown is populated
- [ ] Can submit search form
- [ ] Health check works: `/health`

## Need Help?

See the detailed `RENDER_DEPLOY.md` guide for troubleshooting and advanced configuration.
