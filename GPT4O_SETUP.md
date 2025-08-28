# GPT-4o Setup Guide

This guide explains how to configure your Prospector deployment to use GPT-4o instead of GPT-4.

## Changes Made

The AI service has been updated with the following improvements for GPT-4o compatibility:

1. **Configurable Model**: The model can now be set via environment variable
2. **Improved Prompts**: Better JSON formatting instructions
3. **Response Format**: Forces JSON responses for better parsing
4. **Token Limits**: Increased max tokens for GPT-4o
5. **Temperature**: Optimized temperature settings for GPT-4o

## Environment Variables

To use GPT-4o, add this environment variable to your Render deployment:

| Key | Value | Description |
|-----|-------|-------------|
| `OPENAI_MODEL` | `gpt-4o` | Use GPT-4o model |
| `OPENAI_MODEL` | `gpt-4o-mini` | Use GPT-4o-mini (faster, cheaper) |
| `OPENAI_MODEL` | `gpt-4` | Use GPT-4 (default) |

## Setting Up in Render

1. Go to your Render dashboard
2. Navigate to your Prospector web service
3. Click on "Environment" tab
4. Add a new environment variable:
   - **Key**: `OPENAI_MODEL`
   - **Value**: `gpt-4o`
5. Click "Save Changes"
6. Your service will automatically redeploy

## Testing GPT-4o

After deployment:

1. Visit your Render app URL
2. Start a new search job
3. Monitor the results to ensure GPT-4o is working properly

## Troubleshooting

### No Results from GPT-4o

If GPT-4o is returning no results:

1. **Check the model name**: Ensure `OPENAI_MODEL` is set to `gpt-4o`
2. **Check API key**: Verify your OpenAI API key has access to GPT-4o
3. **Check credits**: Ensure your OpenAI account has sufficient credits
4. **Check logs**: Look at Render logs for any error messages

### Fallback to GPT-4

If you encounter issues with GPT-4o, you can fallback to GPT-4:

1. Set `OPENAI_MODEL` to `gpt-4`
2. Redeploy the service

### Debugging

Use the database checking scripts to debug issues:

```bash
# For local debugging (if you have DATABASE_URL set)
python3 check_render_db.py

# For local SQLite database
python3 check_database.py
```

## Model Comparison

| Model | Speed | Cost | Quality | Use Case |
|-------|-------|------|---------|----------|
| `gpt-4o` | Fast | Medium | High | Production use |
| `gpt-4o-mini` | Very Fast | Low | Good | Testing, development |
| `gpt-4` | Slow | High | Very High | When maximum quality needed |

## Cost Considerations

- GPT-4o is generally cheaper than GPT-4
- GPT-4o-mini is the most cost-effective option
- Monitor your OpenAI usage in the OpenAI dashboard

## Performance Tips

1. **Use GPT-4o-mini for testing**: Faster and cheaper for development
2. **Use GPT-4o for production**: Good balance of speed and quality
3. **Monitor response times**: GPT-4o should be significantly faster than GPT-4
4. **Check result quality**: Ensure the results meet your accuracy requirements
