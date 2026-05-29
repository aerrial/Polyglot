# ui/components/panels.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class Panel(QFrame):
    """Базовий контейнер робочої області додатку із закругленими кутами"""
    def __init__(self, title=""):
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        self.title = QLabel(title)
        if title:
            self.title.setObjectName("PanelTitle")
            layout.addWidget(self.title)
            
        self.body = QVBoxLayout()
        layout.addLayout(self.body)