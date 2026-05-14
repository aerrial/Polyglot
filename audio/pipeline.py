import os
import tempfile
import numpy as np
from pydub import AudioSegment

from .effects import stretch_audio_ffmpeg

SAMPLE_RATE = 44100


async def process_segment(segment, tts_path):
    """
    Fast segment processing:
    - no MoviePy
    - no librosa
    - no heavy objects
    """

    duration = segment.end - segment.start

    if not os.path.exists(tts_path):
        silence = AudioSegment.silent(duration=int(duration * 1000))
        return silence, segment.start

    # temp file for stretched audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        stretched_path = tmp.name

    try:
        stretch_audio_ffmpeg(
            tts_path,
            duration,
            stretched_path
        )

        audio = AudioSegment.from_wav(stretched_path)

        # align
        audio = audio.set_frame_rate(SAMPLE_RATE)
        audio = audio.set_channels(2)

        return audio, segment.start

    finally:
        try:
            os.remove(stretched_path)
        except:
            pass