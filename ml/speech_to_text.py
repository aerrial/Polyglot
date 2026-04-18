# ml/speech_to_text.py
from faster_whisper import WhisperModel
import config

def transcribe_audio(audio_path, language="uk"):
    print(f"🧠 Whisper (GPU) розпізнає: {audio_path}")
    model = WhisperModel(
        config.WHISPER_MODEL_SIZE, 
        device=config.DEVICE, 
        compute_type=config.COMPUTE_TYPE
    )
    
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=1000)
    )
    return list(segments)