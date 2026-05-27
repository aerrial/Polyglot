# services/translate_service.py
import asyncio
from deep_translator import GoogleTranslator
from core.project import TimelineSegment

class TranslateService:
    def __init__(self):
        pass

    async def translate_text(self, text: str, target_lang: str = "en") -> str:
        """Перекладає один окремий рядок тексту (Пункт 2)"""
        if not text.strip():
            return ""
        try:
            translated = await asyncio.to_thread(
                lambda: GoogleTranslator(source='auto', target=target_lang).translate(text)
            )
            return translated if translated else text
        except Exception as e:
            print(f"[Translate Error] Помилка рядка: {e}")
            return text

    async def process(self, segments: list[TimelineSegment], target_lang: str = "en"):
        """Пакетний ВИСОКОПРОДУКТИВНИЙ переклад усіх сегментів через паралельні таски"""
        print(f"[Translate] Початок паралельного перекладу {len(segments)} сегментів...")
        
        # Створюємо список асинхронних завдань для кожного сегмента
        async def _translate_single_seg(seg: TimelineSegment):
            if seg.original_text.strip():
                seg.translated_text = await self.translate_text(seg.original_text, target_lang)
                seg.status = "transcribed"

        # Запускаємо всі запити в мережу ОДНОЧАСНО
        tasks = [_translate_single_seg(seg) for seg in segments]
        await asyncio.gather(*tasks)
        
        print("[Translate] Пакетний переклад успішно завершено.")