import torch
from TTS.api import TTS
import os

class VoiceEngine:
    def __init__(self):
        # Визначаємо пристрій (cuda для твоєї RTX 3050)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Ініціалізація XTTS на {self.device} ---")
        
        # Завантаження моделі (при першому запуску завантажить ~2ГБ)
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)

    def clone_voice(self, text, speaker_wav, output_path, language="en"):
        """
        text: що говорити
        speaker_wav: шлях до файлу з твоїм голосом (15-20 сек)
        output_path: куди зберегти результат
        language: мова озвучки (en, uk, і т.д.)
        """
        print(f"--- Генерація озвучки ({language})... ---")
        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path
        )
        print(f"✅ Файл збережено: {output_path}")

# Тестовий запуск
if __name__ == "__main__":
    # Переконайся, що файл 'my_voice.wav' лежить у папці з проєктом
    engine = VoiceEngine()
    engine.clone_voice(
        text="Hello! This is my first cloned voice for my diploma project. It works locally on my computer!",
        speaker_wav="my_voice.wav", 
        output_path="cloned_output.wav",
        language="en"
    )