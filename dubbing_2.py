import os
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
from moviepy.video.fx import MultiplySpeed
from faster_whisper import WhisperModel
from gtts import gTTS

# Конфігурація
VIDEO_FILE = "input_video.mp4"
OUTPUT_FILE = "translated_video.mp4"
TEMP_DIR = "temp_segments"

def run_dubbing():
    # Створюємо папку для тимчасових аудіо-файлів
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    # 1. Завантаження відео
    print("🎬 Завантаження відео...")
    video = VideoFileClip(VIDEO_FILE)
    temp_original_audio = "temp_original.mp3"
    video.audio.write_audiofile(temp_original_audio)

    # 2. Розпізнавання та сегментація (Whisper)
    print("🧠 Аналіз мовлення та переклад за таймкодами...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    # task="translate" перекладає на англійську та дає таймінги сегментів
    segments, _ = model.transcribe(temp_original_audio, task="translate")

    audio_clips = []

    # 3. Генерація озвучки для кожного сегмента окремо
    print("🎙 Генерація сегментів озвучки...")
    for i, segment in enumerate(segments):
        print(f"--- Обробка фрагмента {i+1}: [{segment.start:.2f}s -> {segment.end:.2f}s]")
        
        tts = gTTS(text=segment.text, lang='en')
        segment_path = os.path.join(TEMP_DIR, f"seg_{i}.mp3")
        tts.save(segment_path)

        # Завантажуємо
        seg_audio = AudioFileClip(segment_path)
        
        orig_duration = segment.end - segment.start
        if orig_duration <= 0: orig_duration = 0.5 
        
        # 1. Змінюємо швидкість, якщо треба
        speed_factor = seg_audio.duration / orig_duration
        if speed_factor > 1.0:
            seg_audio = seg_audio.with_effects([MultiplySpeed(speed_factor)])
        
        # 2. ФІКС ПОМИЛКИ: Додаємо 0.5 сек тиші в кінець кожного кліпу як "буфер"
        # Це гарантує, що t=3.12-3.17 не вилетить, бо файл тепер триватиме 3.62
        from moviepy.audio.AudioClip import AudioArrayClip
        import numpy as np
        
        # Створюємо мікро-паузу (тишу)
        silence = AudioArrayClip(np.zeros((4410, 2)), fps=44100) # 0.1 сек тиші
        
        from moviepy import concatenate_audioclips
        # Склеюємо основний звук і тишу
        seg_audio = concatenate_audioclips([seg_audio, silence])
        
        # 3. Встановлюємо жорстку тривалість для відеоряду, 
        # але MoviePy тепер матиме запас даних у файлі
        seg_audio = seg_audio.with_duration(orig_duration)
        seg_audio = seg_audio.with_start(segment.start)
        
        audio_clips.append(seg_audio)

    # 4. Збирання фінального аудіо
    print("⚙️ Зведення звукових доріжок...")
    if not audio_clips:
        print("❌ Не знайдено мовлення для перекладу!")
        return

    final_audio = CompositeAudioClip(audio_clips)
    # Гарантуємо, що довжина аудіо дорівнює довжині відео
    final_audio = final_audio.with_duration(video.duration)

    # 5. Створення фінального відео
    final_video = video.with_audio(final_audio)

    print("💾 Рендеринг фінального файлу...")
    final_video.write_videofile(
        OUTPUT_FILE, 
        codec="libx264", 
        audio_codec="aac",
        fps=video.fps
    )

    # Очищення тимчасових файлів
    print("🧹 Очищення тимчасових файлів...")
    video.close() # Закриваємо доступ до файлів перед видаленням
    os.remove(temp_original_audio)
    for f in os.listdir(TEMP_DIR):
        os.remove(os.path.join(TEMP_DIR, f))
    os.rmdir(TEMP_DIR)

    print(f"✅ Готово! Результат: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_dubbing()