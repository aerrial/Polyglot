import os
import numpy as np
from gtts import gTTS
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
from moviepy.video.fx import MultiplySpeed
from moviepy.audio.AudioClip import AudioArrayClip
from faster_whisper import WhisperModel
import asyncio
import edge_tts

# Конфігурація
VIDEO_FILE = "input_video.mp4"
OUTPUT_FILE = "translated_video.mp4"
TEMP_DIR = "temp_segments"

async def generate_voice_segments(segments, temp_dir):
    """Асинхронна функція для генерації голосу через edge-tts"""
    audio_clips = []
    
    # Виберіть голос: en-US-GuyNeural або en-US-AriaNeural
    voice = "en-US-GuyNeural" 

    for i, segment in enumerate(segments):
        print(f"--- Обробка фрагмента {i+1}: [{segment.start:.2f}s -> {segment.end:.2f}s]")
        
        segment_path = os.path.join(temp_dir, f"seg_{i}.mp3")
        
        # Генерація через edge-tts
        communicate = edge_tts.Communicate(segment.text, voice)
        await communicate.save(segment_path)

        seg_audio = AudioFileClip(segment_path)
        
        orig_duration = segment.end - segment.start
        if orig_duration <= 0: orig_duration = 0.5 
        
        # Розраховуємо швидкість
        speed_factor = seg_audio.duration / orig_duration
        if speed_factor > 1.0:
            print(f"   ⚠️ Прискорення (edge-tts): x{speed_factor:.2f}")
            seg_audio = seg_audio.with_effects([MultiplySpeed(speed_factor)])
        
        # Додаємо мікро-тишу (0.2 сек), щоб уникнути OSError
        silence = AudioArrayClip(np.zeros((8820, 2)), fps=44100) 
        seg_audio = concatenate_audioclips([seg_audio, silence])
        
        # Фіксуємо тривалість і час початку
        seg_audio = seg_audio.with_duration(orig_duration)
        seg_audio = seg_audio.with_start(segment.start)
        
        audio_clips.append(seg_audio)
    
    return audio_clips

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
    loop = asyncio.get_event_loop()
    audio_clips = loop.run_until_complete(generate_voice_segments(segments, TEMP_DIR))

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