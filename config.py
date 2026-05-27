# config.py
import os
from core.settings import (
    BASE_DIR, VIDEO_FILE, OUTPUT_FILE, TEMP_DIR, DEMUCS_OUTPUT,
    WHISPER_MODEL_SIZE, COMPUTE_TYPE, DEVICE, SUPPORTED_LANGUAGES, VOICE_PROFILES
)

HF_TOKEN = os.getenv("HF_TOKEN")

# Налаштування за замовчуванням для зворотної сумісності зі старими модулями
DEFAULT_VOICE_MALE = VOICE_PROFILES["uk"]["Male"]
DEFAULT_VOICE_FEMALE = VOICE_PROFILES["uk"]["Female"]