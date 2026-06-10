# ui/components/speaker_widget.py
import os
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton, QListWidgetItem

class SpeakerRowWidget(QWidget):
    """Картка спікера з преміальним дизайном без маркерів статі"""
    def __init__(self, speaker_id: str, ref_wav: str, parent_window):
        super().__init__()
        self.speaker_id = speaker_id
        self.ref_wav = ref_wav
        self.parent_window = parent_window
        self.init_ui()
        self.apply_row_styles()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        self.lbl_icon = QLabel()
        icon = "👤" if "Unknown" in self.speaker_id else "🎙️"
        self.lbl_icon.setText(icon)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.lbl_name = QLabel(self.speaker_id)
        self.lbl_status = QLabel("Голосовий профіль XTTS")
        
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_status)
        
        self.btn_play_ref = QPushButton("▶ Зразок")
        self.btn_play_ref.setFixedWidth(80)
        self.btn_play_ref.setFixedHeight(26)
        self.btn_play_ref.clicked.connect(self.play_speaker_sample)
        
        layout.addWidget(self.lbl_icon)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.btn_play_ref)

    def apply_row_styles(self):
        # Визначаємо, яка тема активна в головному вікні
        is_light = self.parent_window.theme_btn.isChecked() if self.parent_window else False

        if is_light:
            # Світла тема для інспектора спікерів (максимально контрастна)
            self.lbl_icon.setStyleSheet("font-size: 16px; color: #6200ee; background: transparent;")
            self.lbl_name.setStyleSheet("font-weight: 700; color: #1c1b1f; font-size: 13px; background: transparent;")
            self.lbl_status.setStyleSheet("color: #5f6368; font-size: 10px; font-weight: 500; background: transparent;")
            self.btn_play_ref.setStyleSheet("""
                QPushButton { 
                    background: #ffffff; border: 1px solid #ced4da; border-radius: 5px; 
                    color: #212529; font-size: 11px; font-weight: 600;
                }
                QPushButton:hover { background: #f8f9fa; border-color: #6200ee; color: #6200ee; }
                QPushButton:pressed { background: rgba(139, 124, 255, 0.1); }
            """)
        else:
            # Оригінальна преміальна темна тема
            self.lbl_icon.setStyleSheet("font-size: 16px; color: #8B7CFF; background: transparent;")
            self.lbl_name.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 13px; background: transparent;")
            self.lbl_status.setStyleSheet("color: #71717A; font-size: 10px; font-weight: 500; background: transparent;")
            self.btn_play_ref.setStyleSheet("""
                QPushButton { 
                    background: #202022; border: 1px solid #27272A; border-radius: 5px; 
                    color: #E4E4E7; font-size: 11px; font-weight: 600;
                }
                QPushButton:hover { background: #27272A; border-color: #8B7CFF; color: #FFFFFF; }
                QPushButton:pressed { background: rgba(139, 124, 255, 0.1); }
            """)

    def play_speaker_sample(self):
        self.parent_window.play_shared_sample(self.ref_wav, self.speaker_id)