# controllers/localization_controller.py
import asyncio
import os
from PySide6.QtCore import QObject, Signal
from moviepy.video.io.VideoFileClip import VideoFileClip

from core.project import Project, TimelineSegment
from core import settings
from services.audio_service import AudioService
from services.stt_service import STTService
from services.translate_service import TranslateService
from services.tts_service import TTSService
from video.export import export_final

class LocalizationController(QObject):
    # Сигнали для системних логів
    status_changed = Signal(str)      
    
    # Пункт 8: Роздільні сигнали прогресу для кожної лінії пайплайну в дизайні
    overall_progress = Signal(int)    # Загальний прогрес (%)
    audio_progress = Signal(int)      # Лінія "Audio" (Demucs)
    stt_progress = Signal(int)        # Лінія "STT" (Whisper)
    translate_progress = Signal(int)  # Лінія "Translate"
    tts_progress = Signal(int)        # Лінія "Synthesis" (TTS)
    
    # Запит на синхронізацію та завершення великих етапів
    sync_required = Signal(list)      
    step_completed = Signal(str, str) # Повертає (ЕТАП, ШЛЯХ_ДО_МЕДІА) для Пункту 6

    def __init__(self, video_path: str):
        super().__init__()
        self.project = Project(video_path)
        self.video_duration = 0.0
        
        self.audio_service = AudioService()
        self.stt_service = STTService()
        self.translate_service = TranslateService()
        self.tts_service = TTSService()

    async def run_full_analysis(self):
        """Етап 1: Повний аналіз медіафайлу, транскрипція, діаризація та переклад"""
        try:
            self.status_changed.emit("🎬 Ініціалізація проєкту та аналіз відео...")
            self.overall_progress.emit(2)

            with VideoFileClip(self.project.video_path) as clip:
                self.video_duration = clip.duration
            self.status_changed.emit(f"⏱ Тривалість відео: {self.video_duration:.2f} сек.")
            
            # 1. Розділення аудіодоріжок через Demucs
            self.status_changed.emit("🎧 Відокремлення вокалу від фонового супроводу (Demucs)...")
            self.audio_progress.emit(10)  # Старт лінії Audio
            
            # Передаємо колбек всередину AudioService (якщо він підтримує чанки) або емулюємо старт/фініш
            self.project.background_path, self.project.vocals_path = \
                await self.audio_service.extract_and_separate(self.project.video_path)
            
            self.audio_progress.emit(100) # Лінія Audio завершена
            self.overall_progress.emit(30)

            # 2. Розпізнавання мовлення та спікерів (Whisper + Pyannote)
            self.status_changed.emit("🧠 Розпізнавання мови та аналіз спікерів (Whisper + Pyannote)...")
            self.stt_progress.emit(0)     # Старт лінії STT
            
            # Передаємо лямбду для динамічного оновлення прогрес-бару STT (Пункт 8)
            segments, speaker_samples = await self.stt_service.process(
                self.project.vocals_path, 
                self.project.source_lang,
                progress_callback=lambda p: self.stt_progress.emit(p)
            )
            self.project.segments = segments
            # Пункт 3: Зберігаємо мапу зразків голосу для майбутнього клонування
            self.project.speaker_voice_map = speaker_samples 
            
            self.stt_progress.emit(100)   # Лінія STT завершена
            self.overall_progress.emit(70)

            # 3. Автоматичний пакетний переклад
            self.status_changed.emit("🌐 Генерація первинного перекладу тексту...")
            self.translate_progress.emit(20)
            
            await self.translate_service.process(self.project.segments, self.project.target_lang)
            
            self.translate_progress.emit(100) # Лінія Translate завершена
            self.overall_progress.emit(90)
            
            # Пункт 5: Автоматично зберігаємо стан проєкту в JSON після Фази 1
            saved_json = self.project.save_to_json()
            self.status_changed.emit(f"💾 Стан проєкту заархівовано: {saved_json}")
            
            # Передаємо дані в інтерфейс для перевірки
            self.status_changed.emit("⏳ Очікування валідації або редагування тексту користувачем...")
            self.sync_required.emit(self.project.segments)
            
            # Пункт 6: Сигналізуємо, що аналіз готовий, передаємо шлях до оригінального відео для плеєра
            self.step_completed.emit("ANALYSIS_DONE", self.project.video_path)
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі аналізу: {str(e)}")
            self.overall_progress.emit(0)

    async def run_synthesis(self):
        """Етап 2: Після ручного редагування — генерація голосу, мікшування та рендеринг відео"""
        try:
            # Пункт 5: Користувач міг внести зміни в текст або налаштування, тому перед TTS оновлюємо JSON
            self.project.save_to_json()
            
            self.status_changed.emit("🎙️ Запуск нейронного синтезу мовлення (Клонування голосу)...")
            self.tts_progress.emit(10)
            self.overall_progress.emit(5)
            
            # 1. Генерація аудіо для ВСІХ або тільки для MODIFIED сегментів (Частковий перерендеринг)
            # Передаємо self.project.speaker_voice_map для клонування голосу на основі вирізаних WAV-файлів
            voice_results = await self.tts_service.process_all(
                self.project.segments, 
                self.project.target_lang,
                speaker_refs=self.project.speaker_voice_map, # Для Пункту 3
                progress_callback=lambda p: self.tts_progress.emit(p) # Для Пункту 8
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
            
            # 3. Інтеграція нової доріжки у відеоряд через MoviePy
            self.status_changed.emit("🎞️ Програмний монтаж та кодування відео (MoviePy libx264)...")
            self.overall_progress.emit(85)
            
            # Передаємо ЖИВИЙ об'єкт final_audio_obj прямо в аргумент audio_segment, як і хоче твій export.py!
            await asyncio.to_thread(
                export_final,
                video_path=self.project.video_path,
                audio_segment=final_audio_obj,  # ПЕРЕДАЄМО ОБ'ЄКТ, А НЕ РЯДОК
                output_path=self.project.output_video_path
            )
            
            # Маркуємо успішно згенеровані сегменти як 'rendered'
            for seg in self.project.segments:
                if seg.status == "modified" or seg.status == "transcribed":
                    seg.status = "rendered"
            
            # Фінальний автосейв стану проєкту в архів
            self.project.save_to_json()
            
            self.status_changed.emit(f"🎉 Локалізацію завершено! Файл збережено: {self.project.output_video_path}")
            self.overall_progress.emit(100)
            
            # Повертаємо шлях до готового відео для автоматичного старту у плеєрі
            self.step_completed.emit("SYNTHESIS_DONE", self.project.output_video_path)
            
        except Exception as e:
            self.status_changed.emit(f"❌ Помилка на етапі рендеру: {str(e)}")
            self.overall_progress.emit(0)
            
    def load_archived_project(self, json_path: str):
        """Метод для Пункту 5: Завантаження проєкту з архіву без повторного запуску AI"""
        try:
            self.project = Project.load_from_json(json_path)
            self.status_changed.emit(f"📂 Проєкт успішно відновлено з файлу: {json_path}")
            # Відправляємо відновлені сегменти прямо в UI картки
            self.sync_required.emit(self.project.segments)
            self.step_completed.emit("ANALYSIS_DONE", self.project.video_path)
        except Exception as e:
            self.status_changed.emit(f"❌ Не вдалося завантажити проєкт: {str(e)}")