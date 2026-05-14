import tempfile
from moviepy import VideoFileClip, AudioFileClip


def export_final(video_path, audio_segment, output_path):
    """
    One-pass final render (no intermediate MoviePy audio graph).
    """

    temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    audio_segment.export(temp_audio, format="mp3")

    video = VideoFileClip(video_path)
    audio = AudioFileClip(temp_audio)

    final = video.with_audio(audio)

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=tempfile.mktemp(suffix=".m4a"),
        remove_temp=True,
        logger=None
    )

    video.close()
    audio.close()