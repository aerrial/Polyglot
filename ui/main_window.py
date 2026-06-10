# ui/main_window.py
import sys
import os
import datetime
import shutil
from qasync import QEventLoop, asyncSlot
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget,
    QMainWindow, QPushButton, QProgressBar, QSlider, QSplitter, QVBoxLayout, 
    QWidget, QFileDialog, QInputDialog, QTextEdit, QFrame, QDialog, QDialogButtonBox,
    QCheckBox, QLineEdit, QFormLayout, QComboBox, QMessageBox
)
from PySide6.QtGui import QColor, QPalette
from controllers.localization_controller import LocalizationController

# Модульні імпорти компонентів
from ui.components.panels import Panel
from ui.components.speaker_widget import SpeakerRowWidget
from ui.components.segment_card import SegmentCardWidget
from ui.components.projects_tab import ProjectsTabWidget
from ui.styles import get_dark_qss, get_light_qss

class PolyGlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyGlot AI Studio")
        self.resize(1700, 950)
        
        self.controller = None
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.sample_player = QMediaPlayer()
        self.sample_audio_output = QAudioOutput()
        self.sample_player.setAudioOutput(self.sample_audio_output)

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
        
        logo = QLabel("POLYGLOT")
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
        
        # Залишаємо тільки дві функціональні кнопки
        self.nav_buttons = {}
        for item in ["Projects", "Settings"]:
            btn = QPushButton(item)
            btn.setObjectName("NavButton")
            self.nav_buttons[item] = btn
            if item == "Projects":
                btn.clicked.connect(self.toggle_projects_tab_action)
            elif item == "Settings":
                btn.clicked.connect(self.open_settings_dialog)
            top_layout.addWidget(btn)

        top_layout.addStretch()

        self.theme_btn = QPushButton("🌙 Темна тема")  # Початковий стан
        self.theme_btn.setCheckable(True)
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_layout.addWidget(self.theme_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("WarningBadge")
        top_layout.addWidget(self.status_label)
        main_layout.addWidget(top_bar)

        # --- CONTENT AREA ---
        root_content = QWidget()
        main_layout.addWidget(root_content)
        workspace_layout = QVBoxLayout(root_content)
        workspace_layout.setContentsMargins(15, 15, 15, 15)
        
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(15)
        
        # 1. Dynamic Left Panel (Editor <-> Projects)
        self.transcript_panel = Panel("Transcript Editor")
        self.left_side_stack = QStackedWidget()
        
        self.editor_page = QWidget()
        editor_layout = QVBoxLayout(self.editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self.transcript_list = QListWidget()
        self.transcript_list.setObjectName("TranscriptList")
        editor_layout.addWidget(self.transcript_list)

        self.btn_confirm = QPushButton("ПІДТВЕРДИТИ ТЕКСТ")
        self.btn_confirm.setObjectName("NewProjectButton")
        self.btn_confirm.setFixedHeight(45)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.confirm_and_synthesize)
        editor_layout.addWidget(self.btn_confirm)
        
        self.projects_tab = ProjectsTabWidget(self)
        
        self.left_side_stack.addWidget(self.editor_page)  # Index 0
        self.left_side_stack.addWidget(self.projects_tab) # Index 1
        self.transcript_panel.body.addWidget(self.left_side_stack)

        # 2. Middle Panel (Player + Console)
        mid_container = QWidget()
        mid_layout = QVBoxLayout(mid_container)
        mid_layout.setSpacing(15)
        mid_layout.setContentsMargins(0,0,0,0)
        mid_container.setObjectName("MidContainer")

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("VideoPlayer")
        self.video_widget.setMinimumHeight(400)
        self.media_player.setVideoOutput(self.video_widget)
        mid_layout.addWidget(self.video_widget, stretch=5)
        
        player_controls = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayButton")
        self.play_btn.setFixedWidth(50)
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setObjectName("TimeSlider")
        self.time_slider.setRange(0, 0)
        self.time_slider.sliderMoved.connect(self.set_player_position)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("TimeLabel")
        
        player_controls.addWidget(self.play_btn)
        player_controls.addWidget(self.time_slider)
        player_controls.addWidget(self.lbl_time)
        mid_layout.addLayout(player_controls)

        self.media_player.positionChanged.connect(self.on_player_position_changed)
        self.media_player.durationChanged.connect(self.on_player_duration_changed)

        self.console_panel = Panel("System Logs")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("LogConsole")
        self.console_panel.body.addWidget(self.log_console)
        mid_layout.addWidget(self.console_panel, stretch=3)

        # 3. Right Panel (Speakers + Progress)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0,0,0,0)

        self.speaker_panel = Panel("Speaker Inspector")
        self.speaker_list = QListWidget()
        self.speaker_list.setObjectName("SpeakerList")
        self.speaker_panel.body.addWidget(self.speaker_list)

        self.pipeline_panel = Panel("AI Pipeline Progress")
        self.progress_widgets = {}
        for step in ["Overall", "Audio", "STT", "Translate", "Synthesis"]:
            lbl = QLabel(f"{step} Process:")
            lbl.setObjectName("ProgressLabel")
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
        workspace_layout.addWidget(self.main_splitter)

    def connect_signals(self):
        if self.controller:
            self.controller.status_changed.connect(self.add_log)
            self.controller.sync_required.connect(self.fill_transcript)
            self.controller.overall_progress.connect(self.progress_widgets["Overall"].setValue)
            self.controller.audio_progress.connect(self.progress_widgets["Audio"].setValue)
            self.controller.stt_progress.connect(self.progress_widgets["STT"].setValue)
            self.controller.translate_progress.connect(self.progress_widgets["Translate"].setValue)
            self.controller.tts_progress.connect(self.progress_widgets["Synthesis"].setValue)
            self.controller.step_completed.connect(self.on_pipeline_step_completed)
            self.add_log("✅ Канали зв'язку з ШІ-модулем налаштовано")

    def play_shared_sample(self, ref_wav, speaker_id):
        if ref_wav and os.path.exists(ref_wav):
            if self.media_player.playbackState() == QMediaPlayer.PlayingState:
                self.media_player.pause()
                self.play_btn.setText("▶")
            self.sample_player.setSource(QUrl.fromLocalFile(ref_wav))
            self.sample_player.play()
            self.add_log(f"🔊 Прослуховування еталону голосу для {speaker_id}")

    def update_speaker_inspector(self):
        self.speaker_list.clear()
        if not self.controller or not self.controller.project: return
        project = self.controller.project
        if not project.speaker_voice_map: return
            
        for speaker_id, ref_path in project.speaker_voice_map.items():
            item = QListWidgetItem(self.speaker_list)
            row_widget = SpeakerRowWidget(speaker_id, ref_path, self)
            from PySide6.QtCore import QSize
            item.setSizeHint(QSize(row_widget.sizeHint().width(), 52))
            self.speaker_list.addItem(item)
            self.speaker_list.setItemWidget(item, row_widget)
            
        self.add_log(f"👥 Інспектор спікерів оновлено. Профілів: {len(project.speaker_voice_map)}")

    def animate_left_panel_transition(self, target_index, new_title):
        from PySide6.QtCore import QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        current_widget = self.left_side_stack.currentWidget()
        target_widget = self.left_side_stack.widget(target_index)

        if current_widget == target_widget: return

        eff_current = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(eff_current)
        eff_target = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(eff_target)

        anim_out = QPropertyAnimation(eff_current, b"opacity")
        anim_out.setDuration(250)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.OutCubic)

        anim_in = QPropertyAnimation(eff_target, b"opacity")
        anim_in.setDuration(300)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.InCubic)

        anim_move = QPropertyAnimation(target_widget, b"pos")
        anim_move.setDuration(300)
        if target_index == 1:
            target_widget.move(self.left_side_stack.width(), 0)
            anim_move.setEndValue(self.left_side_stack.rect().topLeft())
        else:
            target_widget.move(-self.left_side_stack.width(), 0)
            anim_move.setEndValue(self.left_side_stack.rect().topLeft())
        anim_move.setEasingCurve(QEasingCurve.OutQuad)

        self.panel_animation_group = QParallelAnimationGroup()
        self.panel_animation_group.addAnimation(anim_out)
        self.panel_animation_group.addAnimation(anim_in)
        self.panel_animation_group.addAnimation(anim_move)

        def on_anim_finished():
            self.left_side_stack.setCurrentIndex(target_index)
            self.transcript_panel.title.setText(new_title)
            current_widget.setGraphicsEffect(None)
            target_widget.setGraphicsEffect(None)

        self.panel_animation_group.finished.connect(on_anim_finished)
        target_widget.setVisible(True)
        self.left_side_stack.setCurrentIndex(target_index)
        self.panel_animation_group.start()

    def toggle_projects_tab_action(self):
        btn = self.nav_buttons.get("Projects")
        if self.left_side_stack.currentIndex() == 0:
            self.projects_tab.scan_projects_folder()
            self.animate_left_panel_transition(1, "ПРОЄКТИ")
            self.add_log("📂 Відображення менеджера локальних проєктів у бічній панелі.")
            if btn:
                if self.theme_btn.isChecked():
                    btn.setStyleSheet("QPushButton { background: rgba(139, 124, 255, 0.15); border: 2px solid #8B7CFF; color: #6200ee; font-weight: bold; }")
                else:
                    btn.setStyleSheet("QPushButton { background: rgba(139, 124, 255, 0.2); border: 1px solid #8B7CFF; color: #FFFFFF; font-weight: bold; }")
        else:
            self.show_workspace_action()

    def show_workspace_action(self):
        self.animate_left_panel_transition(0, "Transcript Editor")
        btn = self.nav_buttons.get("Projects")
        if btn: btn.setStyleSheet("")
        self.add_log("📝 Повернення до редактора субтитрів.")

    def load_existing_project(self, json_path):
        try:
            self.add_log(f"⏳ Відновлення стану з файлу: {os.path.basename(json_path)}...")
            self.controller = LocalizationController.load_from_json(json_path)
            
            from core import settings
            settings.TARGET_LANGUAGE = self.controller.project.target_lang
            self.connect_signals()
            
            v_path = self.controller.project.video_path
            if os.path.exists(v_path):
                self.media_player.setSource(QUrl.fromLocalFile(v_path))
            
            self.fill_transcript(self.controller.project.segments)
            
            btn = self.nav_buttons.get("Projects")
            if btn: btn.setStyleSheet("")
            
            self.left_side_stack.setCurrentIndex(0)
            self.transcript_panel.title.setText("Transcript Editor")
            self.add_log(f"🎉 Проєкт '{self.controller.project.project_name}' завантажено в Workspace.")
        except Exception as e:
            self.add_log(f"❌ Помилка відкриття проєкту: {e}")

    def open_settings_dialog(self):
        from PySide6.QtWidgets import QGroupBox, QDialogButtonBox
        from core import settings
        
        dialog = QDialog(self)
        dialog.setWindowTitle("PolyGlot AI Studio — Конфігурація системи")
        dialog.setMinimumWidth(600)
        
        if self.theme_btn.isChecked():
            dialog.setStyleSheet("""
                QDialog { background-color: #f8f9fa; }
                QLabel { color: #2e2e2e; font-size: 12px; font-weight: 500; }
                QGroupBox { 
                    background-color: #ffffff; border: 1px solid #ced4da; border-radius: 8px; 
                    margin-top: 16px; padding-top: 12px; font-weight: bold; color: #2e2e2e;
                }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; margin-left: 10px; color: #6200ee; }
                QLineEdit, QComboBox { background-color: #ffffff; border: 1px solid #ced4da; border-radius: 6px; padding: 6px 10px; color: #1c1b1f; font-size: 12px; }
                QLineEdit:focus, QComboBox:focus { border-color: #8B7CFF; }
                QCheckBox { color: #2e2e2e; font-size: 12px; spacing: 8px; }
                QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #ced4da; border-radius: 4px; background: #ffffff; }
                QCheckBox::indicator:checked { background-color: #8B7CFF; border-color: #8B7CFF; }
            """)
        else:
            dialog.setStyleSheet("""
                QDialog { background-color: #0D0D0E; }
                QLabel { color: #A1A1AA; font-size: 12px; font-weight: 500; }
                QGroupBox { 
                    background-color: #151516; border: 1px solid #27272A; border-radius: 8px; 
                    margin-top: 16px; padding-top: 12px; font-weight: bold; color: #FFFFFF;
                }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; margin-left: 10px; color: #8B7CFF; }
                QLineEdit, QComboBox { background-color: #202022; border: 1px solid #27272A; border-radius: 6px; padding: 6px 10px; color: #FFFFFF; font-size: 12px; }
                QLineEdit:focus, QComboBox:focus { border-color: #8B7CFF; }
                QCheckBox { color: #E4E4E7; font-size: 12px; spacing: 8px; }
                QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3F3F46; border-radius: 4px; background: #202022; }
                QCheckBox::indicator:checked { background-color: #8B7CFF; border-color: #8B7CFF; }
            """)
        
        main_vertical_layout = QVBoxLayout(dialog)
        main_vertical_layout.setContentsMargins(20, 10, 20, 20)
        main_vertical_layout.setSpacing(10)
        
        group_translation = QGroupBox("Модуль перекладу та локалізації")
        trans_layout = QFormLayout(group_translation)
        trans_layout.setSpacing(12)
        
        cb_mode = QCheckBox("Увімкнути розумний Lipsync (Gemini 1.5 Flash LLM)")
        cb_mode.setChecked(settings.TRANSLATION_MODE_LLM)
        if self.theme_btn.isChecked():
            cb_mode.setStyleSheet("font-weight: 600; color: #1c1b1f;")
        else:
            cb_mode.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        trans_layout.addRow(cb_mode)
        
        le_key = QLineEdit(settings.GEMINI_API_KEY)
        le_key.setEchoMode(QLineEdit.Password)
        le_key.setPlaceholderText("Введіть ваш секретний API Key...")
        trans_layout.addRow("Ключ доступу Gemini API:", le_key)
        
        combo_lang = QComboBox()
        combo_lang.addItems(["uk", "en", "es", "de", "fr"])
        combo_lang.setCurrentText(settings.TARGET_LANGUAGE)
        trans_layout.addRow("Цільова мова за замовчуванням:", combo_lang)
        main_vertical_layout.addWidget(group_translation)
        
        group_stt = QGroupBox("Параметри розпізнавання (Whisper STT)")
        stt_layout = QFormLayout(group_stt)
        stt_layout.setSpacing(12)
        
        combo_whisper = QComboBox()
        combo_whisper.addItems(["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"])
        combo_whisper.setCurrentText(settings.WHISPER_MODEL_SIZE)
        stt_layout.addRow("Нейронна модель розпізнавання:", combo_whisper)
        main_vertical_layout.addWidget(group_stt)
        
        group_system = QGroupBox("Обслуговування системи")
        system_layout = QHBoxLayout(group_system)
        system_layout.setContentsMargins(15, 15, 15, 15)
        
        def get_cache_size_mb():
            total_size = 0
            for folder in [settings.CACHE_AUDIO_DIR, settings.CACHE_DEMUCS_DIR]:
                if os.path.exists(folder):
                    for dirpath, _, filenames in os.walk(folder):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.exists(fp) and not os.path.islink(fp):
                                total_size += os.path.getsize(fp)
            return total_size / (1024 * 1024)

        current_cache_size = get_cache_size_mb()
        
        lbl_cache_info = QLabel(f"Тимчасові ШІ-файли (Аудіо, Вокал, Фон).<br>Зайнято на диску: <b style='color: #8B7CFF;'>{current_cache_size:.1f} МБ</b>")
        if self.theme_btn.isChecked():
            lbl_cache_info.setStyleSheet("color: #495057; line-height: 15px;")
        else:
            lbl_cache_info.setStyleSheet("color: #A1A1AA; line-height: 15px;")
        
        btn_clear_cache = QPushButton("🗑️ Очистити кеш")
        btn_clear_cache.setFixedWidth(140)
        if self.theme_btn.isChecked():
            btn_clear_cache.setStyleSheet("""
                QPushButton { background-color: #e9ecef; border: 1px solid #ced4da; color: #212529; font-weight: 600; padding: 6px; border-radius: 6px; }
                QPushButton:hover { background-color: #dc3545; border-color: #dc3545; color: #FFFFFF; }
            """)
        else:
            btn_clear_cache.setStyleSheet("""
                QPushButton { background-color: #27272A; border: 1px solid #3F3F46; color: #F4F4F5; font-weight: 600; padding: 6px; border-radius: 6px; }
                QPushButton:hover { background-color: #7f1d1d; border-color: #ef4444; color: #FFFFFF; }
            """)
        
        def clear_cache_action():
            deleted_counts = 0
            for folder in [settings.CACHE_AUDIO_DIR, settings.CACHE_DEMUCS_DIR]:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                            deleted_counts += 1
                        except Exception:
                            pass
            QMessageBox.information(dialog, "Успіх", f"Кеш повністю очищено. Видалено {deleted_counts} об'єктів.")
            self.add_log("🧹 Користувач повністю очистив тимчасовий кеш проєкту.")
            lbl_cache_info.setText("Тимчасові ШІ-файли (Аудіо, Вокал, Фон).<br>Зайнято на диску: <b style='color: #8B7CFF;'>0.0 МБ</b>")
            
        btn_clear_cache.clicked.connect(clear_cache_action)
        system_layout.addWidget(lbl_cache_info)
        system_layout.addStretch()
        system_layout.addWidget(btn_clear_cache)
        group_system.setLayout(system_layout)
        main_vertical_layout.addWidget(group_system)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        if self.theme_btn.isChecked():
            buttons.setStyleSheet("""
                QPushButton { background-color: #e9ecef; border: 1px solid #ced4da; color: #212529; padding: 6px 20px; border-radius: 6px; min-width: 80px; }
                QPushButton:hover { background-color: #dee2e6; }
                QPushButton[text="OK"] { background-color: #8B7CFF; color: #000000; font-weight: 600; border: none; }
                QPushButton[text="OK"]:hover { background-color: #7c4dff; color: #ffffff; }
            """)
        else:
            buttons.setStyleSheet("""
                QPushButton { background-color: #202022; border: 1px solid #27272A; color: #FFFFFF; padding: 6px 20px; border-radius: 6px; min-width: 80px; }
                QPushButton:hover { background-color: #27272A; }
                QPushButton[text="OK"] { background-color: #8B7CFF; color: #000000; font-weight: 600; border: none; }
                QPushButton[text="OK"]:hover { background-color: #A396FF; }
            """)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        main_vertical_layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            settings.TRANSLATION_MODE_LLM = cb_mode.isChecked()
            settings.GEMINI_API_KEY = le_key.text().strip()
            settings.TARGET_LANGUAGE = combo_lang.currentText()
            settings.WHISPER_MODEL_SIZE = combo_whisper.currentText()
            self.add_log(f"⚙️ Налаштування збережено! Мова: {settings.TARGET_LANGUAGE} | Whisper: {settings.WHISPER_MODEL_SIZE}")

    @asyncSlot()
    async def open_new_project(self):
        self.left_side_stack.setCurrentIndex(0)
        self.transcript_panel.title.setText("Transcript Editor")
        if "Projects" in self.nav_buttons:
            self.nav_buttons["Projects"].setStyleSheet("")
            
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video (*.mp4 *.mkv *.avi)")
        if not path: return

        languages = ["English", "Ukrainian", "French", "German", "Spanish"]
        lang, ok = QInputDialog.getItem(self, "Settings", "Target Language:", languages, 0, False)
        
        if ok and lang:
            lang_map = {"English": "en", "Ukrainian": "uk", "French": "fr", "German": "de", "Spanish": "es"}
            target_iso = lang_map.get(lang, "en")
            
            from core import settings
            settings.TARGET_LANGUAGE = target_iso 

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
        self.transcript_list.clear()
        for seg in segments:
            item = QListWidgetItem(self.transcript_list)
            card = SegmentCardWidget(seg, self.controller, self)
            item.setSizeHint(card.sizeHint())
            self.transcript_list.addItem(item)
            self.transcript_list.setItemWidget(item, card)
        
        self.add_log(f"✅ Успішно завантажено {len(segments)} інтерактивних карток")
        self.btn_confirm.setEnabled(True)
        self.btn_confirm.setText("ПІДТВЕРДИТИ ТЕКСТ")
        self.update_speaker_inspector()

    @Slot()
    def upload_video_action(self):
        if not self.controller:
            self.add_log("⚠️ Спочатку завантажте відео!")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Оберіть місце для збереження", 
            self.controller.project.output_video_path or (self.controller.project.project_name + "_localized.mp4"), "Відео файли (*.mp4)"
        )
        if path:
            self.controller.project.output_video_path = path
            self.add_log(f"💾 Новий шлях експорту: {path}")

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("▶")
        else:
            self.media_player.play()
            self.play_btn.setText("⏸")

    def toggle_theme(self, checked):
        self.apply_styles()
        
        # 1. Оновлюємо стилі карток реплік у списку редактора
        for i in range(self.transcript_list.count()):
            item = self.transcript_list.item(i)
            card = self.transcript_list.itemWidget(item)
            if card and hasattr(card, 'apply_card_styles'):
                card.apply_card_styles()
                
        # 2. Оновлюємо стилі рядків в інспекторі спікерів
        for i in range(self.speaker_list.count()):
            item = self.speaker_list.item(i)
            row = self.speaker_list.itemWidget(item)
            if row and hasattr(row, 'apply_row_styles'):
                row.apply_row_styles()
                
        # 3. Оновлюємо стилі вкладки архіву проєктів та її внутрішніх карток
        if hasattr(self, 'projects_tab') and self.projects_tab:
            self.projects_tab.apply_tab_styles()
                
        if checked:
            self.theme_btn.setText("☀️ Світла тема")
            self.add_log("🎨 Активовано світлу тему")
        else:
            self.theme_btn.setText("🌙 Темна тема")
            self.add_log("🎨 Активовано темну тему")

    @Slot(str, str)
    def on_pipeline_step_completed(self, step_type, media_path):
        if step_type == "ANALYSIS_DONE":
            self.add_log("🎉 Фаза аналізу завершена. Текст готовий до валідації.")
            self.update_speaker_inspector()
        elif step_type == "SYNTHESIS_DONE":
            self.add_log(f"📺 Автоперемикання плеєра на готове дубльоване відео: {media_path}")
            self.media_player.setSource(QUrl.fromLocalFile(media_path))
            self.media_player.play()
            self.play_btn.setText("⏸")
            self.btn_confirm.setEnabled(True)
            self.btn_confirm.setText("ПІДТВЕРДИТИ ТЕКСТ")

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
        self.lbl_time.setText(f"{int(pos_sec // 60):02}:{int(pos_sec % 60):02} / {int(dur_sec // 60):02}:{int(dur_sec % 60):02}")

    @Slot(str)
    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#888;'>[{timestamp}]</span> {message}")
        self.status_label.setText(message)

    def apply_styles(self):
        if self.theme_btn.isChecked():
            # --- ПРЕМІАЛЬНА М'ЯКА СВІТЛА ТЕМА ---
            # Змушуємо QVideoWidget підкорятися стилям QSS
            self.video_widget.setAttribute(Qt.WA_StyledBackground, True)

            self.setStyleSheet("""
                QMainWindow { background: #f4f4f6; }
                QWidget { color: #1c1b1f; font-family: 'Inter', sans-serif; }
                
                QSplitter::handle { background: #e2e4e9; }
                #MidContainer { background: #f4f4f6; }
                
                #TopBar { background: #fcfcfd; border-bottom: 1px solid #e2e4e9; }
                #Logo { font-size: 16px; font-weight: 900; color: #6200ee; margin-right: 15px; letter-spacing: 1px; }
                
                QPushButton#NavButton {
                    background: #fcfcfd; border: 1px solid #ced4da; border-radius: 6px;
                    color: #495057; font-weight: 500; font-size: 12px; padding: 6px 14px; min-width: 85px;
                }
                QPushButton#NavButton:hover { background: #f4f4f6; border-color: #adb5bd; color: #212529; }
                
                #NewProjectButton { background: #6200ee; color: white; border-radius: 8px; padding: 6px 14px; font-weight: 600; }
                #NewProjectButton:disabled { background: #e2e4e9; color: #adb5bd; }
                
                #Panel { background: #fcfcfd; border: 1px solid #ced4da; border-radius: 20px; }
                #PanelTitle { color: #71717a; font-size: 13px; font-weight: 800; text-transform: uppercase; }
                
                #TranscriptList { background: #fafafa; border: none; }
                #SpeakerList { background: #fcfcfd; border: 1px solid #ced4da; border-radius: 6px; }
                
                #LogConsole { background: #fcfcfd; border: 1px solid #ced4da; font-family: 'Consolas'; font-size: 11px; color: #212529; border-radius: 8px; }
                
                /* Фікс плеєра у світлій темі */
                #VideoPlayer { background-color: #e2e4e9; border-radius: 20px; border: 1px solid #ced4da; }
                
                #WarningBadge { 
                    background: rgba(98, 0, 238, 0.05); color: #6200ee; border: 1px solid rgba(98, 0, 238, 0.15); 
                    border-radius: 6px; padding: 4px 12px; font-size: 11px; font-weight: 500;
                }
                QProgressBar { background: #e2e4e9; border-radius: 4px; height: 6px; text-align: center; color: transparent; border: 1px solid #ced4da; }
                QProgressBar::chunk { background: #6200ee; }
                QSlider::groove:horizontal { height: 4px; background: #ced4da; border-radius: 2px; }
                QSlider::handle:horizontal { background: #6200ee; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
                
                QPushButton#PlayButton { background: #fcfcfd; border: 1px solid #ced4da; border-radius: 4px; color: #212529; }
                QPushButton#PlayButton:hover { background: #f4f4f6; }
                QLabel#TimeLabel { font-family: 'Consolas'; font-size: 12px; color: #212529; }
            """)
        else:
            # --- ОРИГІНАЛЬНА ТЕМНА ТЕМА ---
            self.video_widget.setAttribute(Qt.WA_StyledBackground, True)

            self.setStyleSheet("""
                QMainWindow { background: #0A0A0A; }
                QWidget { color: #E0E0E0; font-family: 'Inter', sans-serif; }
                
                QSplitter::handle { background: #1F1F1F; }
                #MidContainer { background: #0A0A0A; }
                
                #TopBar { background: #111111; border-bottom: 1px solid #1F1F1F; }
                #Logo { font-size: 16px; font-weight: 900; color: #8B7CFF; margin-right: 15px; letter-spacing: 1px; }
                
                QPushButton#NavButton {
                    background: #18181B; border: 1px solid #27272A; border-radius: 6px;
                    color: #A1A1AA; font-weight: 500; font-size: 12px; padding: 6px 14px; min-width: 85px;
                }
                QPushButton#NavButton:hover { background: #27272A; border-color: #3F3F46; color: #FFFFFF; }
                
                #NewProjectButton { background: #8B7CFF; color: black; border-radius: 8px; padding: 6px 14px; font-weight: 600; }
                #NewProjectButton:disabled { background: #333; color: #666; }
                
                #Panel { background: #121212; border: 1px solid #1F1F1F; border-radius: 20px; }
                #PanelTitle { color: #555; font-size: 13px; font-weight: 800; text-transform: uppercase; }
                
                #TranscriptList { background: #0D0D0D; border: none; }
                #SpeakerList { background: #121212; border: 1px solid #27272A; border-radius: 6px; }
                
                #LogConsole { background: #080808; border: none; font-family: 'Consolas'; font-size: 11px; color: #8B7CFF; }
                
                /* Плеєр у темній темі лишається канонічним чорним */
                #VideoPlayer { background-color: #000000; border-radius: 20px; }
                
                /* ВІДНОВЛЕНИЙ СТИЛЬ WARNING BADGE ДЛЯ ТЕМНОЇ ТЕМИ */
                #WarningBadge { 
                    background: rgba(139, 124, 255, 0.07); color: #8B7CFF; border: 1px solid rgba(139, 124, 255, 0.25); 
                    border-radius: 6px; padding: 4px 12px; font-size: 11px; font-weight: 500;
                }
                
                QProgressBar { background: #1A1A1A; border-radius: 4px; height: 6px; text-align: center; color: transparent; }
                QProgressBar::chunk { background: #8B7CFF; }
                QSlider::groove:horizontal { height: 4px; background: #222; border-radius: 2px; }
                QSlider::handle:horizontal { background: #8B7CFF; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
                
                QPushButton#PlayButton { background: #18181B; border: 1px solid #27272A; color: #E0E0E0; }
                QLabel#TimeLabel { font-family: 'Consolas'; font-size: 12px; color: #E0E0E0; }
            """)