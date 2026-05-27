# services/audio_service.py
import os
import subprocess
from audio.separation import separate_vocals
from core import settings
from core.project import TimelineSegment
from typing import List

class AudioService:
    def __init__(self):
        pass

    async def extract_and_separate(self, video_path: str):
        """
        Використовує Demucs для розділення на вокал та фон.
        Повертає шляхи до (background_path, vocals_path).
        """
        bg_path, vocals_path = separate_vocals(video_path)
        return bg_path, vocals_path

    def mix_final(self, background_path: str, segments: List[TimelineSegment], video_duration: float, output_path: str) -> str:
        """
        [ОПТИМІЗОВАНО] Чистий FFmpeg Mixer (БЕЗ pydub).
        Бере збережений фон, накладає нові TTS репліки за таймінгами через adelay та amix.
        Повертає СТРОКОВИЙ шлях до готового .wav файлу.
        """
        print(f"[Mixer] Початок швидкого зведення аудіо через FFmpeg. Фон: {background_path}")
        
        # Визначаємо шлях для фінального звукового файлу
        final_wav_path = os.path.splitext(output_path)[0] + ".wav"
        
        # Фільтруємо лише ті сегменти, які реально мають згенерований звук
        valid_segments = [seg for seg in segments if seg.audio_path and os.path.exists(seg.audio_path)]
        
        # Якщо немає жодної репліки або немає фону — просто повертаємо наявний фон чи робимо копію
        if not valid_segments:
            print("[Mixer] Згенерованих реплік не знайдено. Повертаємо чистий фон.")
            return background_path if (background_path and os.path.exists(background_path)) else ""

        try:
            # Починаємо будувати команду FFmpeg
            # Перший вхідний файл (-i) — це завжди наш фоновий супровід
            cmd = ["ffmpeg", "-y", "-i", background_path]
            
            # Додаємо всі TTS сегменти як окремі входи
            for seg in valid_segments:
                cmd.extend(["-i", seg.audio_path])
                
            # Будуємо складний фільтр (filter_complex) для зміщування звуку по таймлайну
            filter_inputs = "[0:a]"  # Початковий вхід — аудіо з фону (індекс 0)
            filter_graph = ""
            
            for idx, seg in enumerate(valid_segments):
                # FFmpeg adelay очікує затримку в мілісекундах для кожного каналу (лівий|правий)
                delay_ms = int(seg.start * 1000)
                
                # Застосовуємо затримку до входу (idx + 1), бо 0 - це фон
                # Приклад: [1:a]adelay=3500|3500[delayed1];
                filter_graph += f"[{idx+1}:a]adelay={delay_ms}|{delay_ms}[delayed{idx+1}];"
                filter_inputs += f"[delayed{idx+1}]"
                
            # Рахуємо загальну кількість потоків для змішування (фон + кількість реплік)
            total_inputs = len(valid_segments) + 1
            
            # Додаємо фінальний фільтр amix, який склеїть все в один потік
            # dropout_transition=0 не дає звуку затухати, коли закінчуються окремі репліки
            filter_graph += f"{filter_inputs}amix=inputs={total_inputs}:duration=first:dropout_transition=0[outa]"
            
            # Дописуємо фільтри та параметри кодування в загальну команду
            cmd.extend([
                "-filter_complex", filter_graph,
                "-map", "[outa]",
                "-acodec", "pcm_s16le",  # зберігаємо в чистий нестиснений wav
                "-ar", "44100",
                "-ac", "2",
                final_wav_path
            ])
            
            print(f"[Mixer] Запуск утиліти FFmpeg для нативного зведення...")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print(f"[Mixer] Фінальний мікс успішно матеріалізовано: {final_wav_path}")
            return final_wav_path

        except Exception as e:
            print(f"[Mixer Error] Помилка нативного зведення: {e}")
            # Аварійний фолбек
            return background_path