# video/processing.py
import numpy as np
from moviepy import AudioFileClip, VideoFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.fx import MultiplySpeed
import config

async def process_voice_segment(i, segment, voice_path):
    """Адаптує довжину аудіо під оригінальний таймінг сегмента."""
    orig_duration = segment.end - segment.start
    seg_audio = AudioFileClip(voice_path)

    # Якщо переклад довше оригіналу — прискорюємо його
    if seg_audio.duration > orig_duration:
        factor = seg_audio.duration / orig_duration
        # Обмежуємо прискорення до 1.4x, щоб голос не став мультяшним
        factor = min(factor, 1.4) 
        seg_audio = seg_audio.with_effects([MultiplySpeed(factor)])

    # Додаємо мікро-паузу для стабільності MoviePy
    padding_duration = max(0.01, orig_duration - seg_audio.duration + 0.05)
    silence = AudioArrayClip(np.zeros((int(44100 * padding_duration), 2)), fps=44100)
    
    final_seg = concatenate_audioclips([seg_audio, silence])
    return final_seg.with_duration(orig_duration).with_start(segment.start)

def assemble_final_video(video_path, final_audio, output_path):
    """Накладає звук на відео та зберігає файл."""
    video = VideoFileClip(video_path)
    final_video = video.with_audio(final_audio)
    
    final_video.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac",
        fps=video.fps
    )
    video.close()