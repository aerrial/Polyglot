import os
import asyncio
import edge_tts
import numpy as np
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, TextClip, CompositeVideoClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.fx import MultiplySpeed
from faster_whisper import WhisperModel

# КОНФІГУРАЦІЯ
VIDEO_FILE = "input_video.mp4"
OUTPUT_FILE = "final_dubbed_v2.mp4"
TEMP_DIR = "temp_processing"
FONT_PATH = "C:\\Windows\\Fonts\\arialbd.ttf" # Використовуємо Arial Bold для кращої видимості

async def generate_content(original_segments, translated_segments, video_width, video_height):
    audio_clips = []
    subtitle_clips = []
    voice = "en-US-AriaNeural"

    # Розрахунок ширини області субтитрів (90% від екрана)
    sub_width = int(video_width * 0.9)

    for i, (orig, trans) in enumerate(zip(original_segments, translated_segments)):
        # 1. ГЕНЕРАЦІЯ АУДІО
        segment_path = os.path.join(TEMP_DIR, f"seg_{i}.mp3")
        communicate = edge_tts.Communicate(trans.text, voice)
        await communicate.save(segment_path)

        seg_audio = AudioFileClip(segment_path)
        orig_duration = max(0.5, trans.end - trans.start)
        
        speed_factor = seg_audio.duration / orig_duration
        if speed_factor > 1.05:
            seg_audio = seg_audio.with_effects([MultiplySpeed(speed_factor)])
        
        silence = AudioArrayClip(np.zeros((4410, 2)), fps=44100)
        seg_audio = concatenate_audioclips([seg_audio, silence])
        seg_audio = seg_audio.with_duration(orig_duration).with_start(trans.start)
        audio_clips.append(seg_audio)

        # 2. ГЕНЕРАЦІЯ СУБТИТРІВ
        # Додаємо порожній рядок між мовами для відстані
        full_sub_text = f"{orig.text.strip()}\n\n({trans.text.strip()})"
        
        try:
            txt_clip = TextClip(
                text=full_sub_text,
                font=FONT_PATH,
                font_size=26, # Трохи зменшуємо для довгих фраз
                color='white',
                bg_color='black',
                size=(sub_width, None), # Обмежуємо ширину для переносу
                method='caption',       # 'caption' автоматично переносить рядки
                text_align='center'
            ).with_start(trans.start).with_duration(orig_duration).with_position(('center', video_height - 120))
            
            subtitle_clips.append(txt_clip)
        except Exception as e:
            print(f"⚠️ Помилка субтитрів {i}: {e}")

    return audio_clips, subtitle_clips

def run_dubbing():
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

    video = VideoFileClip(VIDEO_FILE)
    w, h = video.size
    
    print("🧠 Крок 1: AI Аналіз...")
    # Додаємо initial_prompt для покращення розпізнавання української
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    common_params = {
        "initial_prompt": "Це відео українською мовою про розробку програмного забезпечення.",
        "word_timestamps": False
    }

    print("   > Розпізнавання (UA)...")
    orig_segments, _ = model.transcribe(VIDEO_FILE, language="uk", **common_params)
    orig_list = list(orig_segments)
    
    print("   > Переклад (EN)...")
    trans_segments, _ = model.transcribe(VIDEO_FILE, task="translate", **common_params)
    trans_list = list(trans_segments)

    print(f"🎙 Крок 2: Обробка {len(orig_list)} фрагментів...")
    audio_clips, subtitle_clips = asyncio.run(
        generate_content(orig_list, trans_list, w, h)
    )

    print("🎬 Крок 3: Рендеринг...")
    final_audio = CompositeAudioClip(audio_clips).with_duration(video.duration)
    
    # Використовуємо CompositeVideoClip для накладання всіх шарів
    final_video = CompositeVideoClip([video] + subtitle_clips, use_bgclip=True)
    final_video = final_video.with_audio(final_audio)

    final_video.write_videofile(
        OUTPUT_FILE, 
        codec="libx264", 
        audio_codec="aac", 
        fps=video.fps,
        threads=4 # Прискорення рендеру
    )

    # Очистка
    video.close()
    for f in os.listdir(TEMP_DIR):
        try: os.remove(os.path.join(TEMP_DIR, f))
        except: pass
    os.rmdir(TEMP_DIR)
    print(f"✅ Файл {OUTPUT_FILE} готовий!")

if __name__ == "__main__":
    run_dubbing()