# config.py
import os

# Базові шляхи
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Шляхи до файлів (використовуємо відносні шляхи від кореня проєкту)
VIDEO_FILE = os.path.join(BASE_DIR, "data", "input_video.mp4")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "translated_video.mp4")
TEMP_DIR = os.path.join(BASE_DIR, "output", "temp_segments")
DEMUCS_OUTPUT = os.path.join(BASE_DIR, "output", "demucs_output")

# Налаштування нейромереж
WHISPER_MODEL_SIZE = "medium"
COMPUTE_TYPE = "float16"
DEVICE = "cuda"  # Твоя RTX 3050

# Налаштування озвучки
DEFAULT_VOICE_MALE = "uk-UA-OstapNeural"
DEFAULT_VOICE_FEMALE = "uk-UA-PolinaNeural"

# Створення папок (exist_ok=True дозволяє створювати вкладені папки відразу)
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DEMUCS_OUTPUT, exist_ok=True)