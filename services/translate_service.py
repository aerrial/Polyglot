# services/translate_service.py
import httpx
import asyncio
from deep_translator import GoogleTranslator
from core.project import TimelineSegment
from core import settings

class TranslateService:
    def __init__(self):
        pass

    async def _translate_with_google(self, text: str, target_lang: str) -> str:
        """Режим А: Класичний переклад через GoogleTranslator"""
        try:
            translated = await asyncio.to_thread(
                lambda: GoogleTranslator(source='auto', target=target_lang).translate(text)
            )
            return translated if translated else text
        except Exception:
            return text

    async def _translate_with_gemini(self, text: str, max_duration: float, target_lang: str) -> str:
        """Режим Б: Інтелектуальний переклад Gemini з гнучким контролем складів та маркуванням довгих фраз"""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return await self._translate_with_google(text, target_lang)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        # Визначаємо, чи потрібно просити модель про розбиття (якщо вікно > 7 секунд)
        need_split = max_duration > 7.0

        # Промпт повністю сфокусований на складах, ритміці та гнучкому розбитті довгих реплік
        prompt = (
            f"You are an expert dubbing translator. Translate the following text into target language code '{target_lang}'.\n"
            f"CRITICAL CONSTRAINTS:\n"
            f"1. The original audio takes {max_duration:.2f} seconds to speak. Your translation MUST be concise and rhythmic, "
            f"matching the original duration as closely as possible. A flexibility of +/- 2 syllables is acceptable to maintain natural grammar.\n"
        )
        
        if need_split:
            prompt += (
                f"2. IMPORTANT: Since this segment is longer than 7 seconds ({max_duration:.2f}s), you MUST split the translation "
                f"into two logical, chronological halves using the '||' separator (e.g., 'Перша підфраза || друга підфраза'). "
                f"Ensure each half corresponds to roughly half of the total time.\n"
            )
            
        prompt += (
            f"Original text: \"{text}\"\n"
            f"Output ONLY the translated string, no notes, no explanations, no quotes."
        )

        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    translated = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    return translated.strip('"').strip("'")
                else:
                    return await self._translate_with_google(text, target_lang)
        except Exception:
            return await self._translate_with_google(text, target_lang)

    async def process(self, segments: list[TimelineSegment], target_lang: str = "en"):
        """Пакетний переклад з динамічним розбиттям сегментів тривалістю > 7 секунд"""
        use_llm = settings.TRANSLATION_MODE_LLM
        print(f"[Translate] Початок перекладу. Режим: LLM={use_llm}")
        
        original_segments = list(segments)
        segments.clear()  # Перебудовуємо динамічний таймлайн у пам'яті
        
        new_id_counter = 0

        for seg in original_segments:
            if not seg.original_text.strip():
                continue

            max_duration = float(seg.end - seg.start)
            
            if use_llm:
                translated_raw = await self._translate_with_gemini(seg.original_text, max_duration, target_lang)
                
                # Перевіряємо умову розбиття: маркер присутній ТА оригінальний сегмент дійсно > 7 секунд
                if "||" in translated_raw and max_duration > 7.0:
                    parts = [p.strip() for p in translated_raw.split("||") if p.strip()]
                    if len(parts) == 2:
                        print(f"[Sub-Segmenting] Сегмент {seg.id} триває {max_duration:.2f}с (> 7с). Ділимо навпіл.")
                        mid_time = seg.start + (max_duration / 2)
                        
                        # Перша підфраза (половина часу)
                        seg1 = TimelineSegment(
                            id=new_id_counter, start=seg.start, end=mid_time,
                            original_text=seg.original_text, translated_text=parts[0],
                            speaker_id=seg.speaker_id, gender=seg.gender, status="transcribed"
                        )
                        new_id_counter += 1
                        
                        # Друга підфраза (друга половина часу)
                        seg2 = TimelineSegment(
                            id=new_id_counter, start=mid_time, end=seg.end,
                            original_text="", translated_text=parts[1],
                            speaker_id=seg.speaker_id, gender=seg.gender, status="transcribed"
                        )
                        new_id_counter += 1
                        
                        segments.append(seg1)
                        segments.append(seg2)
                        continue

                # Якщо сегмент менший за 7 секунд, або ЛЛМ не повернула маркер
                seg.id = new_id_counter
                seg.translated_text = translated_raw
                seg.status = "transcribed"
                segments.append(seg)
                new_id_counter += 1
            else:
                # Звичайний фолбек/Google-режим
                seg.id = new_id_counter
                seg.translated_text = await self._translate_with_google(seg.original_text, target_lang)
                seg.status = "transcribed"
                segments.append(seg)
                new_id_counter += 1

        print(f"[Translate] Оптимізацію таймлайну завершено. Кількість карт на виході: {len(segments)}")

    async def translate_single_text(self, text: str, max_duration: float, target_lang: str) -> str:
        """Спеціальний метод для миттєвого перекладу однієї фрази при ручному редагуванні"""
        if not text.strip():
            return ""
        
        # Динамічно дивимося на прапорець із глобальних налаштувань
        if settings.TRANSLATION_MODE_LLM:
            return await self._translate_with_gemini(text, max_duration, target_lang)
        else:
            return await self._translate_with_google(text, target_lang)