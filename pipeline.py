# pipeline.py
import asyncio
import os
import config
from audio.separation import separate_vocals
from ml.speech_to_text import transcribe_audio
from ml.translation import translate_segments
from ml.tts import generate_voice
from audio.mixing import mix_audio
from video.processing import process_voice_segment, assemble_final_video
from moviepy import VideoFileClip

async def run_localization_pipeline(video_path, target_lang="en"):
    # 1. Підготовка аудіо
    video = VideoFileClip(video_path)
    temp_audio = "temp_orig.mp3"
    video.audio.write_audiofile(temp_audio)
    
    bg_path, vocals_path = separate_vocals(temp_audio)
    
    # 2. Аналіз та переклад
    segments = transcribe_audio(vocals_path)
    translated = translate_segments(segments, target_lang)
    
    # 3. Синтез голосу
    voice_clips = []
    for i, seg in enumerate(translated):
        seg_path = os.path.join(config.TEMP_DIR, f"seg_{i}.mp3")
        await generate_voice(seg.text, seg_path)
        
        # Обробити сегмент (прискорення, таймінг)
        processed_clip = await process_voice_segment(i, seg, seg_path)
        voice_clips.append(processed_clip)
    
    # 4. Зведення та фінал
    final_audio = mix_audio(bg_path, voice_clips, video.duration)
    assemble_final_video(video_path, final_audio, config.OUTPUT_FILE)
    
    print("✨ ЛОКАЛІЗАЦІЯ ЗАВЕРШЕНА УСПІШНО!")