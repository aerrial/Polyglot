#актуально
#main.py
import sys
import asyncio
import os
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from ui.main_window import PolyGlotWindow

os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
os.environ["FFMPEG_HARDWARE_ACCELERATION"] = "none"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = PolyGlotWindow()
    window.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()