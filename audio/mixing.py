# audio/mixing.py
from moviepy import AudioFileClip, CompositeAudioClip
import config

def mix_audio(background_path, new_vocals_clips, video_duration):
    """Змішує фонову музику та нові сегменти озвучки."""
    print("⚙️ Мікшування фінальної доріжки...")
    
    bg_audio = AudioFileClip(background_path).with_volume_scaled(0.3)
    
    # Створюємо композицію з усіх нових сегментів
    new_vocals_composite = CompositeAudioClip(new_vocals_clips).with_duration(video_duration)
    
    # Накладаємо новий голос (трохи гучніше) на притишений фон
    final_audio = CompositeAudioClip([
        bg_audio, 
        new_vocals_composite.with_volume_scaled(1.2)
    ])
    
    return final_audio