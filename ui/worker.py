# ui/worker.py
from PySide6.QtCore import QThread, Signal
import asyncio
import traceback
import pipeline # Імпортуємо модуль для доступу до shared_data та event

class DubbingWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str)
    finished_signal = Signal(str)
    error_signal = Signal(str)
    edit_required_signal = Signal(list) 

    def __init__(self, video_path, target_path, target_lang_code):
        super().__init__()
        self.video_path = video_path
        self.target_path = target_path
        self.target_lang_code = target_lang_code
        self.loop = None

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.execute())
        except Exception as e:
            # Виводимо повний шлях помилки для дебагу
            err_details = traceback.format_exc()
            print(f"Критична помилка воркера:\n{err_details}")
            self.error_signal.emit(str(e))

    async def execute(self):
        def progress_callback(data):
            if isinstance(data, tuple):
                if data[0] == "WAIT_FOR_EDIT":
                    pipeline.shared_data["segments"] = data[1]
                    self.edit_required_signal.emit(data[1])
                elif data[0] == "SPEAKERS_LOADED":
                    # Тут можна додати новий сигнал, але поки просто виведемо в лог
                    self.log_signal.emit(f"Detected {len(data[1])} speakers")
            elif isinstance(data, int):
                self.progress_signal.emit(data)
            elif isinstance(data, str):
                self.log_signal.emit(data)