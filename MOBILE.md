# FaceStream Mobile Usage Guide

## Browser Compatibility

FaceStream is designed to work on mobile devices with modern browsers:

| Browser | Platform | Support Level | Notes |
|---------|----------|---------------|-------|
| Chrome | Android | Full | Recommended |
| Safari | iOS 14.5+ | Full | Requires HTTPS |
| Firefox | Android | Partial | May have issues |
| Edge | Android | Partial | May have issues |

## Requirements for Mobile

### 1. HTTPS Connection

Camera access via `getUserMedia()` requires HTTPS. Modal provides HTTPS automatically.

If using a custom domain, ensure SSL certificate is valid.

### 2. Camera Permissions

On mobile, users will be prompted for camera access:

```
"[App Name] wants to access your camera"
```

- **iOS**: Settings > Privacy > Camera > [Browser] > Allow
- **Android**: Settings > Apps > [Browser] > Permissions > Camera > Allow

### 3. TURN Server (Cellular Networks)

**Critical for cellular networks.** Without TURN, WebRTC will fail on most mobile carriers.

### 4. Stable Internet Connection

Recommended minimum:
- **Download**: 5 Mbps
- **Upload**: 2 Mbps
- **Latency**: < 100ms

## TURN Server Setup for Mobile

### Why TURN is Required

WebRTC uses ICE (Interactive Connectivity Establishment) to establish peer connections:

1. **STUN**: Discovers public IP (works on WiFi)
2. **TURN**: Relays traffic through server (required for cellular)

Most cellular networks use symmetric NAT or port restrictions that prevent direct peer connections.

### Cloudflare TURN Setup

#### Step 1: Create Cloudflare Account

1. Go to [cloudflare.com](https://cloudflare.com) and sign up
2. Navigate to [Cloudflare Calls](https://dash.cloudflare.com/calls)

#### Step 2: Create TURN App

1. Click "Create TURN App"
2. Configure:
   - **App Name**: facestream
   - **Allowed Origins**: Your deployed domain
   - **TTL**: 86400 (24 hours)
3. Copy the credentials:
   - `TURN Token ID`
   - `TURN API Token`

#### Step 3: Add Secrets to Modal

```bash
# Install Modal CLI if not already installed
pip install modal

# Login to Modal
modal token set

# Create secret
modal secret create facestream \
  TURN_TOKEN_ID=your_turn_token_id \
  TURN_API_TOKEN=your_turn_api_token
```

#### Step 4: Enable Secrets in Code

Edit `src/facestream/main.py`:

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
    # ENABLE THIS SECTION:
    secrets=[
        modal.Secret.from_name(
            "facestream",
            required_keys=[SECRET_KEY_TURN_TOKEN_ID, SECRET_KEY_TURN_API_TOKEN],
        )
    ],
)
```

#### Step 5: Redeploy

```bash
uv run modal deploy -m facestream.main
```

## Mobile Usage Steps

### Android (Chrome)

1. **Open Chrome** on your Android device
2. **Navigate** to your FaceStream deployment URL
3. **Tap** the upload button
4. **Grant camera permission** when prompted
5. **Select** a face image from gallery
6. **Allow** video access
7. **View** the transformed video

### iOS (Safari)

1. **Open Safari** on your iPhone/iPad
2. **Navigate** to your FaceStream deployment URL
3. **Tap** the upload button
4. **Allow** camera access when prompted
5. **Select** a face image
6. **View** the transformed video

**Note**: iOS Safari requires HTTPS. Ensure your deployment uses HTTPS.

## Known Issues on Mobile

### FaceStream May Not Work On

- Private/Incognito mode (camera blocked)
- Low memory devices (may crash)
- Very old iOS/Android versions
- Devices without cameras

### Performance Considerations

| Issue | Cause | Solution |
|-------|-------|----------|
| High latency | Network congestion | Use WiFi instead of cellular |
| Frame drops | Slow device | Reduce video quality |
| App crash | Memory limit | Close other apps |
| Black screen | Permission denied | Check settings |

## Troubleshooting Mobile Issues

### "Camera not available" Error

1. Check browser has camera permission
2. Try a different browser (Chrome recommended)
3. Restart the browser/app
4. Check device isn't in low-power mode

### WebRTC Connection Failed

1. **On WiFi**: Usually works without TURN
2. **On Cellular**: TURN server required - see setup above
3. Check internet connection stability
4. Try a different network

### Very Laggy Video

1. Check network speed
2. Reduce video quality:
   - Lower resolution in `web/index.html`
   - Change `ideal: 1280` to `ideal: 640`
3. Move closer to WiFi router

### Image Upload Fails

1. Check file format (JPG, PNG, HEIC supported)
2. Check file size (max ~10MB recommended)
3. Try a smaller image
4. Check internet connection

## Optimizing for Mobile

### Reduce Video Resolution

Edit `web/index.html` to request lower resolution:

```javascript
const stream = await navigator.mediaDevices.getUserMedia({
  video: {
    width: { min: 320, ideal: 640, max: 1280 },  // Reduce here
    height: { min: 240, ideal: 480, max: 720 },  // Reduce here
  },
});
```

### Add Mobile-Specific Styles

The frontend already has mobile-responsive CSS. To customize:

```css
@media (max-width: 768px) {
  /* Mobile-specific styles */
  #localVideo {
    width: 100px;  /* Smaller preview on mobile */
    height: 133px;
  }
}
```

## Testing Mobile

### Test Your Deployment

1. Deploy to Modal (see DEPLOYMENT.md)
2. Test on desktop first
3. Test on mobile WiFi
4. Test on mobile cellular (with TURN server)

### Test Checklist

- [ ] Page loads correctly
- [ ] Upload button works
- [ ] Camera permission prompts
- [ ] Face detection works
- [ ] Video streams smoothly
- [ ] No connection drops
- [ ] Works on WiFi
- [ ] Works on cellular (with TURN)

## Security & Privacy

### Data Handling

- **Video Processing**: All processing happens server-side on Modal GPU
- **No Storage**: Frames are not stored or logged
- **Peer-to-Peer**: Video goes directly from browser to server
- **WebRTC Encryption**: All video is encrypted in transit

### Permissions

FaceStream requests:
- **Camera**: For video capture
- **Microphone**: Audio passthrough (not processed)

### Privacy Tips

1. Use HTTPS (always on Modal)
2. Review browser permissions
3. Clear site data when done
4. Don't use on public networks without VPN

## Emergency Backup

If FaceStream doesn't work on your mobile device:

1. Use a desktop/laptop instead
2. Use OBS Virtual Camera on desktop
3. Try a different browser
4. Wait for future mobile optimization updates

## Future Mobile Improvements

See [ROADMAP.md](ROADMAP.md) for planned mobile enhancements:
- Progressive Web App (PWA) support
- Native app wrapper
- Reduced bandwidth mode
- Better mobile UI/UX
