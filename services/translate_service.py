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
            # Виконуємо синхронний переклад у фоновому потоці, щоб не блокувати асинхронне ядро
            translated = await asyncio.to_thread(
                lambda: GoogleTranslator(source='auto', target=target_lang).translate(text)
            )
            return translated if translated else text
        except Exception as e:
            print(f"[Translate] Помилка перекладу рядка: {e}")
            return text

    async def process(self, segments: list[TimelineSegment], target_lang: str = "en"):
        """Пакетний переклад усіх сегментів на Фазі 1"""
        print(f"[Translate] Початок пакетного перекладу {len(segments)} сегментів...")
        for seg in segments:
            if seg.original_text:
                seg.translated_text = await self.translate_text(seg.original_text, target_lang)
                # Оскільки це первинний автоматичний переклад, статус залишається transcribed
                seg.status = "transcribed"