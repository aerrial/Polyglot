def get_light_qss():
    return """
    /* Головне вікно та діалоги */
    QMainWindow, QDialog {
        background-color: #f8f9fa;
        color: #1c1b1f;
    }
    
    /* Картки сегментів */
    QWidget#SegmentCardWidget {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    
    /* Текстові поля (Оригінал / Переклад) */
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #bdbdbd;
        border-radius: 4px;
        color: #1c1b1f;
    }
    QTextEdit:focus {
        border: 2px solid #6200ee; /* Фіолетовий фокус */
    }
    
    /* Кнопки з фіолетовим акцентом */
    QPushButton {
        background-color: #6200ee;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #7c4dff; /* Світліший фіолетовий при наведенні */
    }
    QPushButton:pressed {
        background-color: #3700b3; /* Темніший фіолетовий при натисканні */
    }
    
    /* Списки, що випадають (QComboBox) */
    QComboBox {
        background-color: #ffffff;
        border: 1px solid #bdbdbd;
        border-radius: 4px;
        padding: 4px;
        color: #1c1b1f;
    }
    
    /* Текстове поле логів */
    QTextBrowser#log_output {
        background-color: #f1f3f4;
        color: #202124;
        border: 1px solid #e0e0e0;
    }
    """

def get_dark_qss():
    # Твоя поточна темна тема (приблизний варіант для повернення назад)
    return """
    QMainWindow, QDialog { background-color: #121212; color: #ffffff; }
    QWidget#SegmentCardWidget { background-color: #1e1e1e; border: 1px solid #333333; }
    QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #444444; }
    QTextEdit:focus { border: 2px solid #bb86fc; }
    QPushButton { background-color: #bb86fc; color: #000000; font-weight: bold; }
    QPushButton:hover { background-color: #d7aeec; }
    QTextBrowser#log_output { background-color: #1e1e1e; color: #00ff00; }
    """