# services/tts_service.py
import os
import httpx
import edge_tts
import asyncio
import subprocess
from typing import List, Dict, Optional
from core.project import TimelineSegment
from core.settings import VOICE_PROFILES


class TTSService:
    def __init__(self):
        self.voice_profiles = VOICE_PROFILES
        self.server_url = "http://localhost:8000/clone"

        # 🔥 простий in-memory кеш (зменшує повторні XTTS виклики)
        self.xtts_cache = {}

    def _speed_up_audio_if_needed(self, file_path: str, max_duration: float):
        """
        [AUDIO ALIGNMENT] Нативно прискорює аудіофайл через FFmpeg-фільтр 'atempo',
        якщо він перевищує відведений ліміт часу картки на екрані.
        """
        if max_duration <= 0 or not file_path or not os.path.exists(file_path):
            return

        try:
            # 1. Дізнаємося реальну тривалість створеного ШІ-файлу через ffprobe
            cmd_probe = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nocut=1", file_path
            ]
            result = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True)
            actual_duration = float(result.stdout.strip().split('=')[1])
        except Exception:
            return  # Якщо не вдалося зчитати довжину, пропускаємо, щоб не ламати конвеєр

        # 2. Порівнюємо: якщо ШІ-голос довший за вікно картки субтитрів
        if actual_duration > max_duration:
            # Обчислюємо точний коефіцієнт потрібного прискорення
            factor = actual_duration / max_duration
            
            # Обмеження коефіцієнта (макс. 1.45), щоб мовлення залишалося розбірливим і природним для людини
            factor = min(factor, 1.45) 
            
            print(f"[TTS Alignment] Сегмент виходить за межі на {actual_duration - max_duration:.2f} сек. "
                  f"Запуск нативного прискорення atempo={factor:.2f}x...")
            
            temp_output = file_path + "_speedup.wav"
            
            cmd_ffmpeg = [
                "ffmpeg", "-y",
                "-i", file_path,
                "-filter:a", f"atempo={factor:.2f}",
                "-c:a", "pcm_s16le",  # зберігаємо нестиснений стабільний wav
                temp_output
            ]
            
            try:
                subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                # Замінюємо початковий файл його прискореною версією
                if os.path.exists(temp_output):
                    os.replace(temp_output, file_path)
            except Exception as e:
                print(f"[TTS Alignment Error] Не вдалося виконати atempo для {file_path}: {e}")

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

                # ----------------------------------------------------------------------
                # 🔥 РОЗУМНИЙ АЛАЙНМЕНТ: Захист від накладання на наступну репліку (Overlap Resolver)
                # ----------------------------------------------------------------------
                if seg.audio_path and os.path.exists(seg.audio_path):
                    # За замовчуванням максимальний час — це чиста тривалість картки
                    max_allowed_time = float(seg.end - seg.start)
                    
                    # ПЕРЕВІРКА НАПЕРЕД: Якщо це не останній сегмент, дивимося на старт наступного
                    if i < total - 1:
                        next_seg = segments[i + 1]
                        
                        # Обчислюємо максимальний ліміт: від нашого старту до старту наступної репліки!
                        # Це залізобетонно не дасть поточному голосу налізти на наступний.
                        absolute_limit = float(next_seg.start - seg.start)
                        
                        # Якщо між репліками є пауза, absolute_limit буде більшим за тривалість картки.
                        # Нам вигідно взяти саме absolute_limit, щоб дати XTTS більше простору для природного темпу!
                        if absolute_limit > 0:
                            max_allowed_time = absolute_limit

                    # Викликаємо автоматичний тайм-стретч, який тепер знає про сусідів
                    self._speed_up_audio_if_needed(seg.audio_path, max_allowed_time)
                # ----------------------------------------------------------------------

                results.append(seg.audio_path or "")

                if progress_callback:
                    progress_callback(int(((i + 1) / total) * 100))

        return results

    async def _edge_fallback(self, seg, target_lang, output_path):
        """
        Резервний синтез мовлення через Edge-TTS (Захищений від voice must be str)
        """
        lang_pool = self.voice_profiles.get(
            target_lang,
            self.voice_profiles.get("en", {})
        )

        if isinstance(lang_pool, dict):
            voice_list = lang_pool.get(seg.gender, [])
            voice = voice_list[0] if voice_list else None
        elif isinstance(lang_pool, list) and lang_pool:
            voice = lang_pool[0]
        else:
            voice = None

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