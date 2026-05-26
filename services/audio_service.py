# services/audio_service.py
import os
from audio.separation import separate_vocals
from audio.mixer import mix_audio_fast
from core import settings
from core.project import TimelineSegment
from pydub import AudioSegment
from typing import List

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

    def mix_final(self, background_path: str, segments: List[TimelineSegment], video_duration: float, output_path: str) -> AudioSegment:
            """
            Пункт 3 та 5: Бере збережений фон та накладає нові TTS репліки.
            Повертає об'єкт AudioSegment для подальшого експорту.
            """
            print(f"[Mixer] Початок зведення аудіо. Фон: {background_path}")
            
            try:
                # 1. Завантажуємо оригінальний фоновий супровід (музика/шуми)
                if background_path and os.path.exists(background_path):
                    background = AudioSegment.from_wav(background_path)
                else:
                    # Якщо фону немає, створюємо тишу потрібної тривалості
                    background = AudioSegment.silent(duration=int(video_duration * 1000))
    
                # 2. Накладаємо кожну згенеровану репліку на фон відповідно до таймінгів
                for seg in segments:
                    if not seg.audio_path or not os.path.exists(seg.audio_path):
                        continue
                    
                    # Завантажуємо згенерований шматочок TTS
                    speech_segment = AudioSegment.from_file(seg.audio_path)
                    
                    # Обчислюємо позицію старту в мілісекундах
                    start_ms = int(seg.start * 1000)
                    
                    # Накладаємо репліку поверх фону
                    background = background.overlay(speech_segment, position=start_ms)
    
                print("[Mixer] Фінальний аудіомікс успішно сформовано в пам'яті.")
                # ТУТ ЗМІНА: Повертаємо сам об'єкт, а не рядок шляху!
                return background
    
            except Exception as e:
                print(f"[Mixer] Критична помилка мікшування: {e}")
                raise e