# Guardia AI — API Key Management & Rotation

Guardia AI implements a robust, multi-agent AI pipeline. To ensure maximum uptime and bypass single-key quota limits, the system uses a **Key Rotation Pattern**.

## Configuration Pattern
API keys are configured in the `backend/.env` file as comma-separated strings.

```env
# Pluralized variables
GEMINI_API_KEYS="key_a,key_b"
GROQ_API_KEYS="key_c"
HUGGINGFACE_API_KEYS="key_d,key_e"
```

## How Rotation Works
1. **KeyRotator Utility**: A singleton class (`ai/utils.py`) maintains an index of available keys for each service.
2. **Error Interception**: If an AI provider returns a `429` (Quota Exceeded) or `401` (Unauthorized) error, the AI client catches the exception.
3. **Automatic Switch**: The client calls `rotator.rotate('SERVICE_NAME')` and immediately retries the request with the next key.
4. **Round-Robin**: The rotator loops back to the first key once the list is exhausted.

## Security Best Practices
- **Environment Isolation**: Never commit `.env` files to git. Use the `git-crypt` or similar tools for production.
- **Minimal Scope**: Use specific API keys for the HuggingFace Inference API rather than full administrative tokens.
- **Quota Monitoring**: Monitor usage in the [Google AI Studio](https://aistudio.google.com/app/apikey) and [Groq Console](https://console.groq.com/keys) to balance the number of keys needed.

## Fallback Logic
If **all** keys for a service fail or are missing:
- **Vision**: Falls back to "Rule-based object description".
- **Fusion**: Falls back to "Motion-only heuristic assessment".
- **Audio**: Skips audio signal processing and continues with visual data.
