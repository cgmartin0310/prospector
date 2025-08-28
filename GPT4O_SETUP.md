# AI Model Setup Guide

This guide explains how to configure your Prospector deployment to use different AI models (GPT-4o, GPT-5, or GPT-4).

## Changes Made

The AI service has been updated with the following improvements:

1. **Configurable Model**: The model can now be set via environment variable
2. **GPT-5 Support**: Full support for GPT-5 with the new responses API
3. **Improved Prompts**: Model-specific prompts optimized for each AI
4. **Response Format**: Forces JSON responses for better parsing
5. **Token Limits**: Optimized token limits for each model
6. **Temperature**: Model-specific temperature settings

## Environment Variables

To use different models, add this environment variable to your Render deployment:

| Key | Value | Description |
|-----|-------|-------------|
| `OPENAI_MODEL` | `gpt-5` | Use GPT-5 (newest, most capable) |
| `OPENAI_MODEL` | `gpt-4o` | Use GPT-4o (fast, cost-effective) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Use GPT-4o-mini (fastest, cheapest) |
| `OPENAI_MODEL` | `gpt-4` | Use GPT-4 (legacy, high quality) |

## Model Comparison

| Model | Speed | Cost | Quality | Reasoning | Best For |
|-------|-------|------|---------|-----------|----------|
| `gpt-5` | Medium | High | Excellent | Superior | Complex research, accuracy-critical tasks |
| `gpt-4o` | Fast | Medium | High | Good | Production use, balanced performance |
| `gpt-4o-mini` | Very Fast | Low | Good | Basic | Testing, development, cost-sensitive |
| `gpt-4` | Slow | High | Very High | Excellent | When maximum quality needed |

## Setting Up in Render

1. Go to your Render dashboard
2. Navigate to your Prospector web service
3. Click on "Environment" tab
4. Add a new environment variable:
   - **Key**: `OPENAI_MODEL`
   - **Value**: `gpt-5` (or your preferred model)
5. Click "Save Changes"
6. Your service will automatically redeploy

## Model-Specific Features

### GPT-5
- **New Responses API**: Uses the latest OpenAI API
- **Larger Context**: 6000 max tokens
- **Better Reasoning**: Superior at complex tasks
- **More Detailed Prompts**: Enhanced research instructions
- **Higher Confidence**: Default confidence score of 0.95

### GPT-4o
- **Chat Completions API**: Standard OpenAI API
- **Medium Context**: 4000 max tokens
- **Good Balance**: Speed, cost, and quality
- **JSON Response Format**: Forced JSON responses
- **Standard Confidence**: Default confidence score of 0.9

### GPT-4o-mini
- **Fastest**: Optimized for speed
- **Lowest Cost**: Most cost-effective
- **Basic Research**: Good for simple queries
- **Development**: Perfect for testing

## Testing Different Models

After deployment:

1. Visit your Render app URL
2. Start a new search job
3. Monitor the results to compare model performance
4. Check response times and result quality

## Troubleshooting

### No Results from Any Model

If any model is returning no results:

1. **Check the model name**: Ensure `OPENAI_MODEL` is set correctly
2. **Check API key**: Verify your OpenAI API key has access to the model
3. **Check credits**: Ensure your OpenAI account has sufficient credits
4. **Check logs**: Look at Render logs for any error messages

### Model-Specific Issues

**GPT-5 Issues:**
- Ensure you have GPT-5 access (may require waitlist)
- Check if the responses API is working
- Verify your OpenAI account supports GPT-5

**GPT-4o Issues:**
- Check if GPT-4o is available in your region
- Verify API key permissions
- Check for rate limiting

### Fallback Strategy

If you encounter issues with one model, you can fallback:

1. Set `OPENAI_MODEL` to a different model
2. Redeploy the service
3. Test with the new model

### Debugging

Use the database checking scripts to debug issues:

```bash
# For local debugging (if you have DATABASE_URL set)
python3 check_render_db.py

# For local SQLite database
python3 check_database.py
```

## Cost Considerations

| Model | Relative Cost | Use Case |
|-------|---------------|----------|
| `gpt-5` | High | When maximum accuracy is critical |
| `gpt-4o` | Medium | Production use, good balance |
| `gpt-4o-mini` | Low | Testing, development, cost-sensitive |
| `gpt-4` | Very High | Legacy applications |

## Performance Tips

1. **Start with GPT-4o**: Good balance for most use cases
2. **Use GPT-5 for critical research**: When accuracy is paramount
3. **Use GPT-4o-mini for testing**: Fast and cheap for development
4. **Monitor costs**: Track usage in OpenAI dashboard
5. **Compare results**: Test different models on the same queries

## Recommended Strategy

### For Production Use:
- **Primary**: `gpt-4o` (good balance)
- **Fallback**: `gpt-4o-mini` (if cost becomes an issue)
- **Premium**: `gpt-5` (for critical research tasks)

### For Development/Testing:
- **Primary**: `gpt-4o-mini` (fast and cheap)
- **Validation**: `gpt-4o` (to verify results)

### For Maximum Quality:
- **Primary**: `gpt-5` (best reasoning and accuracy)
- **Fallback**: `gpt-4o` (if GPT-5 has issues)
