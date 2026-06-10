# ui/components/segment_card.py
import asyncio
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
from qasync import asyncSlot
from core.project import TimelineSegment

class SegmentCardWidget(QWidget):
    def __init__(self, segment: TimelineSegment, controller, parent_window):
        super().__init__()
        self.segment = segment
        self.controller = controller
        self.parent_window = parent_window 
        self.setObjectName("SegmentCardWidget")
        self.init_ui()
        self.apply_card_styles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        meta_layout = QHBoxLayout()
        time_str = f"🕒 {int(self.segment.start // 60):02}:{int(self.segment.start % 60):02}"
        self.lbl_meta = QLabel(f"{time_str} | {self.segment.speaker_id}")
        self.lbl_meta.setObjectName("MetaLabel")
        meta_layout.addWidget(self.lbl_meta)
        meta_layout.addStretch()
        main_layout.addLayout(meta_layout)

        fields_layout = QHBoxLayout()
        
        self.edit_orig = QTextEdit(self.segment.original_text)
        self.edit_orig.setFixedHeight(50)
        self.edit_orig.setObjectName("EditOriginal")
        self.edit_orig.textChanged.connect(self.on_original_changed)
        
        self.edit_trans = QTextEdit(self.segment.translated_text)
        self.edit_trans.setFixedHeight(50)
        self.edit_trans.setObjectName("EditTranslated")
        self.edit_trans.textChanged.connect(self.on_translation_changed)

        fields_layout.addWidget(self.edit_orig)
        fields_layout.addWidget(self.edit_trans)
        main_layout.addLayout(fields_layout)

    def apply_card_styles(self):
        # Динамічно адаптуємо кольори картки під тему головного вікна
        is_light = self.parent_window.theme_btn.isChecked() if self.parent_window else False

        if is_light:
            # Світла тема
            self.lbl_meta.setStyleSheet("color: #6200ee; font-weight: bold; font-size: 11px;")
            self.edit_orig.setStyleSheet("""
                QTextEdit { background: #f1f3f4; border: 1px solid #ced4da; color: #5f6368; border-radius: 4px; }
                QTextEdit:focus { border: 2px solid #6200ee; background: #ffffff; color: #1c1b1f; }
            """)
            self.edit_trans.setStyleSheet("""
                QTextEdit { background: #ffffff; border: 1px solid #ced4da; color: #1c1b1f; border-radius: 4px; font-weight: 500; }
                QTextEdit:focus { border: 2px solid #6200ee; }
            """)
        else:
            # темна тема
            self.lbl_meta.setStyleSheet("color: #8B7CFF; font-weight: bold; font-size: 11px;")
            self.edit_orig.setStyleSheet("""
                QTextEdit { background: #111111; border: 1px solid #222222; color: #aaaaaa; border-radius: 4px; }
                QTextEdit:focus { border: 1px solid #8B7CFF; color: #ffffff; }
            """)
            self.edit_trans.setStyleSheet("""
                QTextEdit { background: #222222; border: 1px solid #333333; color: #ffffff; border-radius: 4px; }
                QTextEdit:focus { border: 1px solid #8B7CFF; }
            """)

    def on_translation_changed(self):
        new_text = self.edit_trans.toPlainText()
        if self.segment.translated_text != new_text:
            self.segment.translated_text = new_text
            self.segment.status = "modified" 

    def on_original_changed(self):
        new_orig = self.edit_orig.toPlainText()
        if self.segment.original_text != new_orig:
            self.segment.original_text = new_orig
            self.segment.status = "modified"
            
            if hasattr(self, 'qt_debounce_timer'):
                self.qt_debounce_timer.stop()
            else:
                self.qt_debounce_timer = QTimer()
                self.qt_debounce_timer.setSingleShot(True)
                
            try:
                self.qt_debounce_timer.timeout.disconnect()
            except Exception:
                pass
                
            def timeout_slot():
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.trigger_single_translation(new_orig))
                
            self.qt_debounce_timer.timeout.connect(timeout_slot)
            self.qt_debounce_timer.start(800)

    async def trigger_single_translation(self, text):
        if not text.strip(): return
        try:
            self.edit_trans.textChanged.disconnect(self.on_translation_changed)
            max_dur = float(self.segment.end - self.segment.start)
            
            from core import settings
            target_lang = settings.TARGET_LANGUAGE
            
            if not hasattr(self.controller, 'translate_service') or self.controller.translate_service is None:
                from services.translate_service import TranslateService
                self.controller.translate_service = TranslateService()
                
            translated = await self.controller.translate_service.translate_single_text(
                text, max_dur, target_lang
            )
            
            self.segment.translated_text = translated
            self.edit_trans.setPlainText(translated)
            self.edit_trans.textChanged.connect(self.on_translation_changed)
            
            if self.parent_window:
                self.parent_window.add_log(f"✍️ Живий автопереклад для сегмента {self.segment.id} оновлено.")
                
        except Exception as e:
            print(f"Помилка поштучного живого перекладу: {e}")
            try:
                self.edit_trans.textChanged.connect(self.on_translation_changed)
            except Exception:
                pass