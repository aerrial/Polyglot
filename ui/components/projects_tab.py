# ui/components/projects_tab.py
import os
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame

class ProjectCard(QFrame):
    def __init__(self, project_name, target_lang, segments_count, video_path, full_json_path, parent_tab):
        super().__init__()
        self.json_path = full_json_path
        self.parent_tab = parent_tab
        self.init_ui(project_name, target_lang, segments_count, video_path)
        self.apply_card_styles()

    def init_ui(self, name, lang, count, path):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("ProjectCard")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        
        h_layout = QHBoxLayout()
        self.lbl_name = QLabel(f"📁 {name}")
        self.lbl_name.setObjectName("ProjectNameLabel")
        
        self.lbl_lang = QLabel(f" {lang.upper()} ")
        self.lbl_lang.setObjectName("ProjectLangLabel")
        
        h_layout.addWidget(self.lbl_name)
        h_layout.addStretch()
        h_layout.addWidget(self.lbl_lang)
        layout.addLayout(h_layout)
        
        self.lbl_count = QLabel(f"📊 Стан: {count} розпізнаних сегментів")
        self.lbl_count.setObjectName("ProjectCountLabel")
        layout.addWidget(self.lbl_count)
        
        short_path = path if len(path) < 45 else "..." + path[-42:]
        self.lbl_path = QLabel(f"🎬 {short_path}")
        self.lbl_path.setObjectName("ProjectPathLabel")
        layout.addWidget(self.lbl_path)

    def apply_card_styles(self):
        # Перевіряємо, яку тему обрано в головному вікні
        is_light = self.parent_tab.parent_window.theme_btn.isChecked() if self.parent_tab and self.parent_tab.parent_window else False

        if is_light:
            # Світла тема 
            self.setStyleSheet("""
                QFrame#ProjectCard { background-color: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 12px; }
                QFrame#ProjectCard:hover { border-color: #6200ee; background-color: #f8f9fa; }
                QLabel { background: transparent; }
            """)
            self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #1c1b1f;")
            self.lbl_lang.setStyleSheet("background-color: rgba(98, 0, 238, 0.1); color: #6200ee; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            self.lbl_count.setStyleSheet("color: #495057; font-size: 12px;")
            self.lbl_path.setStyleSheet("color: #5f6368; font-size: 11px; font-family: 'Consolas';")
        else:
            # темна тема
            self.setStyleSheet("""
                QFrame#ProjectCard { background-color: #151516; border: 1px solid #27272A; border-radius: 8px; padding: 12px; }
                QFrame#ProjectCard:hover { border-color: #8B7CFF; background-color: #1C1C1E; }
                QLabel { background: transparent; }
            """)
            self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
            self.lbl_lang.setStyleSheet("background-color: #27272A; color: #8B7CFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            self.lbl_count.setStyleSheet("color: #A1A1AA; font-size: 12px;")
            self.lbl_path.setStyleSheet("color: #71717A; font-size: 11px; font-family: 'Consolas';")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_tab.parent_window.load_existing_project(self.json_path)


class ProjectsTabWidget(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.init_ui()
        self.apply_tab_styles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        self.title = QLabel("Архів проєктів")
        self.title.setObjectName("TabTitle")
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("RefreshButton")
        self.btn_refresh.setFixedSize(28, 28)
        self.btn_refresh.clicked.connect(self.scan_projects_folder)
        
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 5, 0, 0)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

    def apply_tab_styles(self):
        is_light = self.parent_window.theme_btn.isChecked() if self.parent_window else False

        if is_light:
            self.title.setStyleSheet("font-size: 15px; font-weight: 800; color: #6200ee;")
            self.btn_refresh.setStyleSheet("""
                QPushButton { background: #ffffff; border: 1px solid #ced4da; border-radius: 4px; color: #212529; } 
                QPushButton:hover { border-color: #6200ee; background: #f8f9fa; }
            """)
        else:
            self.title.setStyleSheet("font-size: 15px; font-weight: 800; color: #8B7CFF;")
            self.btn_refresh.setStyleSheet("""
                QPushButton { background: #151516; border: 1px solid #27272A; border-radius: 4px; color: white; } 
                QPushButton:hover { border-color: #8B7CFF; }
            """)

        # Оновлюємо стилі для всіх карток, які вже згенеровані всередині контейнера
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ProjectCard):
                item.widget().apply_card_styles()

    def scan_projects_folder(self):
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        projects_dir = "projects"
        if not os.path.exists(projects_dir): return
            
        cards_added = 0
        for filename in os.listdir(projects_dir):
            if filename.endswith(".json") and filename != "settings.json":
                full_path = os.path.join(projects_dir, filename)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    card = ProjectCard(
                        project_name=data.get("project_name", "Без назви"),
                        target_lang=data.get("target_lang", "uk"),
                        segments_count=len(data.get("segments", [])),
                        video_path=data.get("video_path", ""),
                        full_json_path=full_path,
                        parent_tab=self
                    )
                    self.container_layout.insertWidget(cards_added, card)
                    cards_added += 1
                except Exception as e:
                    print(f"Помилка рендеру картки {filename}: {e}")