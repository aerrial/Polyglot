import sys
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QProgressBar, QTextEdit, QFileDialog, QLabel
from PySide6.QtCore import QObject, Signal
from ui.worker import DubbingWorker

class StreamToLogger(QObject):
    """Клас для перенаправлення stdout у сигнал Qt"""
    new_text = Signal(str)

    def write(self, text):
        if text.strip(): # ігноруємо пусті рядки
            self.new_text.emit(str(text))

    def flush(self):
        # Потрібно для сумісності з sys.stdout
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Video Dubbing Tool")
        self.setMinimumSize(800, 600)

        # Зберігаємо шлях до обраного відео тут
        self.selected_path = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 1. Секція вибору файлу
        self.label_path = QLabel("Файл не обрано")
        self.btn_select = QPushButton("📁 Обрати відео")
        layout.addWidget(self.label_path)
        layout.addWidget(self.btn_select)

        # 2. Кнопка запуску
        self.btn_run = QPushButton("🚀 Запустити локалізацію")
        self.btn_run.setEnabled(False) # Вимкнена, поки не обрано файл
        layout.addWidget(self.btn_run)

        # 3. Прогрес-бар (FR-008)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # 4. Консоль логів (FR-009)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Створюємо перехоплювач
        self.stream_logger = StreamToLogger()
        self.stream_logger.new_text.connect(self.log_output.append)

        # Перенаправляємо stdout (звичайні print) та stderr (помилки)
        sys.stdout = self.stream_logger
        sys.stderr = self.stream_logger

        # З'єднання сигналів
        self.btn_select.clicked.connect(self.select_file)
        self.btn_run.clicked.connect(self.start_processing)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Оберіть відео", "", "Video Files (*.mp4 *.mkv)")
        if file_path:
            self.selected_path = file_path
            self.label_path.setText(f"Файл: {file_path}")
            self.btn_run.setEnabled(True) # Тепер можна запускати
            self.log_output.append(f"✅ Обрано файл: {file_path}")

    def start_processing(self):
        # Тепер ми беремо шлях зі змінної, а не з неіснуючого поля
        if not self.selected_path:
            return

        self.btn_run.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.log_output.append("<b>⏳ Починаю обробку...</b>")

        # Створюємо та запускаємо воркер
        self.worker = DubbingWorker(self.selected_path, "en") # "en" можна замінити на вибір з ComboBox
        
        # Підключаємо сигнали з worker.py
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log_output.append)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)

        self.worker.start()

    def on_finished(self, message):
        self.log_output.append(f"<span style='color: green;'>{message}</span>")
        self.btn_run.setEnabled(True)
        self.btn_select.setEnabled(True)

    def on_error(self, error_traceback):
        self.log_output.append(f"<span style='color: red;'>❌ ПОМИЛКА:</span>\n{error_traceback}")
        self.btn_run.setEnabled(True)
        self.btn_select.setEnabled(True)

