import sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, 
    QMainWindow, QPushButton, QProgressBar, QSlider, 
    QSplitter, QVBoxLayout, QWidget
)

class Panel(QFrame):
    def __init__(self, title=""):
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("PanelTitle")
            layout.addWidget(self.title_label)

        self.body = QVBoxLayout()
        layout.addLayout(self.body)

class PolyGlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyGlot AI Studio")
        self.resize(1700, 950)
        
        # Ініціалізація медіа-двигуна
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0) # Панелі йдуть до краю
        main_layout.setSpacing(0)

        # --- TOPBAR ---
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(70)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 0, 20, 0)
        
        logo = QLabel("POLYGLOT AI")
        logo.setObjectName("Logo")
        top_bar_layout.addWidget(logo)
        
        # Кнопка New Project
        self.btn_new = QPushButton("+ New Project")
        self.btn_new.setObjectName("NewProjectButton")
        top_bar_layout.addWidget(self.btn_new)
        
        top_bar_layout.addSpacing(40)

        # Навігація
        for item in ["Workspace", "Projects", "Voices", "Settings"]:
            btn = QPushButton(item)
            btn.setObjectName("NavButton")
            top_bar_layout.addWidget(btn)

        top_bar_layout.addStretch()
        
        self.status_badge = QLabel("Translating 84%")
        self.status_badge.setObjectName("WarningBadge")
        top_bar_layout.addWidget(self.status_badge)

        main_layout.addWidget(top_bar)

        # --- WORKSPACE ---
        # Контейнер з відступами, щоб блоки не тулилися до країв з боків
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(15, 15, 15, 15) # Знизу 0 для ефекту продовження
        
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(15) # Відступи між головними блоками

        # 1. Left: Transcript
        self.left_panel = Panel("Transcript Editor")
        self.transcript_list = QListWidget()
        self.left_panel.body.addWidget(self.transcript_list)

        # 2. Middle: Video + Timeline
        middle_container = QWidget()
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setSpacing(15)
        middle_layout.setContentsMargins(0, 0, 0, 0)

        # VIDEO PLAYER
        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("VideoPlayer")
        self.media_player.setVideoOutput(self.video_widget)
        
        # Controls for Video
        controls_panel = QFrame()
        controls_panel.setObjectName("ControlsPanel")
        controls_layout = QHBoxLayout(controls_panel)
        self.play_btn = QPushButton("▶")
        self.slider = QSlider(Qt.Horizontal)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.slider)

        # Timeline
        self.timeline_panel = Panel("Timeline")
        self.timeline_panel.setFixedHeight(280)

        middle_layout.addWidget(self.video_widget, stretch=5)
        middle_layout.addWidget(controls_panel)
        middle_layout.addWidget(self.timeline_panel, stretch=2)

        # 3. Right: Inspector split into two
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.speaker_panel = Panel("Speaker Inspector")
        self.pipeline_panel = Panel("AI Pipeline Progress")
        
        # AI Pipeline content example
        for task in ["Transcription", "Diarization", "Translation"]:
            lbl = QLabel(task)
            bar = QProgressBar()
            bar.setValue(70)
            self.pipeline_panel.body.addWidget(lbl)
            self.pipeline_panel.body.addWidget(bar)
        self.pipeline_panel.body.addStretch()

        right_layout.addWidget(self.speaker_panel, stretch=3)
        right_layout.addWidget(self.pipeline_panel, stretch=2)

        # Додавання до спліттера
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(middle_container)
        self.main_splitter.addWidget(right_container)
        self.main_splitter.setStretchFactor(1, 4)

        content_layout.addWidget(self.main_splitter)
        main_layout.addWidget(content_wrapper)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PolyGlotWindow()
    window.show()
    sys.exit(app.exec())