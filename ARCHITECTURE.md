# FaceStream Architecture Report

## Overview

FaceStream is a realtime face swapping web application that leverages WebRTC for low-latency video streaming and GPU-accelerated cloud processing for face swapping. The system enables users to upload a reference face image and then have their webcam feed processed in real-time to replace faces with the uploaded identity.

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │   Webcam    │───▶│ getUserMedia() │───▶│ RTCPeerConnection (send)   │  │
│  │   (Media)   │    │   Local Video   │    │   WebRTC Video Track        │  │
│  └─────────────┘    └─────────────────┘    └──────────────┬──────────────┘  │
│         │                                                    │                │
│         │ Mirror                                             │ Stream         │
│         ▼                                                    ▼                │
│  ┌─────────────┐                                    ┌─────────────────┐    │
│  │ localVideo  │                                    │   WebSocket     │    │
│  │  (Preview)  │                                    │   /ws endpoint  │    │
│  └─────────────┘                                    └────────┬────────┘    │
│                                                              │                │
└───────────────────────────────────────────────────────────────│───────────────┘
                                                               │
                                                               │ WebSocket
                                                               │ JSON/WebRTC
                                                               │ Signaling
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVER (Modal Cloud)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI ASGI Server                            │   │
│  │  ┌─────────────┐    ┌─────────────────┐    ┌───────────────────────┐ │   │
│  │  │  WebSocket  │───▶│ Signaling Logic│───▶│ RTCPeerConnection     │ │   │
│  │  │   Handler   │    │ - Image Upload │    │ - Answer Creation     │ │   │
│  │  │  /ws route   │    │ - Offer/Answer  │    │ - ICE Candidate Exch │ │   │
│  │  └─────────────┘    │ - ICE Handling  │    └───────────┬───────────┘ │   │
│  │                     └─────────────────┘                │             │   │
│  └─────────────────────────────────────────────────────────┼─────────────┘   │
│                                                              │                 │
│  ┌──────────────────────────────────────────────────────────▼─────────────┐   │
│  │                     ProcessFrameTrack (aiortc)                        │   │
│  │  - Wraps MediaStreamTrack                                              │   │
│  │  - Queue-based frame processing                                        │   │
│  │  - Frame dropping for latency management                               │   │
│  └────────────────────────────────────────┬───────────────────────────────┘   │
│                                           │                                     │
│                                           │ Frame Processing                     │
│                                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                          FaceSwap Service                              │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────────┐  │   │
│  │  │ InsightFace     │    │ INSwapper Model │    │ CUDA Execution    │  │   │
│  │  │ FaceAnalysis    │───▶│ (inswapper_     │───▶│ Provider          │  │   │
│  │  │ (buffalo_l)     │    │  128_fp16.onnx) │    │ (GPU T4)          │  │   │
│  │  └─────────────────┘    └─────────────────┘    └───────────────────┘  │   │
│  │                                                                           │   │
│  │  Processing Pipeline:                                                   │   │
│  │  1. Face Detection (FaceAnalysis)                                       │   │
│  │  2. Face Swapping (INSwapper)                                           │   │
│  │  3. Image Compositing (paste_back=True)                                  │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        WebRTC Video Return                              │  │
│  │  - Processed VideoFrame returned via RTCPeerConnection                  │  │
│  │  - Browser displays in remoteVideo element                               │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Analysis

### 1. Frontend (web/index.html)

#### Technologies
- Vanilla JavaScript (no framework)
- WebRTC via native browser APIs
- HEIC image support via heic2any library

#### Key Components

**State Management:**
- `ws` - WebSocket connection
- `pc` - RTCPeerConnection
- `source_face` - Uploaded face image data (on server side)

**Functions:**
| Function | Purpose |
|----------|---------|
| `resizeImage(file, maxWidth)` | Resize and compress uploaded images to max 800px width |
| `convertHeicToJpeg(file)` | Convert HEIC format images to JPEG |
| `start()` | Initialize WebSocket connection and event handlers |
| `startVideoStream(iceServers)` | Create WebRTC peer connection and start streaming |
| `selectPresetImage(imageUrl)` | Handle preset face image selection |
| `triggerFileInput()` | Trigger file upload dialog |

