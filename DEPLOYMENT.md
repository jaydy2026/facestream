# FaceStream Deployment Guide

This guide covers deploying FaceStream to Modal cloud infrastructure.

## Prerequisites

### 1. Modal Account Setup

1. **Create a Modal account** at [modal.com](https://modal.com)
2. **Add payment method** (required for GPU usage)
3. **Install Modal CLI**:
   ```bash
   pip install modal
   # or
   uv add modal
   ```
4. **Authenticate**:
   ```bash
   modal token set
   ```

### 2. GitHub Account

1. Fork or clone this repository to your GitHub account
2. Clone to your local machine:
   ```bash
   git clone https://github.com/YOUR_USERNAME/facestream.git
   cd facestream
   ```

## Deployment Options

### Option 1: Deploy with uv

```bash
# Install dependencies
uv sync

# Deploy to Modal
uv run modal deploy -m facestream.main
```

### Option 2: Deploy with Modal directly

```bash
modal deploy -m facestream.main
```

### Option 3: Development Mode (Local with Remote GPU)

```bash
# This runs the app locally but uses Modal for GPU processing
uv run modal serve facestream.main
```

## Post-Deployment Configuration

### 1. Update Frontend WebSocket URL

After deployment, Modal will provide a URL like:
```
https://YOUR_USERNAME--facestream-main-web.modal.run
```

The frontend in `web/index.html` has a hardcoded URL for the original creator. Update line ~423:

```javascript
// Change from:
const hostname = "philipp-eisen--facestream-main-web.modal.run";

// To your deployment URL (or use dynamic detection):
const hostname = window.location.hostname;
```

### 2. Enable HTTPS (Required for Camera Access)

Modal automatically provides HTTPS, so no additional configuration is needed.

### 3. Create Modal Volume for Model Cache

The first deployment will automatically create the volume `facestream-model-cache`. Models will be downloaded from HuggingFace and cached for future deployments.

## Optional: Cloudflare TURN Server

For mobile devices on cellular networks, you need a TURN server.

### Step 1: Create Cloudflare Account

1. Sign up at [cloudflare.com](https://cloudflare.com)
2. Go to [Cloudflare Calls](https://dash.cloudflare.com/calls)

### Step 2: Create TURN Credentials

1. Create a new TURN app in Cloudflare dashboard
2. Note your `TURN Token ID` and `TURN API Token`

### Step 3: Add Secrets to Modal

```bash
modal secret create facestream \
  TURN_TOKEN_ID=your_turn_token_id \
  TURN_API_TOKEN=your_turn_api_token
```

### Step 4: Enable Secrets in Code

Edit `src/facestream/main.py` and uncomment the secrets section:

```python
@app.cls(
    gpu="T4",
    scaledown_window=60,
    cpu=16,
    timeout=120,
    volumes={
        MODEL_CACHE_DIR: modal.Volume.from_name(
            "facestream-model-cache", create_if_missing=True
        )
    },
    # UNCOMMENT THIS SECTION:
    secrets=[
        modal.Secret.from_name(
            "facestream",
            required_keys=[SECRET_KEY_TURN_TOKEN_ID, SECRET_KEY_TURN_API_TOKEN],
        )
    ],
)
```

### Step 5: Redeploy

```bash
uv run modal deploy -m facestream.main
```

## Environment Variables & Secrets

### Required Secrets

None required for basic operation.

### Optional Secrets

| Secret Name | Key | Description |
|-------------|-----|-------------|
| `facestream` | `TURN_TOKEN_ID` | Cloudflare TURN token ID |
| `facestream` | `TURN_API_TOKEN` | Cloudflare TURN API token |

## Troubleshooting

### Deployment Fails

1. **Authentication Error**: Run `modal token set` to re-authenticate
2. **GPU Quota Exceeded**: Check Modal dashboard for usage limits
3. **Package Not Found**: Ensure `uv sync` completed successfully

### Model Download Fails

Models are downloaded from HuggingFace on first deployment. If this fails:

1. Check your HuggingFace Hub access token (if required)
2. Manually download models:
   ```python
   from facestream.faceswap import FaceSwap
   fs = FaceSwap()  # Triggers download
   ```

### Cold Start Timeout

If the app times out during first use (cold start):

1. Increase timeout in `main.py`:
   ```python
   timeout=300,  # 5 minutes for cold start
   ```
2. Or keep the app warm by making periodic requests

### WebSocket Connection Issues

1. Check browser console for errors
2. Ensure you're using `wss://` (WebSocket Secure)
3. Check Modal logs:
   ```bash
   modal app logs facestream
   ```

### Check Deployment Status

```bash
# View active deployments
modal deploy list

# View logs
modal app logs facestream

# Open Modal dashboard
modal dashboard
```

## Scaling Configuration

### Adjusting Concurrency

Edit `src/facestream/main.py`:

```python
@modal.concurrent(max_inputs=4)  # Increase for more parallel users
class Main:
    ...
```

### GPU Selection

| GPU | VRAM | Speed | Cost |
|-----|------|-------|------|
| T4 | 16GB | Good | Low |
| A10G | 24GB | Better | Medium |
| A100 | 40GB | Best | High |

Change in `main.py`:

```python
@app.cls(
    gpu="A10G",  # Change from "T4"
    ...
)
```

### Scaling to Zero

The `scaledown_window=60` means the app scales to zero after 60 seconds of inactivity. For always-on deployment:

```python
@app.cls(
    scaledown_window=None,  # Never scale to zero
    ...
)
```

## Custom Domain (Optional)

Modal supports custom domains. After setting up DNS:

1. Add domain in Modal dashboard
2. Configure DNS records
3. Update frontend WebSocket URL

## Monitoring & Alerts

### Modal Dashboard

View real-time metrics:
- Request count
- GPU utilization
- Cold start frequency
- Memory usage

### Setting Up Alerts

In Modal dashboard:
1. Go to Settings > Alerts
2. Create alert for:
   - Cold start rate > 20%
   - GPU utilization > 90%
   - Error rate > 5%

## Cost Estimation

| Configuration | Hourly Cost (approx) |
|---------------|---------------------|
| T4 GPU, 4 workers | $0.30 |
| A10G GPU, 4 workers | $0.60 |
| A100 GPU, 4 workers | $1.20 |

### Cost Optimization Tips

1. **Use T4** for personal projects
2. **Set appropriate scaledown_window** to avoid idle charges
3. **Monitor usage** in Modal dashboard
4. **Use free tier** - Modal offers free credits

## Backup & Recovery

### Model Cache

Models are stored in Modal Volume `facestream-model-cache`. They persist across deployments.

To backup:
```bash
modal volume get facestream-model-cache --path / > backup.tar.gz
```

## Security Considerations

1. **No Authentication**: Currently no user auth - anyone can use the app
2. **Video Processing**: All processing is done server-side
3. **No Data Persistence**: Frames are not stored
4. **HTTPS**: All connections are encrypted via Modal's TLS

## Next Steps

- Set up [Cloudflare TURN](MOBILE.md) for mobile support
- Review [Architecture](ARCHITECTURE.md) for understanding
- Check [Roadmap](ROADMAP.md) for future features
