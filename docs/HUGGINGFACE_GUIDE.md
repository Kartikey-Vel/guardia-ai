# HuggingFace Audio Inference Setup Guide

This guide explains how to configure and use the HuggingFace Inference API for the Guardia AI audio anomaly detection pipeline.

## 1. Get an API Key
1. Go to [HuggingFace Settings](https://huggingface.co/settings/tokens).
2. Create a new "Read" token.
3. Name it "Guardia-AI-Inference".

## 2. Configure Environment
Add your key to the `.env` file in the `backend/` directory:

```env
# Single key
HUGGINGFACE_API_KEYS="your_hf_token_here"

# Multiple keys (for automatic rotation)
HUGGINGFACE_API_KEYS="token_1,token_2,token_3"
```

## 3. Model Details
Guardia AI uses the following model for audio classification:
- **Model ID**: `MIT/ast-finetuned-audioset-10-10-0.4593`
- **Output**: Multi-label classification (Top 5 labels with scores).
- **Inference Method**: POST request to `https://api-inference.huggingface.co/models/[MODEL_ID]`.

## 4. Troubleshooting
- **429 Rate Limit**: If you hit a rate limit, Guardia AI will automatically rotate to the next key in your `HUGGINGFACE_API_KEYS` list.
- **Model Loading**: The first request might take longer (20-30s) as HuggingFace loads the model into their infrastructure.
- **Audio Format**: The `AudioDetector` expects 16kHz mono `.wav` or raw byte data.

## 5. Security Relevance
The system specifically monitors for the following high-priority sounds from the AudioSet taxonomy:
- `Siren`
- `Explosion`
- `Glass breaking`
- `Crying, sobbing`
- `Screaming`
- `Gunshot, gunfire`
