# video/export.py
import subprocess

def export_final(video_path: str, audio_path: str = None, output_path: str = None, **kwargs):
    """
    Direct FFmpeg mux (no MoviePy) - Fixed Audio Mapping
    """
    print("[FFMPEG Export] Muxing video + audio...")

    if audio_path is None:
        audio_path = kwargs.get("audio_segment")

    if output_path is None:
        output_path = kwargs.get("output_path", "output/final_output.mp4")

    if not audio_path:
        raise ValueError("[FFMPEG Export] Помилка: Не вказано шлях до аудіофайлу!")

    audio_path = str(audio_path)
    video_path = str(video_path)
    output_path = str(output_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,       # Індекс 0
        "-i", audio_path,       # Індекс 1
        
        # 🔥 КРИТИЧНО ВАЖЛИВИЙ МАПІНГ:
        "-map", "0:v:0",        # Брати перше відео з 0-го входу (оригінальний відеоряд)
        "-map", "1:a:0",        # Брати перше аудіо з 1-го входу (твій новий .wav мікс)
        
        "-c:v", "copy",         # Відео не перекодовуємо (миттєвий рендер)
        "-c:a", "aac",          # Новий звук кодуємо в стандартний AAC
        "-shortest",            # Обрізаємо за довжиною найкоротшого потоку
        output_path
    ]

    # Запускаємо процес зведення
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"[FFMPEG Export] Success! Final video with NEW audio: {output_path}")

    return output_path