**WebRTC Flow:**
1. Connect to WebSocket at `/ws`
2. Upload face image via `upload_image` message
3. Receive `readyForStream` with ICE servers
4. Call `getUserMedia()` for webcam access
5. Create `RTCPeerConnection` with ICE servers
6. Send `offer` via WebSocket
7. Receive `answer` and set remote description
8. Exchange ICE candidates
9. Receive remote stream in `remoteVideo` element

**Mobile Considerations:**
- Responsive CSS with viewport meta tag
- Adjusted sizing for mobile viewports
- MediaDevices API feature detection

### 2. Backend - Main Entry (src/facestream/main.py)

#### Modal Configuration
```python
@app.cls(
    gpu="T4",                    # NVIDIA T4 GPU for inference
    scaledown_window=60,          # Scale to zero after 60 seconds idle
    cpu=16,                       # 16 vCPU for processing
    timeout=120,                  # 2 minute timeout per request
    volumes={
        MODEL_CACHE_DIR: modal.Volume.from_name(...)
    }
)
```

#### WebSocket Protocol

**Client → Server Messages:**

| Type | Payload | Description |
|------|---------|-------------|
| `ping` | - | Keep-alive, server responds with `pong` |
| `upload_image` | `{image: base64string}` | Upload face image for swapping |
| `offer` | `{sdp: string}` | WebRTC SDP offer |
| `candidate` | `{candidate, sdpMid, sdpMLineIndex}` | ICE candidate |

**Server → Client Messages:**

| Type | Payload | Description |
|------|---------|-------------|
| `pong` | - | Acknowledgment of ping |
| `readyForStream` | `{iceServers: [...]}` | Image processed, ready for video |
| `answer` | `{sdp: string}` | WebRTC SDP answer |
| `candidate` | `{candidate, sdpMid, sdpMLineIndex}` | ICE candidate |

#### ICE Server Configuration

**Without Cloudflare TURN:**
```json
{"urls": "stun:stun.l.google.com:19302"}
```

**With Cloudflare TURN:**
- Fetches credentials from Cloudflare RTC API
- Required for cellular networks
- Requires `TURN_TOKEN_ID` and `TURN_API_TOKEN` secrets

### 3. Frame Processing (src/facestream/track.py)

#### ProcessFrameTrack Class

A custom `MediaStreamTrack` that wraps another track and applies frame processing:

```python
class ProcessFrameTrack(MediaStreamTrack):
    kind = "video"
    
    def __init__(self, track, process_frame):
        self.input_queue = asyncio.Queue(maxsize=3)   # Max 3 frames buffered
        self.output_queue = asyncio.Queue(maxsize=1)   # Latest frame only
```

**Latency Management Strategy:**
- Input queue size: 3 frames (drop oldest if full)
- Output queue size: 1 frame (keep only latest)
- Frame dropping when processing can't keep up
- Async processor task maintains pipeline

**Frame Processing Flow:**
```
Frame N received → input_queue.put() → [PROCESSOR] → output_queue.put() → recv() returns
                                               ↓
                                      If queue full, drop oldest
```

### 4. Face Swap Engine (src/facestream/faceswap.py)

#### Model Architecture

**Face Analysis Model:**
- Model: `buffalo_l` from InsightFace
- Purpose: Face detection and landmark extraction
- Detection size: 640x640 pixels
- Execution: CUDA GPU

**Face Swapping Model:**
- Model: `inswapper_128_fp16.onnx` from Deep Live Cam
- Source: HuggingFace Hub (`hacksider/deep-live-cam`)
- Format: ONNX with FP16 precision
- Execution: CUDA GPU

#### Processing Pipeline

```python
def _swap_face(self, target: np.ndarray, source_face: dict):
    # 1. Get target face from frame
    target_face = self._get_one_face(target)
    
    # 2. Swap using INSwapper
    result = self.faceswap_model.get(
        target,           # Target image
        target_face,      # Face to replace
        source_face,      # Source identity
        paste_back=True  # Blend result back
    )
    
    return result
```

**Key Parameters:**
- `paste_back=True`: Composites the swapped face back onto the original image with proper blending
- Face selection: `min(faces, key=lambda x: x.bbox[0])` - selects leftmost face

