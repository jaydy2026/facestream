# FaceStream - Realtime Face Transformation Platform

**Become anyone in real-time.** Upload a face image and transform your webcam feed instantly.

[![Demo](assets/demo.gif)](https://facestream.phileisen.com)

## Features

- **Real-time Face Swapping** - Transform your webcam feed in real-time using GPU-accelerated cloud processing
- **Low Latency** - Optimized frame pipeline with WebRTC for minimal delay
- **Browser-based** - No installation required, works directly in your browser
- **Mobile Compatible** - Works on iOS Safari and Android Chrome (with TURN server)
- **OBS/Streaming Ready** - Output can be used with virtual camera software

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [Modal](https://modal.com/) account with GPU credits

### Deployment

```bash
# Install dependencies
uv sync

# Deploy to Modal
uv run modal deploy -m facestream.main
```

### Optional: TURN Server for Mobile/Cellular

For WebRTC to work on cellular networks:

1. Create a TURN app on [Cloudflare](https://developers.cloudflare.com/calls/turn/)
2. Create a Modal secret:
   ```bash
   modal secret create facestream \
     TURN_TOKEN_ID=your-turn-token-id \
     TURN_API_TOKEN=your-turn-api-token
   ```
3. Uncomment the secrets section in `src/facestream/main.py`

## Usage

1. Open the deployed application in your browser
2. Upload a face image (JPG, PNG, or HEIC)
3. Grant camera permissions when prompted
4. Watch yourself become the uploaded face in real-time

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
- [MOBILE.md](MOBILE.md) - Mobile usage guide
- [ROADMAP.md](ROADMAP.md) - Future development roadmap

## License

This project uses the INSwapper model from [Deep Live Cam](https://github.com/hacksider/Deep-Live-Cam), which is **for non-commercial use only**.
