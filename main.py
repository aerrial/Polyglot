import sys
import asyncio
import os
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from ui.main_window import PolyGlotWindow  # Переконайся, що назва файлу та класу вірні

# Вимикаємо симлінки для HuggingFace, як ти і робила
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

def main():
    # 1. Створюємо стандартний додаток Qt
    app = QApplication(sys.argv)

    # 2. Створюємо спеціальний цикл подій, який поєднує Qt та Asyncio
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # 3. Ініціалізуємо твоє головне вікно
    window = PolyGlotWindow()
    window.show()

    # 4. Запускаємо систему через цей поєднаний цикл
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()