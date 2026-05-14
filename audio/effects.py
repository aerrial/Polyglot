import subprocess
import tempfile
import os


def stretch_audio_ffmpeg(input_path, target_duration, output_path):
    """
    Fast time-stretch using FFmpeg atempo (C-level, very fast).
    """

    # get durations
    import wave

    def get_duration(path):
        import librosa
        y, sr = librosa.load(path, sr=None)
        return len(y) / sr

    current_duration = get_duration(input_path)

    if current_duration <= 0 or target_duration <= 0:
        raise ValueError("Invalid durations")

    speed = current_duration / target_duration

    # clamp to ffmpeg limits (0.5 - 2.0 per filter)
    speed = max(0.5, min(speed, 2.0))

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-filter:a", f"atempo={speed}",
        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return output_path