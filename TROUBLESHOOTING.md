# FaceStream Troubleshooting Guide

## Quick Diagnosis

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|----------|
| "Camera not found" | Permission denied | Check browser settings |
| "WebSocket error" | Server not running | Deploy or restart Modal |
| Face not detected | Poor image quality | Upload clearer photo |
| Identity leaking | Enhancement settings | Increase identity_strength |
| Very slow | Network/GPU issue | Check Modal dashboard |
| Black screen | HTTPS required | Use HTTPS URL |

## Webcam Issues

### Camera Permission Denied

**Symptoms:** "Camera not available" error or no video stream

**Solutions:**

1. **Browser Settings**
   - Chrome: Settings > Privacy > Camera > Allow
   - Firefox: Settings > Permissions > Camera > Allow
   - Safari: Preferences > Websites > Camera > Allow

2. **System Settings**
   - macOS: System Preferences > Security & Privacy > Camera
   - Windows: Settings > Privacy > Camera
   - Linux: Check camera is not blocked by another app

3. **Site Permissions**
   - Click the lock icon in address bar
   - Enable Camera access

### Camera Works But No Video

**Solutions:**

1. Check if another app is using the camera
2. Try a different browser
3. Restart the browser
4. Clear browser cache

## WebSocket/Connection Issues

### "WebSocket Error" or Connection Failed

**Symptoms:** Error message or page reloads automatically

**Solutions:**

1. **Check Server Status**
   ```bash
   modal app logs facestream
   ```

2. **Check URL**
   - Ensure using `https://` not `http://`
   - Check the Modal deployment URL is correct

3. **Check Network**
   - Try a different network
   - Disable VPN temporarily
   - Check firewall settings

4. **Cold Start Timeout**
   - First connection may timeout (30-60 seconds)
   - Subsequent connections should be faster
   - Increase timeout in code if needed

### "Session ended" Message

**Solutions:**

1. Check internet connection stability
2. Reduce video quality if bandwidth is low
3. Enable TURN server for cellular networks
4. Check Modal for cold start issues

## Face Detection Issues

### "Face not detected" Error

**Symptoms:** Source image upload fails or face not found

**Solutions:**

1. **Image Quality**
   - Use high-resolution images
   - Avoid heavily compressed JPEGs
   - Ensure face is clearly visible

2. **Lighting**
   - Good lighting improves detection
   - Avoid shadows on face
   - Avoid backlighting

3. **Face Position**
   - Frontal face works best
   - Avoid extreme angles
   - Ensure both eyes are visible

4. **Image Format**
   - JPG, PNG, HEIC supported
   - Convert HEIC to JPG if needed

### Multiple Faces Detected

**Current Behavior:** Uses the leftmost face in the frame

**Future:** Will add face selection UI

## Identity Preservation Issues

### Source Features Leaking (Beard, Hair, etc.)

**Symptoms:** Output doesn't fully match uploaded face

**Solutions:**

1. **Increase Identity Strength**
   ```python
   # In constants.py
   IDENTITY_STRENGTH = 0.9  # Increase from 0.7
   ```

2. **Enable Skin Tone Matching**
   ```python
   SKIN_TONE_MATCH = True
   ```

3. **Enable Face Enhancement**
   ```python
   FACE_ENHANCE = True  # Adds latency
   ```

4. **Use Better Source Images**
   - High quality reference photo
   - Clear, frontal face
   - Good lighting
   - Natural expression

### Output Quality Issues

**Symptoms:** Blurry, distorted, or unnatural output

**Solutions:**

1. **Enable Face Enhancement**
   ```python
   FACE_ENHANCE = True
   ```

2. **Adjust Skin Smoothing**
   ```python
   SKIN_SMOOTHING = True
   ```

3. **Check Source Image Quality**
   - Use higher resolution source
   - Ensure clear, focused photo

## Mobile Issues

### Not Working on Mobile

**Symptoms:** Can't connect, no video, or very slow

**Solutions:**

1. **Enable TURN Server** (Required for cellular)
   - Set up Cloudflare TURN credentials
   - Add secrets to Modal
   - Redeploy

