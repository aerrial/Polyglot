# core/settings.py
import os

# Тепер BASE_DIR — це корінь проєкту (на один рівень вище від папки core)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Шляхи до файлів тепер будуть правильно будуватися від кореня
VIDEO_FILE = os.path.join(BASE_DIR, "data", "input_video.mp4")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "translated_video.mp4")
TEMP_DIR = os.path.join(BASE_DIR, "output", "temp_segments")
DEMUCS_OUTPUT = os.path.join(BASE_DIR, "output", "demucs_output")

# Налаштування нейромереж
WHISPER_MODEL_SIZE = "medium"
COMPUTE_TYPE = "float16"
DEVICE = "cuda"  # Твоя RTX 3050

# Решта налаштувань залишається без змін
SUPPORTED_LANGUAGES = {
    "Українська": "uk",
    "English": "en",
    "Deutsch": "de",
    "Français": "fr",
    "Español": "es"
}

VOICE_PROFILES = {
    "uk": {"Male": ["uk-UA-OstapNeural"], "Female": ["uk-UA-PolinaNeural"]},
    "en": {"Male": ["en-US-GuyNeural", "en-US-ChristopherNeural"], "Female": ["en-US-AriaNeural", "en-US-JennyNeural"]},
    "de": {"Male": ["de-DE-ConradNeural"], "Female": ["de-DE-KatjaNeural"]},
    "fr": {"Male": ["fr-FR-HenriNeural"], "Female": ["fr-FR-DeniseNeural"]},
    "es": {"Male": ["es-ES-AlvaroNeural"], "Female": ["es-ES-ElviraNeural"]}
}

# Створення папок відносно кореня
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DEMUCS_OUTPUT, exist_ok=True)