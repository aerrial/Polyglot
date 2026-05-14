from moviepy import AudioFileClip, CompositeAudioClip


def mix_audio(background_path, new_vocals_clips, video_duration):
    bg_audio = AudioFileClip(background_path)

    try:
        bg_audio = bg_audio.with_volume_scaled(0.3)

        vocals = CompositeAudioClip(new_vocals_clips)
        vocals = vocals.with_duration(video_duration)

        final_audio = CompositeAudioClip([
            bg_audio,
            vocals.with_volume_scaled(1.2)
        ])

        return final_audio

    except Exception:
        bg_audio.close()
        raise