2. **Check Browser Compatibility**
   - Chrome Android: Full support
   - Safari iOS 14.5+: Full support
   - Avoid private/incognito mode

3. **Reduce Video Quality**
   ```javascript
   // In web/index.html, change:
   width: { min: 320, ideal: 640 }  // Lower resolution
   frameRate: { ideal: 15 }         // Lower FPS
   ```

4. **Check Network**
   - WiFi recommended for best results
   - Stable connection required

### Poor Mobile Performance

**Symptoms:** Laggy video, frame drops, disconnections

**Solutions:**

1. **Close Other Apps**
   - Free up device memory
   - Reduce background processes

2. **Lower Video Quality**
   - Reduce resolution
   - Reduce frame rate

3. **Use WiFi**
   - Cellular has higher latency
   - Unstable connection causes issues

## Deployment Issues

### Modal Deployment Fails

**Symptoms:** `modal deploy` command fails

**Solutions:**

1. **Authentication**
   ```bash
   modal token set
   ```

2. **Dependencies**
   ```bash
   uv sync
   ```

3. **GPU Quota**
   - Check Modal dashboard for quota
   - May need to add payment method

4. **Volume Issues**
   ```bash
   # Recreate volume if needed
   modal volume create facestream-model-cache
   ```

### Model Download Fails

**Symptoms:** Cold start timeout, model not found

**Solutions:**

1. **Check HuggingFace Access**
   - Models downloaded from HuggingFace
   - May need authentication for some models

2. **Manual Download**
   ```python
   from facestream.faceswap import FaceSwap
   fs = FaceSwap()  # Triggers download
   ```

3. **Volume Mount Issues**
   - Check volume is properly configured
   - Ensure write permissions

## Performance Issues

### High Latency

**Symptoms:** Noticeable delay between movement and output

**Solutions:**

1. **Reduce Video Quality**
   - Lower resolution
   - Lower frame rate

2. **Disable Face Enhancement**
   ```python
   FACE_ENHANCE = False
   ```

3. **Check Network**
   - Closer server = lower latency
   - Modal servers are in us-east-1

4. **GPU Utilization**
   - Check Modal dashboard
   - May need to scale workers

### Frame Drops

**Symptoms:** Video stutters or skips frames

**Solutions:**

1. **Check GPU Resources**
   - Modal T4 should handle 4 concurrent
   - Check for bottlenecks

2. **Network Stability**
   - Packet loss causes frame drops
   - Check connection quality

3. **Browser Performance**
   - Try different browser
   - Close other browser tabs

## Error Messages

### "Invalid JSON"

**Cause:** WebSocket message parsing failed

**Solution:** Usually a temporary glitch. Try refreshing.

### "Source face not uploaded"

**Cause:** Tried to start stream before uploading image

**Solution:** Upload face image first, wait for "readyForStream" message.

### "RTCPeerConnection error"

**Cause:** WebRTC connection failed

**Solutions:**
1. Check STUN/TURN server configuration
2. Try different browser
3. Disable VPN/firewall

### "Function timeout"

**Cause:** Modal function exceeded timeout limit

**Solution:** Increase timeout in code or reduce processing load.

## Getting Help

### Check Logs

```bash
# View Modal logs
modal app logs facestream

# Stream logs in real-time
modal app logs facestream --follow
```

### Check Modal Dashboard

1. Go to [modal.com/dashboard](https://modal.com/dashboard)
2. Check app status
3. Monitor GPU usage
4. View error logs

### Community Resources

- [Modal Documentation](https://modal.com/docs)
- [WebRTC Support](https://webrtc.org/)
- [InsightFace GitHub](https://github.com/deepinsight/insightface)

## Debug Mode

### Enable Verbose Logging

Edit `src/facestream/__init__.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
```

### Browser Console

1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for FaceStream logs
4. Check Network tab for WebSocket status

## Common Fixes Summary

| Problem | Fix |
|---------|-----|
| Camera not working | Check permissions, try different browser |
| Connection fails | Use HTTPS, check Modal status |
| Face not detected | Use clearer image, better lighting |
| Identity leaking | Increase identity_strength |
| Slow performance | Lower video quality |
| Mobile issues | Enable TURN server |
| Deployment fails | Check Modal auth, dependencies |
