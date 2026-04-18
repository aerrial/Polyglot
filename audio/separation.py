# audio/separation.py
import subprocess
import os
import sys
import config

def separate_vocals(audio_path):
    """
    Розділяє аудіо на вокал та фон.
    Повертає шляхи до (background_path, vocals_path)
    """
    print(f"🧠 Відокремлення голосу через Demucs (модель htdemucs)...")
    
    # Додаємо шлях до FFmpeg, якщо він не в системному PATH
    ffmpeg_bin = r'C:\ffmpeg\bin' # Твій шлях
    if ffmpeg_bin not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + ffmpeg_bin

    python_exe = sys.executable 
    
    try:
        # Спроба запустити на GPU (CUDA)
        subprocess.run([
            python_exe, "-m", "demucs", 
            "-d", config.DEVICE, 
            "--two-stems", "vocals", 
            audio_path, 
            "-o", config.DEMUCS_OUTPUT
        ], check=True)
    except Exception as e:
        print(f"⚠️ CUDA помилка або мало пам'яті. Перехід на CPU... ({e})")
        subprocess.run([
            python_exe, "-m", "demucs", 
            audio_path, 
            "-o", config.DEMUCS_OUTPUT
        ], check=True)

    # Формуємо шляхи до результатів
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    model_name = "htdemucs"
    
    bg_path = os.path.join(config.DEMUCS_OUTPUT, model_name, base_name, "no_vocals.wav")
    vocal_path = os.path.join(config.DEMUCS_OUTPUT, model_name, base_name, "vocals.wav")
    
    return bg_path, vocal_path