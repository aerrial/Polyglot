import numpy as np
import os
import tempfile
import librosa
import soundfile as sf

from moviepy import AudioFileClip, VideoFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip


# -----------------------------
# AUDIO STRETCH (safe version)
# -----------------------------
def stretch_audio_without_pitch_shift(input_path, target_duration, output_path):
    """
    Time-stretch audio without pitch shift (phase vocoder via librosa).
    """

    if target_duration <= 0:
        raise ValueError("target_duration must be > 0")

    y, sr = librosa.load(input_path, sr=None)

    if len(y) == 0:
        raise ValueError(f"Empty audio file: {input_path}")

    current_duration = librosa.get_duration(y=y, sr=sr)

    if current_duration <= 0:
        raise ValueError("Invalid audio duration")

    # ratio
    rate = current_duration / target_duration

    # clamp to avoid artifacts
    rate = min(max(rate, 0.5), 1.4)

    # time stretch
    y_stretched = librosa.effects.time_stretch(y, rate=rate)

    # normalize dtype safety
    y_stretched = np.asarray(y_stretched, dtype=np.float32)

    sf.write(output_path, y_stretched, sr)

    return output_path


# -----------------------------
# PROCESS SINGLE SEGMENT
# -----------------------------
async def process_voice_segment(i, segment, voice_path):
    """
    Aligns TTS voice to original segment timing.
    """

    orig_duration = float(segment.end - segment.start)

    if orig_duration <= 0:
        raise ValueError(f"Invalid segment duration: {orig_duration}")

    # fallback silence
    if not voice_path or not os.path.exists(voice_path) or os.path.getsize(voice_path) == 0:
        print(f"⚠️ Missing TTS file: {voice_path}")

        silence = AudioArrayClip(
            np.zeros((int(44100 * orig_duration), 2), dtype=np.float32),
            fps=44100
        ).with_start(segment.start)

        return silence.with_duration(orig_duration)

    # temp safe file (prevents collisions)
    with tempfile.NamedTemporaryFile(suffix="_stretched.wav", delete=False) as tmp:
        processed_voice_path = tmp.name

    try:
        stretch_audio_without_pitch_shift(
            voice_path,
            orig_duration,
            processed_voice_path
        )

        seg_audio = AudioFileClip(processed_voice_path)

        # pad if needed
        if seg_audio.duration < orig_duration:
            pad = orig_duration - seg_audio.duration

            silence = AudioArrayClip(
                np.zeros((int(44100 * pad), 2), dtype=np.float32),
                fps=44100
            )

            final_seg = concatenate_audioclips([seg_audio, silence])
        else:
            final_seg = seg_audio

        return final_seg.with_start(segment.start).with_duration(orig_duration)

    finally:
        # cleanup temp file
        try:
            if os.path.exists(processed_voice_path):
                os.remove(processed_voice_path)
        except Exception:
            pass


# -----------------------------
# ASSEMBLE FINAL VIDEO
# -----------------------------
def assemble_final_video(video_path, final_audio, output_path):
    """
    Mux final audio with video safely.
    """

    video = VideoFileClip(video_path)

    try:
        final_video = video.with_audio(final_audio)

        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=video.fps,
            temp_audiofile=os.path.join(tempfile.gettempdir(), "temp_audio.m4a"),
            remove_temp=True,
            logger=None
        )

        return output_path

    finally:
        # IMPORTANT: prevent ffmpeg leaks
        try:
            video.close()
        except Exception:
            pass

        try:
            final_video.close()
        except Exception:
            pass