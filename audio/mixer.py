from pydub import AudioSegment


def mix_audio_fast(background_path, voice_segments, video_duration):
    """
    Ultra-fast mixer using pydub instead of MoviePy.
    """

    background = AudioSegment.from_file(background_path)
    background = background - 12  # lower volume

    final = AudioSegment.silent(duration=int(video_duration * 1000))

    # overlay voice segments
    for audio, start_time in voice_segments:
        final = final.overlay(audio, position=int(start_time * 1000))

    # mix background + voice
    final = background.overlay(final)

    return final