import asyncio
import os
import edge_tts
from faster_whisper import WhisperModel
import numpy as np
from moviepy import AudioFileClip, VideoFileClip, CompositeAudioClip
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.fx import MultiplySpeed
from deep_translator import GoogleTranslator

# Конфігурація
VIDEO_FILE = "input_video.mp4"
OUTPUT_FILE = "translated_video.mp4"
TEMP_DIR = "temp_segments"

async def process_segment(i, segment, voice, temp_dir):
    segment_path = os.path.join(temp_dir, f"seg_{i}.mp3")
    orig_duration = segment.end - segment.start
    
    # 1. Розрахунок швидкості мовлення
    # Середня швидкість ~ 15 символів на секунду. Якщо тексту більше - прискорюємо.
    chars_per_sec = len(segment.text) / orig_duration
    rate = "+0%"
    if chars_per_sec > 15:
        speed_percent = min(int((chars_per_sec / 15 - 1) * 100), 40) # макс +40%
        rate = f"+{speed_percent}%"

    # 2. Генерація через edge-tts
    communicate = edge_tts.Communicate(segment.text, voice, rate=rate)
    await communicate.save(segment_path)

    # 3. Завантаження та обробка
    seg_audio = AudioFileClip(segment_path)

    # Якщо аудіо все ще довше за оригінальний сегмент — прискорюємо примусово
    if seg_audio.duration > orig_duration:
        factor = seg_audio.duration / orig_duration
        seg_audio = seg_audio.with_effects([MultiplySpeed(factor)])

    # --- ЗАХИСТ ВІД OSError (Padding) ---
    # Створюємо тишу, щоб "дотягнути" файл до потрібної довжини, якщо він коротший
    padding_duration = max(0.1, orig_duration - seg_audio.duration + 0.1)
    silence = AudioArrayClip(np.zeros((int(44100 * padding_duration), 2)), fps=44100)
    
    from moviepy.audio.AudioClip import concatenate_audioclips
    # Об'єднуємо голос з мікро-паузою в кінці
    final_seg = concatenate_audioclips([seg_audio, silence])
    
    # Обрізаємо точно під orig_duration і ставимо в потрібний час
    return final_seg.with_duration(orig_duration).with_start(segment.start)

async def generate_voice_segments(segments, temp_dir):
    voice = "en-US-GuyNeural"
    # Створюємо список задач для паралельного виконання
    tasks = [process_segment(i, s, voice, temp_dir) for i, s in enumerate(segments)]
    # Чекаємо на всі сегменти одночасно (це набагато швидше)
    return await asyncio.gather(*tasks)

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
    print("🧠 Розпізнавання мови (Whisper + VAD)...")
    model = WhisperModel("medium", device="cpu", compute_type="int8") # 'medium' краща за 'base'
    
    # vad_filter прибирає галюцинації на тихих ділянках
    segments_orig, info = model.transcribe(
        temp_original_audio, 
        vad_filter=True, 
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    translator = GoogleTranslator(source='auto', target='en')
    translated_segments = []

    print("🌍 Переклад та оптимізація тексту...")
    for s in segments_orig:
        try:
            # Переклад через deep-translator
            translation = translator.translate(s.text)

            from types import SimpleNamespace
            translated_segments.append(SimpleNamespace(start=s.start, end=s.end, text=translation))
            print(f"DEBUG: {s.text} -> {translation}")
        except Exception as e:
            print(f"⚠️ Помилка перекладу: {e}")
            translated_segments.append(s)

    # 2. Передаємо оптимізовані сегменти на озвучку
    loop = asyncio.get_event_loop()
    audio_clips = loop.run_until_complete(generate_voice_segments(translated_segments, TEMP_DIR))

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