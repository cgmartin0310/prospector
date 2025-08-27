# Deploying Prospector to Render

This guide will help you deploy the Prospector application to Render for testing and production use.

## Prerequisites

1. A Render account (sign up at https://render.com)
2. Your code pushed to a GitHub repository
3. An OpenAI API key

## Step 1: Push Code to GitHub

If you haven't already, push your Prospector code to a GitHub repository:

```bash
git init
git add .
git commit -m "Initial Prospector application"
git branch -M main
git remote add origin https://github.com/yourusername/prospector.git
git push -u origin main
```

## Step 2: Create PostgreSQL Database on Render

1. Go to your Render dashboard
2. Click "New" → "PostgreSQL"
3. Fill in:
   - **Name**: `prospector-db`
   - **Database**: `prospector`
   - **User**: `prospector_user`
   - **Region**: Choose closest to your users
   - **PostgreSQL Version**: 15
   - **Plan**: Free (for testing)
4. Click "Create Database"
5. **Important**: Copy the "Internal Database URL" - you'll need this

## Step 3: Deploy Web Service

1. Go to your Render dashboard
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Fill in the deployment settings:

### Basic Settings
- **Name**: `prospector`
- **Region**: Same as your database
- **Branch**: `main`
- **Root Directory**: (leave blank)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### Environment Variables
Add these environment variables in the "Environment" section:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.9.16` |
| `FLASK_ENV` | `production` |
| `DATABASE_URL` | (paste the Internal Database URL from Step 2) |
| `OPENAI_API_KEY` | (your OpenAI API key) |
| `SECRET_KEY` | (Render will auto-generate this) |

### Advanced Settings
- **Plan**: Free (for testing)
- **Auto-Deploy**: Yes

5. Click "Create Web Service"

## Step 4: Monitor Deployment

1. Watch the build logs in real-time
2. The deployment should take 3-5 minutes
3. Once complete, you'll get a live URL like: `https://prospector-abc123.onrender.com`

## Step 5: Test Your Application

1. Visit your Render URL
2. You should see the Prospector dashboard
3. Try creating a new search:
   - Search Query: "overdose response teams"
   - State: North Carolina
   - Start the search and monitor progress

## Troubleshooting

### Common Issues

**Build Fails - Python Version**
- Ensure `PYTHON_VERSION` environment variable is set to `3.9.16`

**Database Connection Error**
- Verify `DATABASE_URL` is correctly set
- Check that both services are in the same region

**OpenAI API Errors**
- Verify your `OPENAI_API_KEY` is valid
- Check your OpenAI account has available credits

**Application Won't Start**
- Check the deployment logs for specific error messages
- Ensure all environment variables are set

### Viewing Logs

1. Go to your web service in Render dashboard
2. Click on "Logs" tab to see application logs
3. Logs update in real-time and show errors

### Database Management

To access your PostgreSQL database:
1. Go to your database service in Render
2. Use the "External Database URL" to connect with tools like pgAdmin
3. Or use the web shell in Render dashboard

## Performance Considerations

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- 750 hours per month (about 31 days)
- Shared resources

### For Production Use
- Upgrade to paid plans for:
  - Always-on services
  - More resources
  - Better performance
  - SSL certificates

## Configuration Options

### Scaling
- Render handles scaling automatically
- For high traffic, consider upgrading plans

### Custom Domain
- Available on paid plans
- Configure in service settings

### SSL/HTTPS
- Automatic on all Render services
- Custom certificates available on paid plans

## Environment Variables Reference

```env
# Required
OPENAI_API_KEY=sk-your-openai-key-here
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional
SECRET_KEY=your-secret-key
FLASK_ENV=production
PYTHON_VERSION=3.9.16
```

## Next Steps

Once deployed successfully:

1. **Test thoroughly** with different search queries
2. **Monitor performance** through Render dashboard
3. **Set up monitoring** for production use
4. **Consider backups** for your database
5. **Review costs** if scaling beyond free tier

## Getting Help

- Render documentation: https://render.com/docs
- Render community: https://community.render.com
- Check application logs for specific errors
