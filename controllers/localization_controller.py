# controllers/localization_controller.py
import asyncio
import os
import subprocess
import json
import config
from PySide6.QtCore import QObject, Signal

from core.project import Project, TimelineSegment
from core import settings
from services.audio_service import AudioService
from services.stt_service import STTService
from services.translate_service import TranslateService
from services.tts_service import TTSService
from video.export import export_final

class LocalizationController(QObject):
    status_changed = Signal(str) 
    overall_progress = Signal(int)
    audio_progress = Signal(int)
    stt_progress = Signal(int)
    translate_progress = Signal(int)
    tts_progress = Signal(int) 
    sync_required = Signal(list)
    step_completed = Signal(str, str) 

    def __init__(self, video_path: str):
        super().__init__()
        self.project = Project(video_path)
        self.video_duration = 0.0
        
        self.audio_service = AudioService()
        self.stt_service = STTService()
        self.translate_service = TranslateService()
        self.tts_service = TTSService()

    def _get_video_duration_ffprobe(self, path: str) -> float:
        """Оптимізоване нативне отримання тривалості відео через ffprobe БЕЗ MoviePy"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nocut=1", path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
            return float(result.stdout.strip().split('=')[1])
        except Exception:
            return 0.0

    async def run_full_analysis(self):
        """Етап 1: Повний аналіз медіафайлу, транскрипція, діаризація та переклад"""
        try:
            self.status_changed.emit("🎬 Ініціалізація проєкту та аналіз відео...")
            self.overall_progress.emit(2)

            # Використовуємо наш швидкий ffprobe
            self.video_duration = self._get_video_duration_ffprobe(self.project.video_path)
            self.status_changed.emit(f"⏱ Тривалість відео: {self.video_duration:.2f} сек.")
            
            # 1. Розділення аудіодоріжок через Demucs
            self.status_changed.emit("🎧 Відокремлення вокалу від фонового супроводу (Demucs)...")
            self.audio_progress.emit(10)
            
            self.project.background_path, self.project.vocals_path = await self.audio_service.extract_and_separate(self.project.video_path)
            
            self.audio_progress.emit(100) 
            self.overall_progress.emit(30)

            # 2. Розпізнавання мовлення та спікерів (Whisper + Pyannote)
            self.status_changed.emit("🧠 Розпізнавання мови та аналіз спікерів (Whisper + Pyannote)...")
            self.stt_progress.emit(0)
            
            segments, speaker_samples = await self.stt_service.process(
                self.project.vocals_path, 
                self.project.source_lang,
                progress_callback=lambda p: self.stt_progress.emit(p)
            )
            self.project.segments = segments
            self.project.speaker_voice_map = speaker_samples 
            
            self.stt_progress.emit(100) 
            self.overall_progress.emit(70)

            # 3. Автоматичний пакетний переклад
            self.status_changed.emit("🌐 Генерація первинного перекладу text...")
            self.translate_progress.emit(20)
            
            await self.translate_service.process(self.project.segments, self.project.target_lang)
            
            self.translate_progress.emit(100) 
            self.overall_progress.emit(90)
            
            saved_json = self.project.save_to_json()
            self.status_changed.emit(f"💾 Стан проєкту заархівовано: {saved_json}")
            
            self.status_changed.emit("⏳ Очікування валідації користувачем...")
            self.sync_required.emit(self.project.segments)
            self.step_completed.emit("ANALYSIS_DONE", self.project.video_path)
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі аналізу: {str(e)}")
            self.overall_progress.emit(0)

    async def run_synthesis(self):
        """Етап 2: Після ручного редагування — генерація голосу, мікшування та рендеринг відео"""
        try:
            self.project.save_to_json()
            
            self.status_changed.emit("🎙️ Запуск нейронного синтезу мовлення (Клонування голосу)...")
            self.tts_progress.emit(10)
            self.overall_progress.emit(5)
            
            # Страховка референсів голосу акторів
            if not self.project.speaker_voice_map and self.project.vocals_path and os.path.exists(self.project.vocals_path):
                print("[Controller] speaker_voice_map пуста. Робимо фолбек наvocals_path.")
                self.project.speaker_voice_map = {"UNKNOWN": self.project.vocals_path}
                # Збираємо всі унікальні спікери з карток, якщо вони там є
                for seg in self.project.segments:
                    self.project.speaker_voice_map[seg.speaker_id] = self.project.vocals_path

            # 1. Генерація аудіо для всіх сегментів
            voice_results = await self.tts_service.process_all(
                self.project.segments, 
                self.project.target_lang,
                speaker_refs=self.project.speaker_voice_map, 
                progress_callback=lambda p: self.tts_progress.emit(p) 
            )
            self.tts_progress.emit(100)
            self.overall_progress.emit(50)
            
            # 2. Зведення фінальної доріжки
            self.status_changed.emit("🎧 Зведення фінального адуіоміксу (Mixer)...")
            final_audio_obj = self.audio_service.mix_final(
                self.project.background_path,
                self.project.segments,  
                self.video_duration,
                self.project.output_video_path
            )
            self.overall_progress.emit(75)
            
            # Обчислюємо шлях до створеного .wav
            if isinstance(final_audio_obj, str) and final_audio_obj and os.path.exists(final_audio_obj):
                audio_path_for_ffmpeg = final_audio_obj
            else:
                audio_path_for_ffmpeg = os.path.splitext(self.project.output_video_path)[0] + ".wav"

            # 3. Інтеграція нової доріжки у відеоряд через прямий FFmpeg
            self.status_changed.emit("🎞️ Програмний монтаж та кодування відео (FFmpeg Mux)...")
            self.overall_progress.emit(85)
            
            await asyncio.to_thread(
                export_final,
                video_path=self.project.video_path,
                audio_path=audio_path_for_ffmpeg,
                output_path=self.project.output_video_path
            )
            
            for seg in self.project.segments:
                if seg.status in ["modified", "transcribed"]:
                    seg.status = "rendered"
            
            self.project.save_to_json()
            
            self.status_changed.emit(f"🎉 Локалізацію завершено! Файл збережено: {self.project.output_video_path}")
            self.overall_progress.emit(100)
            self.step_completed.emit("SYNTHESIS_DONE", self.project.output_video_path)
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі рендеру: {str(e)}")
            self.overall_progress.emit(0)