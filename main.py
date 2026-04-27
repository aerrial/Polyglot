# main.py
import asyncio
import config
from pipeline import run_localization_pipeline
from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication

async def main():
    print("🚀 Початок роботи системи локалізації відео...")
    # Тут можна додати логіку вибору мови через input()
    await run_localization_pipeline(config.VIDEO_FILE, target_lang="en")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    with open("ui/style.qss", "r") as f:
        app.setStyleSheet(f.read())
    window.show()
    app.exec()

    