import asyncio
import os
import sys
import subprocess
import edge_tts
import numpy as np
from faster_whisper import WhisperModel
from moviepy import AudioFileClip, VideoFileClip, CompositeAudioClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.fx import MultiplySpeed
from deep_translator import GoogleTranslator
from types import SimpleNamespace

# --- КОНФІГУРАЦІЯ ---
VIDEO_FILE = "input_video.mp4"
OUTPUT_FILE = "translated_video.mp4"
TEMP_DIR = "temp_segments"
DEMUCS_OUTPUT = "demucs_output"  # Папка для розділеного звуку

async def process_segment(i, segment, voice, temp_dir):
    segment_path = os.path.join(temp_dir, f"seg_{i}.mp3")
    orig_duration = segment.end - segment.start
    
    # Розрахунок швидкості (адаптація під довжину тексту)
    chars_per_sec = len(segment.text) / orig_duration
    rate = "+0%"
    if chars_per_sec > 15:
        speed_percent = min(int((chars_per_sec / 15 - 1) * 100), 40)
        rate = f"+{speed_percent}%"

    # Генерація голосу через Edge-TTS
    communicate = edge_tts.Communicate(segment.text, voice, rate=rate)
    await communicate.save(segment_path)

    seg_audio = AudioFileClip(segment_path)

    # Якщо переклад довше оригіналу — прискорюємо аудіофайл
    if seg_audio.duration > orig_duration:
        factor = seg_audio.duration / orig_duration
        seg_audio = seg_audio.with_effects([MultiplySpeed(factor)])

    # Додаємо мікро-паузу для коректної склейки в MoviePy
    padding_duration = max(0.05, orig_duration - seg_audio.duration + 0.05)
    silence = AudioArrayClip(np.zeros((int(44100 * padding_duration), 2)), fps=44100)
    
    final_seg = concatenate_audioclips([seg_audio, silence])
    return final_seg.with_duration(orig_duration).with_start(segment.start)

async def generate_voice_segments(segments, temp_dir):
    voice = "en-US-GuyNeural"
    tasks = [process_segment(i, s, voice, temp_dir) for i, s in enumerate(segments)]
    return await asyncio.gather(*tasks)

def separate_audio(audio_path):
    """Розділяє аудіо на вокал та фон за допомогою Demucs"""
    print(f"🧠 Відокремлення голосу через Demucs...")
    
    # ПРИМУСОВО ДОДАЄМО FFmpeg В PATH (якщо ви розпакували його в C:\ffmpeg)
    ffmpeg_bin = r'C:\ffmpeg\bin' # Вкажіть ваш реальний шлях до папки bin
    if ffmpeg_bin not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + ffmpeg_bin

    python_exe = sys.executable 
    
    try:
        # Запускаємо: python -m demucs -d cuda <файл> -o <папка>
        # Якщо CUDA не налаштована або виникне помилка, Demucs сам перейде на CPU
        subprocess.run([
            python_exe, "-m", "demucs", 
            "-d", "cuda", 
            "--two-stems", "vocals",  # Робить лише два файли: вокал і все інше
            audio_path, 
            "-o", DEMUCS_OUTPUT
        ], check=True)
    except Exception as e:
        print(f"⚠️ Помилка CUDA (можливо, мало пам'яті або драйвер): {e}. Спроба на CPU...")
        subprocess.run([python_exe, "-m", "demucs", audio_path, "-o", DEMUCS_OUTPUT], check=True)

    # Визначаємо шлях до результатів
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    model_name = "htdemucs" # назва стандартної моделі Demucs
    
    # Шляхи до файлів, які створює Demucs (структура: output/model/filename/stem.wav)
    bg_path = os.path.join(DEMUCS_OUTPUT, model_name, base_name, "no_vocals.wav")
    vocal_path = os.path.join(DEMUCS_OUTPUT, model_name, base_name, "vocals.wav")
    
    return bg_path, vocal_path

def run_dubbing():
    # Створення необхідних папок
    for d in [TEMP_DIR, DEMUCS_OUTPUT]:
        if not os.path.exists(d): os.makedirs(d)

    # 1. Витягуємо оригінальне аудіо з відео
    print("🎬 Аналіз відео...")
    video = VideoFileClip(VIDEO_FILE)
    temp_orig_audio = "temp_original.mp3"
    video.audio.write_audiofile(temp_orig_audio)

    # 2. Розділяємо на Голос та Музику (Фон)
    bg_audio_path, vocals_path = separate_audio(temp_orig_audio)
    background_audio = AudioFileClip(bg_audio_path)

    # 3. Whisper розпізнає чистий вокал (це набагато точніше, ніж з музикою)
    print("🧠 Розпізнавання мови (Whisper GPU)...")
    model = WhisperModel("medium", device="cuda", compute_type="float16") 

    # ПАРАМЕТРИ ДЛЯ КРАЩОЇ ТОЧНОСТІ:
    segments_orig, info = model.transcribe(
        vocals_path, 
        language="uk",             # Примусово ставимо українську мову
        beam_size=5,               # Збільшуємо точність пошуку слів
        vad_filter=False,           # Фільтруємо тишу
        vad_parameters=dict(
            min_silence_duration_ms=1000, # Чекаємо секунду тиші, перш ніж різати сегмент
            speech_pad_ms=400             # Додаємо трохи часу до і після фрази
        ),
        word_timestamps=False      # Нам потрібні цілі речення для перекладу
    )

    # Перетворюємо генератор на список відразу, щоб бачити кількість сегментів
    segments_orig = list(segments_orig)
    print(f"📊 Знайдено сегментів: {len(segments_orig)}")

    # 4. Переклад через Deep-Translator
    translator = GoogleTranslator(source='auto', target='en')
    translated_segments = []
    print("🌍 Переклад тексту...")
    for s in segments_orig:
        try:
            translation = translator.translate(s.text)
            translated_segments.append(SimpleNamespace(start=s.start, end=s.end, text=translation))
            print(f"DEBUG: {s.text[:30]}... -> {translation[:30]}...")
        except Exception as e:
            print(f"Помилка перекладу: {e}")
            translated_segments.append(s)

    # 5. Генерація нової озвучки (Edge-TTS)
    print("🎙️ Генерація нової озвучки...")
    loop = asyncio.get_event_loop()
    new_vocals_clips = loop.run_until_complete(generate_voice_segments(translated_segments, TEMP_DIR))

    # 6. Мікшування: Оригінальний фон (тихіше) + Новий голос (гучніше)
    print("⚙️ Зведення фінальної доріжки...")
    new_vocals_composite = CompositeAudioClip(new_vocals_clips).with_duration(video.duration)
    
    # Налаштування рівнів звуку (0.3 = 30% гучності фону)
    final_audio = CompositeAudioClip([
        background_audio.with_volume_scaled(0.3), 
        new_vocals_composite.with_volume_scaled(1.2)
    ])

    # 7. Складання відео та рендеринг
    final_video = video.with_audio(final_audio)
    print("💾 Рендеринг фінального файлу...")
    final_video.write_videofile(
        OUTPUT_FILE, 
        codec="libx264", 
        audio_codec="aac",
        fps=video.fps
    )

    # 8. Закриваємо всі ресурси (критично для Windows, щоб видалити файли)
    video.close()
    background_audio.close()
    for clip in new_vocals_clips: clip.close()
    print("✅ Готово! Результат збережено у:", OUTPUT_FILE)

if __name__ == "__main__":
    run_dubbing()