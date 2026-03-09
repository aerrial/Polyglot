import os
from moviepy import VideoFileClip, AudioFileClip
from faster_whisper import WhisperModel
from gtts import gTTS

# Конфігурація
VIDEO_FILE = "input_video.mp4" # Твоє відео тут
OUTPUT_FILE = "translated_video.mp4"

def run_dubbing():
    # 1. Витягуємо аудіо з відео
    print("🎬 Обробка відео...")
    video = VideoFileClip(VIDEO_FILE)
    video.audio.write_audiofile("temp_audio.mp3")

    # 2. Розпізнавання та переклад (ASR + Translation)
    print("🧠 Розпізнавання та переклад...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    # task="translate" автоматично перекладає в текст англійською
    segments, _ = model.transcribe("temp_audio.mp3", task="translate")
    
    full_text = " ".join([segment.text for segment in segments])
    print(f"Перекладений текст: {full_text}")

    # 3. Озвучка (TTS)
    print("🎙 Генерація нового голосу...")
    tts = gTTS(text=full_text, lang='en')
    tts.save("translated_audio.mp3")

    # 4. Накладання нового аудіо на відео
    print("⚙️ Збирання фінального файлу...")
    new_audio = AudioFileClip("translated_audio.mp3")
    final_video = video.with_audio(new_audio) # замінюємо доріжку
    final_video.write_videofile(OUTPUT_FILE, codec="libx264", audio_codec="aac")

    print(f"✅ Готово! Результат у файлі: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_dubbing()