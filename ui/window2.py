import sys
import asyncio
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QProgressBar, QSlider, QSplitter, QVBoxLayout, QWidget, QFileDialog
)

# Імпортуємо твій контролер (переконайся, що шлях правильний)
# from controllers.localization_controller import LocalizationController

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
        
        # Контролер (ініціалізуємо як None, поки не вибрано файл)
        self.controller = None
        
        # Медіа плеєр
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
        self.main_splitter.setHandleWidth(15) # Замість setSpacing

        # 1. Transcript
        self.transcript_panel = Panel("Transcript Editor")
        self.transcript_list = QListWidget()
        self.transcript_panel.body.addWidget(self.transcript_list)

        # 2. Middle (Video + Timeline)
        mid_container = QWidget()
        mid_layout = QVBoxLayout(mid_container)
        mid_layout.setSpacing(15)
        mid_layout.setContentsMargins(0,0,0,0)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("VideoPlayer")
        self.media_player.setVideoOutput(self.video_widget)
        
        self.slider = QSlider(Qt.Horizontal)
        self.play_btn = QPushButton("▶")
        self.play_btn.clicked.connect(self.toggle_playback)

        self.timeline_panel = Panel("Timeline")
        self.timeline_panel.setFixedHeight(280)

        mid_layout.addWidget(self.video_widget, stretch=5)
        mid_layout.addWidget(self.play_btn) # Спрощено для прикладу
        mid_layout.addWidget(self.timeline_panel, stretch=2)

        # 3. Right (Inspector + Pipeline)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0,0,0,0)

        self.speaker_panel = Panel("Speaker Inspector")
        self.pipeline_panel = Panel("AI Pipeline Progress")
        
        # Словник для прогрес-барів, щоб звертатися до них з контролера
        self.progress_widgets = {}
        for step in ["Overall", "Audio", "STT", "Translate"]:
            lbl = QLabel(step)
            bar = QProgressBar()
            bar.setRange(0, 100)
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
    def open_new_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.mkv *.avi)")
        if path:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.status_label.setText("Video Loaded")
            
            # Ініціалізація твого контролера
            # self.controller = LocalizationController(path)
            # self.connect_controller()
            # asyncio.create_task(self.controller.run_full_analysis())

    def connect_controller(self):
        """Зв'язка сигналів контролера з методами UI"""
        self.controller.status_changed.connect(self.update_ui_status)
        self.controller.progress_changed.connect(self.progress_widgets["Overall"].setValue)
        self.controller.sync_required.connect(self.fill_transcript)

    @Slot(str)
    def update_ui_status(self, message):
        self.status_label.setText(message)
        # Також можна додавати в лог всередині панелі

    @Slot(list)
    def fill_transcript(self, segments):
        self.transcript_list.clear()
        for seg in segments:
            # seg — це об'єкт TimelineSegment з твоєї core.project
            item = QListWidgetItem(f"[{seg.start:.2f}] Speaker {seg.speaker}:\n{seg.text}")
            self.transcript_list.addItem(item)

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("▶")
        else:
            self.media_player.play()
            self.play_btn.setText("⏸")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #0A0A0A; }
            QWidget { color: #E0E0E0; font-family: 'Inter', sans-serif; }
            
            #TopBar { 
                background: #111111; 
                border-bottom: 1px solid #1F1F1F; 
            }
            
            #Logo { 
                font-size: 16px; font-weight: 900; color: #8B7CFF; 
                margin-right: 15px; letter-spacing: 1px;
            }

            #NewProjectButton {
                background: #222222;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }
            #NewProjectButton:hover { background: #2A2A2A; border-color: #8B7CFF; }

            #NavButton {
                background: transparent; border: none;
                padding: 10px 15px; color: #888; font-weight: 600;
            }
            #NavButton:hover { color: #8B7CFF; }

            #Panel {
                background: #121212;
                border: 1px solid #1F1F1F;
                border-radius: 20px; /* Заокруглення з усіх сторін */
            }

            #PanelTitle { 
                color: #555; font-size: 13px; font-weight: 800; 
                text-transform: uppercase; letter-spacing: 1px; 
            }

            #VideoPlayer {
                background: #000;
                border-radius: 20px;
                border: 1px solid #1F1F1F;
            }

            #ControlsPanel {
                background: #121212;
                border-radius: 15px;
                padding: 5px;
            }

            #WarningBadge {
                background: rgba(139, 124, 255, 0.1);
                color: #8B7CFF;
                border: 1px solid rgba(139, 124, 255, 0.3);
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: 700;
            }

            QProgressBar {
                background: #1A1A1A;
                border-radius: 4px;
                text-align: center;
                height: 8px;
            }
            QProgressBar::chunk {
                background: #8B7CFF;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                border: none; background: transparent; width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #333; border-radius: 4px;
            }
            
            QSplitter::handle {
                background: transparent; /* Робимо розділювач невидимим */
            }
        """)

# Для запуску asyncio з PySide6 рекомендую інсталювати qasync
# pip install qasync
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PolyGlotWindow()
    window.show()
    sys.exit(app.exec())