#### Async Wrapping

All blocking operations are wrapped in `run_in_executor` for async compatibility:
- `get_one_face()` - Face detection
- `swap_face()` - Face swapping

### 5. Configuration (src/facestream/constants.py)

```python
MODEL_CACHE_DIR = "/root/models"  # Volume mount point for cached models

SECRET_KEY_TURN_TOKEN_ID = "TURN_TOKEN_ID"
SECRET_KEY_TURN_API_TOKEN = "TURN_API_TOKEN"
```

## Deployment Architecture

### Modal Infrastructure

```
┌─────────────────────────────────────────────────────────────────┐
│                        Modal Cloud                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Modal App: facestream                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                 │  │
│  │  │  ASGI Server    │  │  GPU Worker     │                 │  │
│  │  │  (FastAPI)      │──│  (T4, 16CPU)    │                 │  │
│  │  │  Port 80        │  │  Max 4 concurrent│                │  │
│  │  └─────────────────┘  └─────────────────┘                 │  │
│  │           │                                    │           │  │
│  │           │                                    │           │  │
│  │           ▼                                    ▼           │  │
│  │  ┌─────────────────┐              ┌─────────────────┐      │  │
│  │  │  WebSocket      │              │  Model Cache    │      │  │
│  │  │  /ws            │              │  Volume         │      │  │
│  │  └─────────────────┘              │  /root/models   │      │  │
│  │                                    └─────────────────┘      │  │
│  │                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Model Caching Strategy

1. On first cold start, models are downloaded from HuggingFace Hub
2. Models cached in Modal Volume (`facestream-model-cache`)
3. Subsequent cold starts use cached models
4. Volume persists across deployments

### Scaling Behavior

- **Scaledown Window**: 60 seconds (scales to zero when idle)
- **Max Concurrency**: 4 (configured via `@modal.concurrent(max_inputs=4)`)
- **Cold Start**: ~30-60 seconds (model loading)
- **Warm Response**: <100ms per frame (GPU inference)

## WebRTC Signaling Flow

```
┌──────────┐                        ┌──────────┐                        ┌──────────┐
│  Client  │                        │ WebSocket │                        │   GPU    │
│ Browser  │                        │  Server   │                        │ Worker   │
└────┬─────┘                        └────┬─────┘                        └────┬─────┘
     │                                     │                                  │
     │ 1. WebSocket Connect                │                                  │
     │─────────────────────────────────────▶│                                  │
     │                                     │                                  │
     │ 2. upload_image (base64)             │                                  │
     │─────────────────────────────────────▶│                                  │
     │                                     │──── Face Detection ──────────────▶│
     │                                     │◀─── Source Face Data ─────────────│
     │                                     │                                  │
     │ 3. readyForStream (iceServers)      │                                  │
     │◀─────────────────────────────────────│                                  │
     │                                     │                                  │
     │ 4. getUserMedia() - webcam          │                                  │
     │                                     │                                  │
     │ 5. RTCPeerConnection.createOffer()  │                                  │
     │                                     │                                  │
     │ 6. offer (sdp)                      │                                  │
     │─────────────────────────────────────▶│                                  │
     │                                     │──── WebRTC Track Setup ─────────▶│
     │                                     │                                  │
     │ 7. answer (sdp)                     │                                  │
     │◀─────────────────────────────────────│                                  │
     │                                     │                                  │
     │ 8. ICE Candidates (candidate)       │                                  │
     │◀─────────────────────────────────────│                                  │
     │                                     │                                  │
     │ 9. ◄══ Video Stream (SRTP) ══►       │                                  │
     │    Frames go to GPU Worker ────────────────────▶│                      │
     │◀── Processed Frames ─────────────────────────────────────────│
     │                                     │                                  │
     ▼                                     ▼                                  ▼
