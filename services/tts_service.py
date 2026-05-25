# services/tts_service.py
import os
import asyncio
from typing import List, Dict
from core import settings
from ml.tts import generate_voice
from audio.pipeline import process_segment

class TTSService:
    def __init__(self):
        self.speaker_to_voice_map = {}

    def assign_voices(self, segments: List, target_lang: str):
        """
        Закріплює конкретний голос за кожним ID спікера.
        Це гарантує, що персонаж не змінить голос посеред відео.
        """
        unique_speakers = list(set(seg.speaker_id for seg in segments))
        
        # Отримуємо доступні голоси для мови
        lang_profiles = settings.VOICE_PROFILES.get(target_lang, settings.VOICE_PROFILES["en"])
        
        for idx, spk_id in enumerate(unique_speakers):
            # Визначаємо гендер (беремо з першого сегмента цього спікера)
            gender = next((s.gender for s in segments if s.speaker_id == spk_id), "Female")
            
            # Вибираємо голос по черзі зі списку доступних для цього гендеру
            available = lang_profiles.get(gender, lang_profiles["Female"])
            voice = available[idx % len(available)]
            self.speaker_to_voice_map[spk_id] = voice

    async def process_single_segment(self, segment, idx, target_lang):
        """Генерує аудіо для одного конкретного сегмента (Partial Rerender)"""
        try:
            voice = self.speaker_to_voice_map.get(segment.speaker_id)
            if not voice:
                # Якщо голос ще не призначено (напр. новий сегмент)
                self.assign_voices([segment], target_lang)
                voice = self.speaker_to_voice_map[segment.speaker_id]

            file_path = os.path.join(settings.TEMP_DIR, f"seg_{idx}_{segment.id}.mp3")
            
            # Виклик існуючої функції edge-tts
            success = await generate_voice(segment.translated_text, file_path, voice)
            
            if success:
                # Обробка темпу (накладання на таймлайн)
                audio_segment, start_time = await process_segment(segment, file_path)
                segment.audio_path = file_path # Зберігаємо шлях для кешу
                segment.status = "ready"
                return audio_segment, start_time
            return None
        except Exception as e:
            print(f"⚠️ TTS Error in segment {segment.id}: {e}")
            segment.status = "error"
            return None

    async def process_all(self, segments: List, target_lang: str):
        """Паралельна генерація всіх сегментів"""
        self.assign_voices(segments, target_lang)
        
        # Semaphore обмежує кількість одночасних запитів до API (щоб не забанили)
        sem = asyncio.Semaphore(5)
        
        async def sem_task(seg, i):
            async with sem:
                return await self.process_single_segment(seg, i, target_lang)

        tasks = [sem_task(seg, i) for i, seg in enumerate(segments)]
        results = await asyncio.gather(*tasks)
        
        # Повертаємо тільки успішні результати для мікшера
        return [r for r in results if r is not None]