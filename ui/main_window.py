# main_window.py
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
    QWidget, QFileDialog, QInputDialog, QTextEdit, QLineEdit
)
from controllers.localization_controller import LocalizationController
from core.project import TimelineSegment

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


# ПУНКТ 1 та 2: Кастомна інтерактивна двомовна картка сегмента
class SegmentCardWidget(QWidget):
    def __init__(self, segment: TimelineSegment, controller: LocalizationController, parent_window):
        super().__init__()
        self.segment = segment
        self.controller = controller
        self.parent_window = parent_window # Для надсилання логів
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Метадані репліки (Час та Спікер)
        meta_layout = QHBoxLayout()
        time_str = f"🕒 {int(self.segment.start // 60):02}:{int(self.segment.start % 60):02}"
        lbl_meta = QLabel(f"{time_str} | {self.segment.speaker_id} ({self.segment.gender})")
        lbl_meta.setStyleSheet("color: #8B7CFF; font-weight: bold; font-size: 11px;")
        meta_layout.addWidget(lbl_meta)
        meta_layout.addStretch()
        main_layout.addLayout(meta_layout)

        # Поля редагування тексту
        fields_layout = QHBoxLayout()
        
        # 1. Поле Оригіналу
        self.edit_orig = QTextEdit(self.segment.original_text)
        self.edit_orig.setFixedHeight(50)
        self.edit_orig.setStyleSheet("background: #111; border: 1px solid #222; color: #aaa;")
        self.edit_orig.textChanged.connect(self.on_original_changed)
        
        # 2. Поле Перекладу
        self.edit_trans = QTextEdit(self.segment.translated_text)
        self.edit_trans.setFixedHeight(50)
        self.edit_trans.setStyleSheet("background: #222; border: 1px solid #333; color: #fff;")
        self.edit_trans.textChanged.connect(self.on_translation_changed)

        fields_layout.addWidget(self.edit_orig)
        fields_layout.addWidget(self.edit_trans)
        main_layout.addLayout(fields_layout)

    def on_translation_changed(self):
        """Слот для Пункту 1: Користувач редагує переклад"""
        new_text = self.edit_trans.toPlainText()
        if self.segment.translated_text != new_text:
            self.segment.translated_text = new_text
            self.segment.status = "modified" # Маркуємо для Partial Rerender

    def on_original_changed(self):
        """Слот для Пункту 2: Редагування оригіналу викликає автопереклад"""
        new_orig = self.edit_orig.toPlainText()
        if self.segment.original_text != new_orig:
            self.segment.original_text = new_orig
            self.segment.status = "modified"
            # Запускаємо асинхронний тасок перекладу однієї репліки, щоб UI не зависав
            asyncio.create_task(self.trigger_single_translation(new_orig))

    async def trigger_single_translation(self, text):
        try:
            # Тимчасово блокуємо сигнал, щоб не було зациклення
            self.edit_trans.textChanged.disconnect(self.on_translation_changed)
            
            # Викликаємо сервіс перекладу через контролер для одного сегмента
            translated = await self.controller.translate_service.translate_text(
                text, self.controller.project.target_lang
            )
            self.segment.translated_text = translated
            self.edit_trans.setPlainText(translated)
            
            # Повертаємо сигнал назад
            self.edit_trans.textChanged.connect(self.on_translation_changed)
        except Exception as e:
            print(f"Помилка поштучного перекладу: {e}")


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

        self.btn_upload = QPushButton("📥 Save Video As...")
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

        # 1. Transcript Editor Panel
        self.transcript_panel = Panel("Transcript Editor")
        self.transcript_list = QListWidget()
        self.transcript_list.setStyleSheet("background: #0D0D0D; border: none;")
        self.transcript_panel.body.addWidget(self.transcript_list)

        self.btn_confirm = QPushButton("✅ ПІДТВЕРДИТИ ТЕКСТ ТА ПОЧАТИ ДУБЛЯЖ")
        self.btn_confirm.setObjectName("NewProjectButton")
        self.btn_confirm.setFixedHeight(45)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.confirm_and_synthesize)
        self.transcript_panel.body.addWidget(self.btn_confirm)

        # 2. Middle Container (Player + Logs)
        mid_container = QWidget()
        mid_layout = QVBoxLayout(mid_container)
        mid_layout.setSpacing(15)
        mid_layout.setContentsMargins(0,0,0,0)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("VideoPlayer")
        self.video_widget.setMinimumHeight(400)
        self.media_player.setVideoOutput(self.video_widget)
        mid_layout.addWidget(self.video_widget, stretch=5)
        
        # ПУНКТ 7: Розширений стандартний медіаплеєр
        player_controls = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(50)
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.sliderMoved.connect(self.set_player_position)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("font-family: 'Consolas'; font-size: 12px;")
        
        player_controls.addWidget(self.play_btn)
        player_controls.addWidget(self.time_slider)
        player_controls.addWidget(self.lbl_time)
        mid_layout.addLayout(player_controls)

        # Синхронізація слайдера з плеєром
        self.media_player.positionChanged.connect(self.on_player_position_changed)
        self.media_player.durationChanged.connect(self.on_player_duration_changed)

        self.console_panel = Panel("System Logs")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("LogConsole")
        self.console_panel.body.addWidget(self.log_console)
        mid_layout.addWidget(self.console_panel, stretch=3)

        # 3. Right Container (Inspector + Pipeline)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0,0,0,0)

        self.speaker_panel = Panel("Speaker Inspector")
        self.pipeline_panel = Panel("AI Pipeline Progress")
        
        self.progress_widgets = {}
        for step in ["Overall", "Audio", "STT", "Translate", "Synthesis"]:
            lbl = QLabel(f"{step} Process:")
            bar = QProgressBar()
            bar.setValue(0)
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

    def connect_signals(self):
        if self.controller:
            self.controller.status_changed.connect(self.add_log)
            self.controller.sync_required.connect(self.fill_transcript)
            
            # ПУНКТ 8: Прив'язка індивідуальних прогрес-барів
            self.controller.overall_progress.connect(self.progress_widgets["Overall"].setValue)
            self.controller.audio_progress.connect(self.progress_widgets["Audio"].setValue)
            self.controller.stt_progress.connect(self.progress_widgets["STT"].setValue)
            self.controller.translate_progress.connect(self.progress_widgets["Translate"].setValue)
            self.controller.tts_progress.connect(self.progress_widgets["Synthesis"].setValue)
            
            # ПУНКТ 6: Обробка завершення етапів
            self.controller.step_completed.connect(self.on_pipeline_step_completed)
            
            self.add_log("✅ Канали зв'язку з ШІ-модулем налаштовано")

    # ПУНКТ 6: Відображення перекладеного відео після рендеру
    @Slot(str, str)
    def on_pipeline_step_completed(self, step_type, media_path):
        if step_type == "ANALYSIS_DONE":
            self.add_log("🎉 Фаза аналізу завершена. Текст готовий до валідації.")
        elif step_type == "SYNTHESIS_DONE":
            self.add_log(f"📺 Автоперемикання плеєра на готове дубльоване відео: {media_path}")
            self.media_player.setSource(QUrl.fromLocalFile(media_path))
            self.media_player.play()
            self.btn_confirm.setEnabled(True)
            self.btn_confirm.setText("✅ ПІДТВЕРДИТИ ТЕКСТ ТА ПОЧАТИ ДУБЛЯЖ")

    # ПУНКТ 7: Логіка керування плеєром та перемотування
    def on_player_position_changed(self, position):
        if not self.time_slider.isSliderDown():
            self.time_slider.setValue(position)
        self.update_time_label(position, self.media_player.duration())

    def on_player_duration_changed(self, duration):
        self.time_slider.setRange(0, duration)

    def set_player_position(self, position):
        self.media_player.setPosition(position)

    def update_time_label(self, position, duration):
        pos_sec = position // 1000
        dur_sec = duration // 1000
        self.lbl_time.setText(
            f"{int(pos_sec // 60):02}:{int(pos_sec % 60):02} / "
            f"{int(dur_sec // 60):02}:{int(dur_sec % 60):02}"
        )

    @Slot(str)
    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#888;'>[{timestamp}]</span> {message}")
        self.status_label.setText(message)

    @asyncSlot()
    async def open_new_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.mkv *.avi)")
        if not path: return

        self.add_log(f"📁 Файл обрано: {path}")
        
        languages = ["English", "Ukrainian", "French", "German", "Spanish"]
        lang, ok = QInputDialog.getItem(self, "Settings", "Target Language:", languages, 0, False)
        
        if ok and lang:
            # Мапінг вибору у ISO коди
            lang_map = {"English": "en", "Ukrainian": "uk", "French": "fr", "German": "de", "Spanish": "es"}
            target_iso = lang_map.get(lang, "en")

            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.add_log("🎬 Оригінальне відео завантажено в плеєр")
            self.btn_confirm.setText("⏳ ОБРОБКА ШІ...")
            
            self.controller = LocalizationController(path)
            self.controller.project.target_lang = target_iso
            self.connect_signals()
            await self.controller.run_full_analysis()

    @asyncSlot()
    async def confirm_and_synthesize(self):
        if self.controller:
            self.add_log("🎙️ Текст підтверджено. Починаємо рендеринг дубляжу...")
            self.btn_confirm.setEnabled(False)
            self.btn_confirm.setText("⚡ РЕНДЕРИНГ...")
            try:
                await self.controller.run_synthesis() 
            except Exception as e:
                self.add_log(f"❌ Помилка синтезу: {str(e)}")
                self.btn_confirm.setEnabled(True)
    
    @Slot(list)
    def fill_transcript(self, segments):
        """ПУНКТ 1 та 2: Наповнення редактора інтерактивними картками"""
        self.transcript_list.clear()
        
        for seg in segments:
            item = QListWidgetItem(self.transcript_list)
            
            # Створюємо кастомний віджет для рядка
            card = SegmentCardWidget(seg, self.controller, self)
            item.setSizeHint(card.sizeHint())
            
            # Зв'язуємо елемент списку з віджетом
            self.transcript_list.addItem(item)
            self.transcript_list.setItemWidget(item, card)
        
        self.add_log(f"✅ Успішно завантажено {len(segments)} інтерактивних карток")
        self.btn_confirm.setEnabled(True)
        self.btn_confirm.setText("✅ ПІДТВЕРДИТИ ТЕКСТ ТА ПОЧАТИ ДУБЛЯЖ")

    @Slot()
    def upload_video_action(self):
        """Пункт 10: Логіка перевизначення шляху збереження фінального відео"""
        if not self.controller:
            self.add_log("⚠️ Спочатку завантажте відео, щоб система створила проєкт!")
            return
    
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Оберіть місце для збереження готового відео", 
            self.controller.project.project_name + "_localized.mp4",
            "Відео файли (*.mp4)"
        )
        
        if path:
            self.controller.project.output_video_path = path
            self.add_log(f"💾 Новий шлях для фінального експорту задано: {path}")

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
            #TopBar { background: #111111; border-bottom: 1px solid #1F1F1F; }
            #Logo { font-size: 16px; font-weight: 900; color: #8B7CFF; margin-right: 15px; letter-spacing: 1px; }
            #NewProjectButton { background: #8B7CFF; color: black; border-radius: 8px; padding: 6px 14px; font-weight: 600; }
            #NewProjectButton:disabled { background: #333; color: #666; }
            #Panel { background: #121212; border: 1px solid #1F1F1F; border-radius: 20px; }
            #PanelTitle { color: #555; font-size: 13px; font-weight: 800; text-transform: uppercase; }
            #LogConsole { background: #080808; border: none; font-family: 'Consolas'; font-size: 11px; color: #8B7CFF; }
            #VideoPlayer { background: #000; border-radius: 20px; }
            #WarningBadge { background: rgba(139, 124, 255, 0.1); color: #8B7CFF; border: 1px solid rgba(139, 124, 255, 0.3); border-radius: 12px; padding: 4px 12px; }
            QProgressBar { background: #1A1A1A; border-radius: 4px; height: 6px; text-align: center; color: transparent; }
            QProgressBar::chunk { background: #8B7CFF; }
            QSplitter::handle { background: transparent; }
            #UploadButton {
                background: #2A2A2A; color: #FFFFFF; border: 1px solid #444; border-radius: 8px;
                padding: 6px 14px; font-weight: 600; margin-left: 10px;
            }
            #UploadButton:hover { background: #353535; border-color: #8B7CFF; }
            QSlider::groove:horizontal { height: 4px; background: #222; border-radius: 2px; }
            QSlider::handle:horizontal { background: #8B7CFF; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = PolyGlotWindow()
    window.show()
    with loop:
        loop.run_forever()