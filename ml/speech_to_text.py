# ml/speech_to_text.py
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torchaudio
import config
import os
import sys
import torch

# Оптимізація для відеокарт серії RTX (як ваша 3050)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Додавання FFmpeg у PATH для коректної роботи аудіо-декодерів
ffmpeg_bin = r'C:\ffmpeg\bin'
if ffmpeg_bin not in os.environ["PATH"]:
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

_model = None
_diarization_pipeline = None

def get_whisper_model():
    """Створює синглтон моделі Whisper для економії відеопам'яті."""
    global _model
    if _model is None:
        print("🧠 Завантаження Whisper моделі...")
        _model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.DEVICE,
            compute_type=config.COMPUTE_TYPE
        )
    return _model

def transcribe_audio(audio_path, language="uk"):
    """Транскрибує аудіо в текст."""
    model = get_whisper_model()
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True
    )
    return list(segments)

def get_diarization_pipeline():
    """Створює синглтон пайплайну діаризації Pyannote."""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        print("👥 Завантаження моделі діаризації (Pyannote)...")
        # В останніх версіях pyannote використовується аргумент 'token'
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=config.HF_TOKEN
        )
        # Переносимо на пристрій з config (cuda або cpu)
        _diarization_pipeline.to(torch.device(config.DEVICE))
    return _diarization_pipeline

def diarize_audio(audio_path):
    """Визначає, хто і коли говорить."""
    pipeline = get_diarization_pipeline()
    
    # Завантажуємо аудіо вручну через torchaudio, щоб оминути AudioDecoder
    waveform, sample_rate = torchaudio.load(audio_path)
    
    # Передаємо словником, як пропонувала помилка в UserWarning раніше
    audio_data = {"waveform": waveform, "sample_rate": sample_rate}
    
    # Викликаємо діаризацію
    diarization = pipeline(audio_data)
    
    speaker_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_segments.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker
        })
    return speaker_segments