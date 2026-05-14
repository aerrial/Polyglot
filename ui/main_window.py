import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QFrame, QSplitter, QListWidget, 
    QListWidgetItem, QFileDialog, QComboBox
)
import config
import pipeline
from ui.worker import DubbingWorker

# --- КОМПОНЕНТИ СТИЛЮ ---

class SidebarButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(46)
        self.setObjectName("SidebarButton")

class Panel(QFrame):
    def __init__(self, title=""):
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        if title:
            label = QLabel(title)
            label.setObjectName("PanelTitle")
            layout.addWidget(label)
        self.body = QVBoxLayout()
        layout.addLayout(self.body)

# --- ГОЛОВНЕ ВІКНО ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyGlot AI Studio Pro")
        self.resize(1700, 980)

        # Дані
        self.input_file = ""
        self.output_file = ""
        self.worker = None

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR (З робочими кнопками)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)

        logo = QLabel("PolyGlot AI\nWorkstation")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(30)

        # Кнопки вибору файлів
        self.btn_in = SidebarButton("📁 Обрати відео")
        self.btn_in.clicked.connect(self.select_input)
        
        self.btn_out = SidebarButton("💾 Куди зберегти")
        self.btn_out.clicked.connect(self.select_output)

        sidebar_layout.addWidget(self.btn_in)
        sidebar_layout.addWidget(self.btn_out)
        
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(QLabel("Мова перекладу:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(list(config.SUPPORTED_LANGUAGES.keys()))
        sidebar_layout.addWidget(self.combo_lang)

        sidebar_layout.addStretch()

        self.btn_run = QPushButton("ЗАПУСТИТИ")
        self.btn_run.setObjectName("NewProjectButton")
        self.btn_run.setMinimumHeight(60)
        self.btn_run.clicked.connect(self.start_process)
        sidebar_layout.addWidget(self.btn_run)

        # 2. CENTRAL AREA
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("Робоча область")
        self.title_label.setObjectName("WorkspaceTitle")
        header.addWidget(self.title_label)
        header.addStretch()
        self.status_badge = QLabel("Очікування")
        self.status_badge.setObjectName("StatusBadge")
        header.addWidget(self.status_badge)
        center_layout.addLayout(header)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Transcript Editor
        self.transcript_panel = Panel("Редактор тексту")
        self.transcript_list = QListWidget()
        self.transcript_panel.body.addWidget(self.transcript_list)
        
        self.btn_confirm = QPushButton("Підтвердити та продовжити")
        self.btn_confirm.setObjectName("PrimaryButton")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.confirm_edit)
        self.transcript_panel.body.addWidget(self.btn_confirm)

        # Console Logs
        self.log_panel = Panel("Логи системи")
        self.log_console = QLabel("Тут з'являтимуться етапи обробки...")
        self.log_console.setWordWrap(True)
        self.log_console.setAlignment(Qt.AlignTop)
        self.log_panel.body.addWidget(self.log_console)
        
        self.progress_bar = QProgressBar()
        self.log_panel.body.addWidget(self.progress_bar)

        splitter.addWidget(self.transcript_panel)
        splitter.addWidget(self.log_panel)
        center_layout.addWidget(splitter)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(center)

    # --- ЛОГІКА РОБОТИ ---

    def select_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Обрати відео", "", "Video (*.mp4 *.mkv)")
        if path:
            self.input_file = path
            self.btn_in.setText(f"✓ {os.path.basename(path)}")
            self.log_console.setText(f"📂 Завантажено: {path}")

    def select_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти як", "", "Video (*.mp4)")
        if path:
            self.output_file = path
            self.btn_out.setText(f"✓ {os.path.basename(path)}")

    def start_process(self):
        if not self.input_file:
            self.log_console.setText("⚠️ Спочатку оберіть відео!")
            return
            
        lang_code = config.SUPPORTED_LANGUAGES[self.combo_lang.currentText()]
        self.worker = DubbingWorker(self.input_file, self.output_file, lang_code)
        
        # З'єднуємо сигнали воркера з новим UI
        self.worker.log_signal.connect(self.log_console.setText)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.edit_required_signal.connect(self.handle_edit_request)
        
        self.worker.start()
        self.btn_run.setEnabled(False)
        self.status_badge.setText("Обробка...")

    def handle_edit_request(self, segments):
        self.transcript_list.clear()
        for seg in segments:
            item = QListWidgetItem(f"[{seg.start:.1f}s] {seg.text}")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.transcript_list.addItem(item)
        
        self.btn_confirm.setEnabled(True)
        self.status_badge.setText("Потрібна перевірка")
        self.status_badge.setObjectName("WarningBadge")
        self.apply_styles()

    def confirm_edit(self):
        # Зберігаємо зміни назад у shared_data
        for i in range(self.transcript_list.count()):
            text = self.transcript_list.item(i).text()
            # Видаляємо таймкод перед збереженням, якщо він там є
            clean_text = text.split("] ", 1)[-1] if "] " in text else text
            pipeline.shared_data["segments"][i].text = clean_text

        if pipeline._current_event:
            self.worker.loop.call_soon_threadsafe(pipeline._current_event.set)
        
        self.btn_confirm.setEnabled(False)
        self.status_badge.setText("Продовження...")
        self.status_badge.setObjectName("StatusBadge")
        self.apply_styles()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #121212; }
            QWidget { color: #EAEAEA; font-family: 'Segoe UI', sans-serif; }
            #Sidebar { background: #181818; border-right: 1px solid #282828; }
            #Logo { font-size: 20px; font-weight: bold; color: #8B7CFF; padding-bottom: 10px; }
            #SidebarButton { background: transparent; border: none; text-align: left; padding-left: 15px; border-radius: 8px; }
            #SidebarButton:hover { background: #282828; }
            #NewProjectButton { background: #8B7CFF; color: #121212; font-weight: bold; border-radius: 12px; }
            #Panel { background: #1E1E1E; border: 1px solid #333; border-radius: 15px; }
            #PanelTitle { font-size: 16px; font-weight: bold; color: #BBB; }
            #StatusBadge { background: #123C31; color: #3FF0B2; border-radius: 10px; padding: 5px 12px; }
            #WarningBadge { background: #453418; color: #FFC857; border-radius: 10px; padding: 5px 12px; }
            #PrimaryButton { background: #3FF0B2; color: #121212; font-weight: bold; border-radius: 10px; height: 40px; }
            QListWidget { background: #181818; border-radius: 10px; padding: 5px; }
            QListWidget::item { background: #252525; margin: 4px; padding: 10px; border-radius: 8px; }
            QProgressBar { background: #282828; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background: #8B7CFF; border-radius: 5px; }
        """)