import os
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

API_ID = os.getenv("API_ID")
if API_ID:
    try:
        API_ID = int(API_ID)
    except ValueError:
        pass

API_HASH = os.getenv("API_HASH", "")

# Userbot Sessions
# If SESSION_NAME is provided, 1 single account will handle both VC1 & VC2
SESSION_NAME = os.getenv("SESSION_NAME", os.getenv("SESSION_LISTENER", "relay_session"))
SESSION_LISTENER = os.getenv("SESSION_LISTENER", SESSION_NAME)
SESSION_BROADCASTER = os.getenv("SESSION_BROADCASTER", SESSION_NAME)

# Chat IDs can be integer IDs, string usernames, or t.me links
def parse_chat_id(val: str):
    if not val:
        return None
    val = val.strip()
    if "t.me/" in val:
        val = val.split("t.me/")[-1].strip("/").replace("@", "")
    if val.startswith("-") or val.isdigit():
        try:
            return int(val)
        except ValueError:
            pass
    return val

CHAT_VC1 = parse_chat_id(os.getenv("CHAT_VC1", ""))
CHAT_VC2 = parse_chat_id(os.getenv("CHAT_VC2", ""))

TARGET_DELAY_SEC = float(os.getenv("TARGET_DELAY_SEC", "2.0"))
MAX_DELAY_SEC = float(os.getenv("MAX_DELAY_SEC", "5.0"))

# Audio settings (Standard PCM 16-bit stereo 48000Hz)
SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit PCM = 2 bytes per sample
# 20ms audio frame duration
FRAME_DURATION_SEC = 0.02
# 20ms * 48000 Hz = 960 samples per frame. 960 * 2 channels * 2 bytes = 3840 bytes per frame
FRAME_SIZE_BYTES = int(SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_DURATION_SEC)
