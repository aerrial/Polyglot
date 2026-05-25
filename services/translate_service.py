# services/translate_service.py
from deep_translator import GoogleTranslator
from typing import List
from core.project import TimelineSegment

class TranslateService:
    def __init__(self):
        # Ми ініціалізуємо перекладач безпосередньо під час виклику, 
        # щоб динамічно змінювати мови
        pass

    async def process(self, segments: List[TimelineSegment], target_lang: str, source_lang: str = 'auto'):
        """
        Перекладає список сегментів.
        Оновлює поле translated_text прямо в об'єктах.
        """
        if not segments:
            return segments

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            
            # Збираємо всі тексти в один список для пакетного перекладу
            texts_to_translate = [seg.original_text for seg in segments]
            
            # Виконуємо переклад (batch)
            translated_texts = translator.translate_batch(texts_to_translate)
            
            # Оновлюємо об'єкти
            for seg, translation in zip(segments, translated_texts):
                seg.translated_text = translation
                seg.status = "translated"
                
            return segments
            
        except Exception as e:
            print(f"❌ Помилка перекладу: {e}")
            # У разі помилки копіюємо оригінал, щоб пайплайн не зупинився
            for seg in segments:
                if not seg.translated_text:
                    seg.translated_text = seg.original_text
            return segments