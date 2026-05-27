# services/tts_service.py
import os
import httpx
import edge_tts
import asyncio
from typing import List, Dict, Optional
from core.project import TimelineSegment
from core.settings import VOICE_PROFILES


class TTSService:
    def __init__(self):
        self.voice_profiles = VOICE_PROFILES
        self.server_url = "http://localhost:8000/clone"

        # 🔥 простий in-memory кеш (зменшує повторні XTTS виклики)
        self.xtts_cache = {}

    async def process_all(
        self,
        segments: List[TimelineSegment],
        target_lang: str = "en",
        speaker_refs: Optional[Dict[str, str]] = None,
        progress_callback=None
    ) -> List[str]:

        print(f"[TTS] Start pipeline | lang={target_lang}")

        output_dir = os.path.join("projects", "cache_audio")
        os.makedirs(output_dir, exist_ok=True)

        results = []
        total = len(segments)

        async with httpx.AsyncClient(timeout=60) as client:
            for i, seg in enumerate(segments):
                seg_output_path = os.path.join(output_dir, f"seg_{seg.id}.wav")
                text = seg.translated_text or seg.original_text

                if not text.strip():
                    continue

                # --- ФІКС XTTS: Страховка від втрати ID спікера в інтерфейсі ---
                ref_path = None
                if speaker_refs:
                    # Намагаємося взяти прямий шлях для SPEAKER_XX
                    ref_path = speaker_refs.get(seg.speaker_id)
                    
                    # Якщо інтерфейс повернув "Unknown" або порожньо, але зразки в проєкті є
                    if (not ref_path or not os.path.exists(ref_path)) and speaker_refs:
                        print(f"[TTS Warning] Спікер '{seg.speaker_id}' не знайдений в мапі. Беремо перший наявний голос.")
                        ref_path = list(speaker_refs.values())[0] if speaker_refs else None

                # -------------------------
                # 1. SKIP RULES (Клонуємо лише якщо є валідний референс-файл)
                # -------------------------
                # Прибираємо обмеження "len(text) > 20" під час захисту диплому, 
                # щоб навіть короткі репліки типу "Yes", "Hello" читалися клонованим XTTS голосом!
                use_xtts = (
                    ref_path is not None and
                    os.path.exists(ref_path)
                )

                # -------------------------
                # 2. XTTS PATH
                # -------------------------
                if use_xtts:
                    cache_key = f"{seg.speaker_id}_{text}"

                    if cache_key in self.xtts_cache:
                        seg.audio_path = self.xtts_cache[cache_key]
                        seg.status = "rendered"
                        print(f"[TTS Cache] Сегмент {seg.id} взято з кешу.")
                    else:
                        payload = {
                            "text": text,
                            "language": target_lang,
                            "speaker_ref_path": os.path.abspath(ref_path),
                            "output_path": os.path.abspath(seg_output_path)
                        }

                        try:
                            print(f"[XTTS Клієнт] Запит на клонування сегмента {seg.id}...")
                            response = await client.post(self.server_url, json=payload)

                            if response.status_code == 200:
                                seg.audio_path = seg_output_path
                                seg.status = "rendered"
                                self.xtts_cache[cache_key] = seg_output_path
                                print(f"[XTTS Успіх] Сегмент {seg.id} успішно згенеровано.")
                            else:
                                print(f"[XTTS Помилка] Сервер повернув код {response.status_code}. Перемикання на Edge.")
                                await self._edge_fallback(seg, target_lang, seg_output_path)
                        except Exception as e:
                            print(f"[XTTS Сервер недоступний] Очікування відповіді збігло. Помилка: {e}. Тікаємо в Edge.")
                            await self._edge_fallback(seg, target_lang, seg_output_path)

                # -------------------------
                # 3. EDGE TTS PATH (DEFAULT)
                # -------------------------
                else:
                    print(f"[TTS] Для сегмента {seg.id} немає зразка голосу. Запуск Edge-TTS.")
                    await self._edge_fallback(seg, target_lang, seg_output_path)

                results.append(seg.audio_path or "")

                if progress_callback:
                    progress_callback(int(((i + 1) / total) * 100))

        return results

    async def _edge_fallback(self, seg, target_lang, output_path):
        """
        Резервний синтез мовлення через Edge-TTS (Захищений від voice must be str)
        """
        # Отримуємо пул голосів для мови
        lang_pool = self.voice_profiles.get(
            target_lang,
            self.voice_profiles.get("en", {})
        )

        # ФІКС: Перевіряємо, чи lang_pool є словником, чи прямим списком голосів
        if isinstance(lang_pool, dict):
            voice_list = lang_pool.get(seg.gender, [])
            voice = voice_list[0] if voice_list else None
        elif isinstance(lang_pool, list) and lang_pool:
            voice = lang_pool[0]
        else:
            voice = None

        # Залізобетонний фолбек на випадок, якщо конфіг порожній (вирішує помилку voice must be str)
        if not voice or not isinstance(voice, str):
            voice = "uk-UA-OstapNeural" if target_lang == "uk" else "en-US-AriaNeural"

        text = seg.translated_text or seg.original_text

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

            seg.audio_path = output_path
            seg.status = "rendered"
            print(f"[Edge Fallback] Сегмент {seg.id} успішно начитано голосом {voice}")

        except Exception as e:
            print(f"[Edge-TTS критична помилка] {e}")