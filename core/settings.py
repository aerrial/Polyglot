# core/settings.py
import os
import torch

# Режим перекладу: True — інтелектуальний Gemini LLM, False — класичний GoogleTranslator
TRANSLATION_MODE_LLM = True  

# Ключ доступу до Gemini API (можна підтягувати зі змінних оточення)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Тепер BASE_DIR — це суворий корінь проєкту
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# ⚡ РАДИКАЛЬНА ОПТИМІЗАЦІЯ VRAM ДЛЯ RTX 3050
# ==========================================
VRAM_SAFE_MODE = True
SERIAL_GPU_PIPELINE = True
CLEAR_CUDA_CACHE = True
CUDA_MEMORY_FRACTION = 0.80  

if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(CUDA_MEMORY_FRACTION)

DEVICE = "cuda"
COMPUTE_TYPE = "float16"     # Апаратне прискорення через напівточність
WHISPER_MODEL_SIZE = "large-v3-turbo" # НАДВАЖЛИВО: small замість medium для стабільності
# ==========================================

# Шляхи до медіа-директорій проєкту
VIDEO_FILE = os.path.join(BASE_DIR, "data", "input_video.mp4")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "translated_video.mp4")
TEMP_DIR = os.path.join(BASE_DIR, "output", "temp_segments")
DEMUCS_OUTPUT = os.path.join(BASE_DIR, "output", "demucs_output")

SUPPORTED_LANGUAGES = {
    "Українська": "uk",
    "English": "en",
    "Deutsch": "de",
    "Français": "fr",
    "Español": "es"
}

# Уніфікована структура: суворо рядки для стабільності Edge-TTS
VOICE_PROFILES = {
    "uk": {"Male": "uk-UA-OstapNeural", "Female": "uk-UA-PolinaNeural"},
    "en": {"Male": "en-US-GuyNeural", "Female": "en-US-AriaNeural"},
    "de": {"Male": "de-DE-ConradNeural", "Female": "de-DE-KatjaNeural"},
    "fr": {"Male": "fr-FR-HenriNeural", "Female": "fr-FR-DeniseNeural"},
    "es": {"Male": "es-ES-AlvaroNeural", "Female": "es-ES-ElviraNeural"}
}

# Автоматичне створення робочого оточення на диску
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DEMUCS_OUTPUT, exist_ok=True)