```

## Required Services & Accounts

### Mandatory

1. **Modal Account**
   - For deployment and hosting
   - Free tier available with GPU credits
   - Configure with `modal token set`

### Optional (for Mobile/Cellular)

2. **Cloudflare Account** (for TURN server)
   - Cloudflare Calls TURN app
   - Requires `TURN_TOKEN_ID` and `TURN_API_TOKEN`
   - Enables WebRTC on cellular networks

### Required Tools

1. **uv** - Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Git** - Version control

3. **GitHub Account** - For hosting the fork

## Latency Analysis

### Latency Breakdown

| Component | Typical Latency | Notes |
|-----------|----------------|-------|
| Camera capture | 33ms | 30 FPS = 33.3ms per frame |
| WebRTC encoding | 5-10ms | H.264/VP8 compression |
| Network (client→server) | 20-100ms | Depends on geography |
| GPU inference | 30-50ms | T4 GPU with ONNX |
| WebRTC encoding (return) | 5-10ms | |
| Network (server→client) | 20-100ms | |
| Browser rendering | 8-16ms | 60-120 FPS display |

**Total Estimated Latency:** 120-320ms

### Bottleneck Points

1. **GPU Inference**: 30-50ms per frame is the primary bottleneck
2. **Network Latency**: Round-trip time between client and Modal servers
3. **Frame Queue**: Buffering can add 1-3 frames of latency

### Optimization Strategies

1. **Frame Dropping**: Skip frames when processing can't keep up
2. **Resolution Scaling**: Lower resolution = faster processing
3. **Model Optimization**: FP16 precision already used
4. **Concurrent Processing**: 4 parallel inference workers

## Dependencies Analysis

### Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `insightface` | 0.7.3 | Face analysis and swapping |
| `onnxruntime-gpu` | 1.16.3 | ONNX model execution |
| `opencv-python` | 4.11+ | Image processing |
| `torch` | 2.0.1 | GPU tensor operations |
| `aiortc` | 1.9+ | WebRTC implementation |
| `fastapi` | 0.115+ | ASGI web framework |
| `huggingface-hub` | 0.27+ | Model download |

### External Resources

| Resource | Location | Purpose |
|----------|----------|---------|
| INSwapper Model | HuggingFace `hacksider/deep-live-cam` | Face swapping |
| Buffalo_l Model | InsightFace Zoo | Face detection |
| Google STUN | `stun.l.google.com:19302` | NAT traversal |
| Cloudflare TURN | `rtc.live.cloudflare.com` | NAT traversal (optional) |

## Security Considerations

1. **No Authentication**: Currently no user authentication
2. **Image Processing**: All processing happens in isolated Modal environment
3. **WebRTC**: Media streams are peer-to-peer
4. **Secrets**: TURN credentials stored as Modal secrets
5. **Model Download**: Models downloaded over HTTPS from HuggingFace

## Future Architecture Considerations

### Identity Preservation Improvements

The current INSwapper model can leak source features. Potential improvements:

1. **Post-processing Filters**:
   - Skin tone matching/transfer
   - Face restoration models (GFPGAN, CodeFormer)
   - Skin smoothing filters

2. **Model Alternatives**:
   - Supeer: Enhanced face swapping
   - Roop: Alternative implementation
   - ComfyUI workflows

3. **Blend Control**:
   - Adjustable identity strength
   - Expression transfer controls

### Realtime Model Alternatives

| Model | Latency | Quality | Commercial Use |
|-------|---------|---------|----------------|
| INSwapper (current) | Low | Good | Non-commercial |
| Lucy 2.1 | Low | Higher | Commercial available |
| FAL Realtime | Low | High | Commercial |

### Scalability Options

1. **Multiple Modal Regions**: Deploy in multiple regions
2. **Auto-scaling**: Configure Modal for higher concurrency
3. **CDN**: Serve static assets via CDN
4. **Load Balancing**: Multiple GPU instances behind same endpoint

## Browser Compatibility

### Desktop Browsers
- Chrome 56+ (WebRTC, MediaDevices)
- Firefox 44+ (WebRTC, MediaDevices)
- Safari 11+ (WebRTC, MediaDevices)
- Edge 79+ (WebRTC, MediaDevices)

### Mobile Browsers
- Chrome Android (with permissions)
- Safari iOS 14.5+ (with permissions)
- Requires HTTPS for camera access
- TURN server recommended for cellular

### Permissions Required
- Camera access (`getUserMedia`)
- Microphone access (audio passthrough)
