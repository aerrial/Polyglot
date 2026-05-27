# ml/speech_to_text.py
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torchaudio
import config
import os
import torch

# Апаратна оптимізація під тензорні ядра твоєї RTX 3050
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Гарантуємо наявність FFmpeg у системних змінних для torchaudio декодерів
ffmpeg_bin = r'C:\ffmpeg\bin'
if ffmpeg_bin not in os.environ["PATH"]:
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

_model = None
_diarization_pipeline = None

def get_whisper_model():
    """Створює стабільний синглтон моделі Whisper для економії VRAM."""
    global _model
    if _model is None:
        print("🧠 [Whisper] Ініціалізація моделі транскрибації...")
        _model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.DEVICE,
            compute_type=config.COMPUTE_TYPE
        )
    return _model

def get_diarization_pipeline():
    """Створює синглтон пайплайну діаризації Pyannote зі страховкою авторизації."""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        print("👥 [Pyannote] Ініціалізація моделі діаризації спікерів...")
        
        # Отримуємо токен Hugging Face із конфігу для завантаження ваг
        hf_token = getattr(config, "HF_TOKEN", None)
        
        try:
            if hf_token:
                _diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=hf_token
                )
            else:
                # Спроба завантажити без токена (якщо модель вже лежить у локальному кеші .cache/huggingface)
                _diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
                
        except Exception as e:
            print(f"[Pyannote Error] Не вдалося завантажити модель діаризації. "
                  f"Перевірте HF_TOKEN у середовищі. Помилка: {e}")
            raise e
            
    return _diarization_pipeline