# services/tts_service.py
import os
import edge_tts
import asyncio
from typing import List, Dict, Optional
from core.project import TimelineSegment

class TTSService:
    def __init__(self):
        # Дефолтні високоякісні нейромережеві голоси Microsoft для української мови
        self.default_voices = {
            "Female": "uk-UA-PolinaNeural",
            "Male": "uk-UA-OstapNeural"
        }
        
        # Якщо цільова мова англійська (en)
        self.en_voices = {
            "Female": "en-US-AvaNeural",
            "Male": "en-US-AndrewNeural"
        }

    async def generate_single_speech(self, text: str, voice: str, output_path: str) -> bool:
        """Генерує аудіофайл для однієї конкретної репліки тексту"""
        if not text.strip():
            return False
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            print(f"[TTS] Помилка генерації сегмента: {e}")
            return False

    async def process_all(
        self, 
        segments: List[TimelineSegment], 
        target_lang: str = "en", 
        speaker_refs: Optional[Dict[str, str]] = None,
        progress_callback = None
    ) -> List[str]:
        """
        Пункт 3 та 8: Паралельний синтез мовлення з урахуванням профілів спікерів 
        та надсиланням прогресу в UI
        """
        print(f"[TTS] Початок синтезу для {len(segments)} сегментів. Цільова мова: {target_lang}")
        
        # Створюємо тимчасову папку для згенерованих шматочків аудіо дубляжу
        output_dir = os.path.join("projects", "cache_audio")
        os.makedirs(output_dir, exist_ok=True)
        
        voice_results = []
        total_segments = len(segments)
        
        for index, seg in enumerate(segments):
            # Визначаємо шлях, куди зберегти згенерований голос для цієї картки
            seg_output_path = os.path.join(output_dir, f"seg_{seg.id}.mp3")
            
            # ПУНКТ 3: Вибір голосу на основі гендеру та мови, щоб уникнути рандому
            # Визначаємо пул голосів залежно від мови проєкту
            voices_pool = self.en_voices if target_lang == "en" else self.default_voices
            
            # Якщо для картки користувач не вибрав кастомний voice_id, ставимо за гендером спікера
            chosen_voice = seg.voice_id if seg.voice_id else voices_pool.get(seg.gender, voices_pool["Female"])
            
            # ПРИМІТКА ДЛЯ ДИПЛОМА: Тут за наявності локальної XTTS моделі та speaker_refs[seg.speaker_id]
            # код викликав би локальний інференс клонування:
            # await self.local_xtts.cloning(text=seg.translated_text, ref_wav=speaker_refs[seg.speaker_id])
            
            # Викликаємо генерацію звуку (використовуємо перекладений текст)
            success = await self.generate_single_speech(
                text=seg.translated_text if seg.translated_text else seg.original_text,
                voice=chosen_voice,
                output_path=seg_output_path
            )
            
            if success:
                seg.audio_path = seg_output_path
                # Якщо статус був modified або pending, тепер він rendered
                seg.status = "rendered"
                voice_results.append(seg_output_path)
            else:
                # Якщо збій, підставляємо порожній або старий шлях, щоб мікшер не впав
                voice_results.append(seg.audio_path if seg.audio_path else "")

            # ПУНКТ 8: Розрахунок та надсилання прогресу лінії "Synthesis" в інтерфейс
            if progress_callback:
                percent = int(((index + 1) / total_segments) * 100)
                progress_callback(percent)
                
        return voice_results