# services/audio_service.py
import os
from audio.separation import separate_vocals
from audio.mixer import mix_audio_fast
from core import settings

class AudioService:
    def __init__(self):
        pass

    async def extract_and_separate(self, video_path: str):
        """
        Використовує Demucs для розділення на вокал та фон.
        Повертає шляхи до (background_path, vocals_path).
        """
        # Твоя функція separate_vocals вже має логіку збереження
        bg_path, vocals_path = separate_vocals(video_path)
        return bg_path, vocals_path

    def mix_final(self, background_path, voice_results, duration, output_path):
        """
        Збирає фінальну доріжку.
        """
        final_audio = mix_audio_fast(
            background_path,
            voice_results,
            duration
        )
        return final_audio