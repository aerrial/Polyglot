import sys
import os
import asyncio
import datetime
from qasync import QEventLoop, asyncSlot
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QProgressBar, QSlider, QSplitter, QVBoxLayout, 
    QWidget, QFileDialog, QInputDialog, QTextEdit
)
from controllers.localization_controller import LocalizationController

class Panel(QFrame):
    def __init__(self, title=""):
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("PanelTitle")
            layout.addWidget(lbl)
        self.body = QVBoxLayout()
        layout.addLayout(self.body)

class PolyGlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyGlot AI Studio")
        self.resize(1700, 950)
        
        self.controller = None
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TOPBAR ---
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(70)
        top_layout = QHBoxLayout(top_bar)
        
        logo = QLabel("POLYGLOT AI")
        logo.setObjectName("Logo")
        top_layout.addWidget(logo)

        self.btn_new = QPushButton("+ New Project")
        self.btn_new.setObjectName("NewProjectButton")
        self.btn_new.clicked.connect(self.open_new_project)
        top_layout.addWidget(self.btn_new)

        # НОВА КНОПКА: Завантаження відео
        self.btn_upload = QPushButton("📥 Upload Video")
        self.btn_upload.setObjectName("UploadButton")
        self.btn_upload.clicked.connect(self.upload_video_action)
        top_layout.addWidget(self.btn_upload)

        top_layout.addSpacing(30)
        for item in ["Workspace", "Projects", "Voices", "Settings"]:
            btn = QPushButton(item)
            btn.setObjectName("NavButton")
            top_layout.addWidget(btn)

        top_layout.addStretch()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("WarningBadge")
        top_layout.addWidget(self.status_label)
        main_layout.addWidget(top_bar)

        # --- WORKSPACE ---
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 0)
        
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(15)

        # 1. Transcript Editor (Тільки для тексту спікерів)
        self.transcript_panel = Panel("Transcript Editor")
        self.transcript_list = QListWidget()
        self.transcript_panel.body.addWidget(self.transcript_list)

        # Кнопка підтвердження
        self.btn_confirm = QPushButton("✅ ПІДТВЕРДИТИ ТЕКСТ")
        self.btn_confirm.setObjectName("NewProjectButton")
        self.btn_confirm.setFixedHeight(45)
        self.btn_confirm.setEnabled(False) # Вона заблокована до завершення STT
        self.btn_confirm.clicked.connect(self.confirm_and_synthesize)
        self.transcript_panel.body.addWidget(self.btn_confirm)

        # 2. Middle (Video + System Logs)
        mid_container = QWidget()
        mid_layout = QVBoxLayout(mid_container)
        mid_layout.setSpacing(15)
        mid_layout.setContentsMargins(0,0,0,0)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("VideoPlayer")
        self.video_widget.setMinimumHeight(400)
        self.media_player.setVideoOutput(self.video_widget)
        
        self.play_btn = QPushButton("▶ PLAY / PAUSE")
        self.play_btn.setFixedHeight(40)
        self.play_btn.clicked.connect(self.toggle_playback)

        self.console_panel = Panel("System Logs")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("LogConsole")
        self.console_panel.body.addWidget(self.log_console)
        
        mid_layout.addWidget(self.video_widget, stretch=5)
        mid_layout.addWidget(self.play_btn)
        mid_layout.addWidget(self.console_panel, stretch=3)

        # 3. Right (Inspector + Pipeline)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0,0,0,0)

        self.speaker_panel = Panel("Speaker Inspector")
        self.pipeline_panel = Panel("AI Pipeline Progress")
        
        self.progress_widgets = {}
        for step in ["Overall", "Audio", "STT", "Translate"]:
            lbl = QLabel(step)
            bar = QProgressBar()
            self.pipeline_panel.body.addWidget(lbl)
            self.pipeline_panel.body.addWidget(bar)
            self.progress_widgets[step] = bar

        right_layout.addWidget(self.speaker_panel, stretch=3)
        right_layout.addWidget(self.pipeline_panel, stretch=2)

        self.main_splitter.addWidget(self.transcript_panel)
        self.main_splitter.addWidget(mid_container)
        self.main_splitter.addWidget(right_container)
        self.main_splitter.setStretchFactor(1, 4)

        content_layout.addWidget(self.main_splitter)
        main_layout.addWidget(content)

    # --- LOGIC ---
    def connect_signals(self):
        if self.controller:
            # З'єднуємо статус (текст) з консоллю
            self.controller.status_changed.connect(self.add_log)
            # З'єднуємо прогрес (число) з баром
            self.controller.progress_changed.connect(self.progress_widgets["Overall"].setValue)
            # З'єднуємо результат (список сегментів) з редактором
            self.controller.sync_required.connect(self.fill_transcript)
            
            self.add_log("✅ Канали зв'язку з ШІ-модулем налагоджено")

    @Slot(str)
    def add_log(self, message):
        """Виводить логи ТІЛЬКИ в System Logs"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#888;'>[{timestamp}]</span> {message}")
        self.status_label.setText(message) # Дублюємо коротко в бадж зверху

    @asyncSlot()
    async def open_new_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.mkv *.avi)")
        if not path: return

        self.add_log(f"📁 Файл обрано: {path}")
        
        languages = ["English", "Ukrainian", "French", "German", "Spanish"]
        lang, ok = QInputDialog.getItem(self, "Settings", "Language:", languages, 0, False)
        
        if ok and lang:
            # Завантаження відео
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.add_log("🎬 Відео завантажено в плеєр")
            self.btn_confirm.setText("⏳ ОБРОБКА ШІ...")
            # ТУТ МАЄ БУТИ ІНІЦІАЛІЗАЦІЯ ТВОГО КОНТРОЛЕРА
            self.controller = LocalizationController(path)
            self.connect_signals()
            await self.controller.run_full_analysis()

    @asyncSlot()
    async def confirm_and_synthesize(self):
        """Викликається при натисканні на кнопку підтвердження"""
        if self.controller:
            self.add_log("🎙️ Текст підтверджено користувачем. Починаємо синтез...")
            self.btn_confirm.setEnabled(False) # Блокуємо кнопку, щоб не натиснути двічі

            try:
                # Викликаємо метод з вашого LocalizationController
                await self.controller.run_synthesis() 
                self.add_log("✨ Процес озвучення завершено успішно!")
            except Exception as e:
                self.add_log(f"❌ Помилка синтезу: {str(e)}")
                self.btn_confirm.setEnabled(True)
    
    @asyncSlot()
    async def upload_video_action(self):
        """Функція для кнопки вибору місця збереження фінального відео"""
        if not self.controller:
            self.add_log("⚠️ Спочатку завантажте відео, щоб система створила проєкт!")
            return
    
        # Відкриваємо діалог "Зберегти як..."
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Оберіть місце для збереження готового відео", 
            self.controller.project.base_name + "_localized.mp4", # Дефолтне ім'я
            "Відео файли (*.mp4)"
        )
        
        if path:
            # ЗАПИСУЄМО ШЛЯХ НАПРЯМУ В ПРОЄКТ
            self.controller.project.output_video_path = path
            
            # Оновлюємо інтерфейс
            filename = os.path.basename(path)
            self.btn_select_out.setText(f"✓ {filename}")
            self.add_log(f"💾 Шлях для фінального експорту задано: {path}")
    
    @Slot(list)
    def fill_transcript(self, segments):
        """Виводить текст у вигляді блоків: Час, Спікер та Текст"""
        self.transcript_list.clear()
        
        for seg in segments:
            # 1. Шукаємо ID спікера
            s_id = getattr(seg, 'speaker_id', getattr(seg, 'speaker', 'Unknown'))
            
            # 2. Шукаємо текст (пробуємо різні варіанти атрибутів)
            # Перевіряємо спочатку перекладений текст, потім оригінальний
            text = getattr(seg, 'translated_text', None)
            if not text:
                text = getattr(seg, 'text', '[Текст не знайдено]')
            
            # 3. Шукаємо час початку
            start = getattr(seg, 'start', 0.0)
            time_str = f"{int(start // 60):02}:{int(start % 60):02}"
            
            # Створюємо блок
            display_text = f"🕒 {time_str} | Спікер {s_id}\n{text}"
            
            item = QListWidgetItem(display_text)
            self.transcript_list.addItem(item)
        
        self.add_log(f"✅ Завантажено {len(segments)} сегментів")
        
        # Активуємо кнопку підтвердження
        self.btn_confirm.setEnabled(True)
        self.btn_confirm.setText("✅ ПІДТВЕРДИТИ ТЕКСТ")

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #0A0A0A; }
            QWidget { color: #E0E0E0; font-family: 'Inter', sans-serif; }
            #TopBar { background: #111111; border-bottom: 1px solid #1F1F1F; }
            #Logo { font-size: 16px; font-weight: 900; color: #8B7CFF; margin-right: 15px; letter-spacing: 1px; }
            #NewProjectButton { background: #8B7CFF; color: black; border-radius: 8px; padding: 6px 14px; font-weight: 600; }
            #Panel { background: #121212; border: 1px solid #1F1F1F; border-radius: 20px; }
            #PanelTitle { color: #555; font-size: 13px; font-weight: 800; text-transform: uppercase; }
            #LogConsole { background: #080808; border: none; font-family: 'Consolas'; font-size: 11px; color: #8B7CFF; }
            #VideoPlayer { background: #000; border-radius: 20px; }
            #WarningBadge { background: rgba(139, 124, 255, 0.1); color: #8B7CFF; border: 1px solid rgba(139, 124, 255, 0.3); border-radius: 12px; padding: 4px 12px; }
            QProgressBar { background: #1A1A1A; border-radius: 4px; height: 6px; text-align: center; }
            QProgressBar::chunk { background: #8B7CFF; }
            QSplitter::handle { background: transparent; }
            /* Стилізація блоків у Transcript Editor */
            QListWidget::item {
                background: #1A1A1A;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 12px;
                margin-bottom: 8px;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                border: 1px solid #8B7CFF;
                background: #252525;
            }
            #UploadButton {
                background: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                margin-left: 10px;
            }
            #UploadButton:hover {
                background: #353535;
                border-color: #8B7CFF;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = PolyGlotWindow()
    window.show()
    with loop:
        loop.run_forever()


# languages = ["English", "Ukrainian", "French", "German", "Spanish"]