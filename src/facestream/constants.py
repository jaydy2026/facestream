MODEL_CACHE_DIR = "/root/models"

SECRET_KEY_TURN_TOKEN_ID = "TURN_TOKEN_ID"
SECRET_KEY_TURN_API_TOKEN = "TURN_API_TOKEN"

# Identity Enhancement Settings
# These can be tuned for better identity preservation
IDENTITY_STRENGTH = 0.7          # 0.0-1.0, higher = stronger source identity
SKIN_TONE_MATCH = True            # Apply histogram matching for skin tone
SKIN_SMOOTHING = True            # Apply bilateral filtering for smooth skin
FACE_ENHANCE = False             # Apply face detail enhancement (adds latency)
PASTE_BACK = True                # Use paste_back for compositing (recommended)
