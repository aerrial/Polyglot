import os
import sys
from PySide6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, 
                               QWidget, QFileDialog, QProgressBar, 
                               QPlainTextEdit, QLabel, QComboBox)
from ui.worker import DubbingWorker
import pipeline
import config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyGlot")
        self.resize(600, 500)
        
        # Сховище для даних
        self.input_file = ""
        self.output_file = ""
        
        # UI Елементи
        layout = QVBoxLayout()
        
        # 1. Вибір файлів 
        self.btn_input = QPushButton("Обрати відео")
        self.btn_input.clicked.connect(self.select_input)
        
        self.btn_output = QPushButton("Куди зберегти результат")
        self.btn_output.clicked.connect(self.select_output)
        
        # 2. Налаштування 
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(list(config.SUPPORTED_LANGUAGES.keys()))
        
        # 3. Моніторинг 
        self.progress = QProgressBar()
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        
        # 4. РЕДАКТОР ТРАНСКРИПЦІЇ 
        self.label_edit = QLabel("Відредагуйте текст (якщо потрібно):")
        self.edit_area = QPlainTextEdit()
        self.btn_confirm_edit = QPushButton("Підтвердити текст та продовжити")
        self.btn_confirm_edit.setEnabled(False)
        self.btn_confirm_edit.clicked.connect(self.confirm_edit)
        
        self.btn_run = QPushButton("ЗАПУСТИТИ ЛОКАЛІЗАЦІЮ")
        self.btn_run.clicked.connect(self.start_process)

# 
        # Додаємо все в лейаут
        for w in [self.btn_input, self.btn_output, QLabel("Оберіть мову:"), 
                  self.combo_lang, self.btn_run, self.progress, 
                  self.log_console, self.label_edit, self.edit_area, self.btn_confirm_edit]:
            layout.addWidget(w)
            
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # --- ЛОГІКА ТЕСТ-КЕЙСІВ ---

    def select_input(self):
    # Отримуємо шлях до файлу. QFileDialog повертає кортеж (шлях, фільтр)
        file_path, _ = QFileDialog.getOpenFileName(self, "Обрати відео", "", "Video (*.mp4 *.mkv *.avi)")
        
        if file_path:
            self.input_file = file_path  # ОНОВЛЮЄМО ЗМІННУ КЛАСУ
            self.log_console.appendPlainText(f"📂 Обрано файл: {file_path}")
            # Можна також вивести назву файлу на кнопку або мітку
            self.btn_input.setText(f"Файл: {os.path.basename(file_path)}")
        else:
            self.log_console.appendPlainText("⚠️ Файл не було обрано")

    def select_output(self):
        # Відкриваємо діалог збереження файлу
        file_path, _ = QFileDialog.getSaveFileName(self, "Зберегти результат як...", "", "Video (*.mp4)")

        if file_path:
            self.output_file = file_path
            self.log_console.appendPlainText(f"💾 Файл результату: {file_path}")
            self.btn_output.setText(f"Зберегти в: {os.path.basename(file_path)}")

    def start_process(self):
        print(f"DEBUG: input_file = {self.input_file}")
        if not self.input_file:
            self.log_console.appendPlainText("Помилка: оберіть файли!")
            return
            
        target_lang_name = self.combo_lang.currentText()
        target_lang_code = config.SUPPORTED_LANGUAGES[target_lang_name]

        # Передаємо в воркер тільки код мови
        self.worker = DubbingWorker(
            self.input_file, 
            self.output_file, 
            target_lang_code
        )
        
        # Підключення сигналів 
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log_console.appendPlainText)
        
        # Обробка запиту на редагування 
        self.worker.edit_required_signal.connect(self.handle_edit_request)
        
        self.worker.start()

    def handle_edit_request(self, segments):
        # Перетворюємо об'єкти сегментів у текст для редагування
        full_text = "\n".join([s.text for s in segments])
        self.edit_area.setPlainText(full_text)
        self.btn_confirm_edit.setEnabled(True)
        self.log_console.appendPlainText("⚠️ ПАУЗА: Перевірте текст у полі редагування.")

    def confirm_edit(self):
        import pipeline
        # 1. Оновлюємо дані в shared_data
        # Беремо текст з текстового поля і розбиваємо на рядки
        new_text_lines = self.edit_area.toPlainText().split("\n")
        
        # Тепер 'pipeline' точно визначено
        if pipeline.shared_data["segments"]:
            for i, line in enumerate(new_text_lines):
                if i < len(pipeline.shared_data["segments"]):
                    pipeline.shared_data["segments"][i].text = line.strip()
    
        # 2. Передача сигналу воркеру
        if hasattr(self, 'worker') and self.worker.loop and pipeline._current_event:
            self.log_console.appendPlainText("✅ Текст підтверджено. Продовжую роботу...")
            # Використовуємо безпечний виклик сигналу
            self.worker.loop.call_soon_threadsafe(pipeline._current_event.set)
        else:
            self.log_console.appendPlainText("⚠️ Помилка: Не вдалося знайти активний процес або подію.")
    
        self.btn_confirm_edit.setEnabled(False)

    def rebuild_segments(self, new_texts):
        # Проста логіка заміни тексту в існуючих сегментах
        # (в реальному коді тут треба мапити по індексах)
        if pipeline.shared_data["segments"]:
            for i, text in enumerate(new_texts):
                if i < len(pipeline.shared_data["segments"]):
                    pipeline.shared_data["segments"][i].text = text
        return pipeline.shared_data["segments"]