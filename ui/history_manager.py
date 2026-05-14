import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, history_file="history.json"):
        self.history_file = history_file

    def add_entry(self, original_name, output_path, language):
        """Додає новий запис у файл історії."""
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original": original_name,
            "result": output_path,
            "language": language,
            "status": "Успішно"
        }
        
        data = self.load_history()
        data.append(entry)
        
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_history(self):
        """Завантажує історію з файлу."""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []