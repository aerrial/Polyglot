import asyncio
import traceback
from PySide6.QtCore import QThread, Signal
from pipeline import run_localization_pipeline

class DubbingWorker(QThread):
    # Сигнали для зв'язку з головним вікном
    progress_signal = Signal(int)    # Оновлення прогрес-бару
    log_signal = Signal(str)         # Вивід тексту в консоль логів
    finished_signal = Signal(str)    # Успішне завершення
    error_signal = Signal(str)       # Повідомлення про помилку

    def __init__(self, video_path, target_lang):
        super().__init__()
        self.video_path = video_path
        self.target_lang = target_lang

    def run(self):
        """Вхідна точка потоку QThread"""
        try:
            # Створюємо новий цикл подій asyncio для цього потоку
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаємо асинхронний пайплайн
            loop.run_until_complete(self.execute())
            loop.close()
        except Exception:
            self.error_signal.emit(traceback.format_exc())

    async def execute(self):
        """Виклик пайплайну з передачею callback-функції"""
        
        # Функція-міст, яка прокидає дані з asyncio в Qt Signals
        def update_gui_progress(value):
            self.progress_signal.emit(value)

        self.log_signal.emit("🚀 <b>Ініціалізація системи...</b>")
        
        # Викликаємо твій змінений пайплайн
        # Тепер він буде сам "рухати" прогрес-бар через наш callback
        await run_localization_pipeline(
            video_path=self.video_path, 
            target_lang=self.target_lang,
            progress_callback=update_gui_progress
        )
        
        self.finished_signal.emit("✨ Локалізація завершена успішно!")