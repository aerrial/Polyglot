# controllers/localization_controller.py
import asyncio
import os
from PySide6.QtCore import QObject, Signal
from moviepy import VideoFileClip

from core.project import Project, TimelineSegment
from core import settings
from services.audio_service import AudioService
from services.stt_service import STTService
from services.translate_service import TranslateService
from services.tts_service import TTSService
from video.export import export_final  # Твоя реальна функція рендеру

class LocalizationController(QObject):
    # Сигнали для зворотного зв'язку з UI (MainWindow)
    status_changed = Signal(str)      # Повідомлення для логів системи
    progress_changed = Signal(int)    # Загальний прогрес виконання (%)
    sync_required = Signal(list)      # Запит на редагування (передає сегменти в UI)
    step_completed = Signal(str)      # Прапорець завершення великих етапів

    def __init__(self, video_path: str):
        super().__init__()
        # Створюємо єдине джерело істини проекту
        self.project = Project(video_path)
        self.video_duration = 0.0
        
        # Ініціалізація сервісного шару реальними об'єктами
        self.audio_service = AudioService()
        self.stt_service = STTService()
        self.translate_service = TranslateService()
        self.tts_service = TTSService()

    async def run_full_analysis(self):
        """Етап 1: Повний аналіз медіафайлу, транскрипція, діаризація та переклад"""
        try:
            self.status_changed.emit("🎬 Ініціалізація проєкту та аналіз відео...")
            self.progress_changed.emit(2)

            # Визначаємо тривалість оригінального відео
            with VideoFileClip(self.project.video_path) as clip:
                self.video_duration = clip.duration
            self.status_changed.emit(f"⏱ Тривалість відео: {self.video_duration:.2f} сек.")
            
            # 1. Розділення аудіодоріжок через Demucs (AudioService)
            self.status_changed.emit("🎧 Відокремлення вокалу від фонового шуму (Demucs)...")
            self.project.background_path, self.project.vocals_path = \
                await self.audio_service.extract_and_separate(self.project.video_path)
            self.progress_changed.emit(30)

            # 2. Розпізнавання мовлення та спікерів (STTService)
            self.status_changed.emit("🧠 Розпізнавання мови та аналіз спікерів (Whisper + Pyannote)...")
            self.project.segments = \
                await self.stt_service.process(self.project.vocals_path, self.project.source_lang)
            self.progress_changed.emit(70)

            # 3. Автоматичний пакетний переклад (TranslateService)
            self.status_changed.emit("🌐 Генерація первинного перекладу тексту...")
            await self.translate_service.process(self.project.segments, self.project.target_lang)
            self.progress_changed.emit(90)
            
            # Зупиняємо автоматичний пайплайн і передаємо дані в інтерфейс для перевірки
            self.status_changed.emit("⏳ Очікування валідації або редагування тексту користувачем...")
            self.sync_required.emit(self.project.segments)
            self.step_completed.emit("ANALYSIS_DONE")
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі аналізу: {str(e)}")
            self.progress_changed.emit(0)

    async def run_synthesis(self):
        """Етап 2: Після ручного редагування — генерація голосу, мікшування та рендеринг відео"""
        try:
            self.status_changed.emit("🎙️ Запуск нейронного синтезу мовлення (Edge-TTS)...")
            self.progress_changed.emit(5)
            
            # 1. Паралельна генерація аудіо для всіх сегментів тексту
            voice_results = await self.tts_service.process_all(
                self.project.segments, 
                self.project.target_lang
            )
            self.progress_changed.emit(50)
            
            # 2. Зведення фінальної доріжки: накладання нового голосу на оригінальний фон
            self.status_changed.emit("🎧 Зведення фінального аудіоміксу (Mixer)...")
            final_audio_segment = self.audio_service.mix_final(
                self.project.background_path,
                voice_results,
                self.video_duration,
                settings.OUTPUT_FILE # Тимчасовий шлях для зведеного аудіоміксу
            )
            self.progress_changed.emit(75)
            
            # 3. Інтеграція нової доріжки у відеоряд через твій MoviePy експортер
            self.status_changed.emit("🎞️ Програмний монтаж та кодування відео (MoviePy libx264)...")
            self.progress_changed.emit(85)
            
            # Виконуємо важкий рендер відео у фоновому потоці, щоб не «заморожувати» інтерфейс
            await asyncio.to_thread(
                export_final,
                video_path=self.project.video_path,
                audio_segment=final_audio_segment,
                output_path=self.project.output_video_path  # Збереження у вибране в UI місце
            )
            
            self.status_changed.emit(f"🎉 Локалізацію завершено! Файл збережено: {self.project.output_video_path}")
            self.progress_changed.emit(100)
            self.step_completed.emit("SYNTHESIS_DONE")
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі рендеру: {str(e)}")
            self.progress_changed.emit(0)