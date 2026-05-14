# ml/audio_analysis.py
import parselmouth
import numpy as np


def analyze_gender(audio_path):
    sound = parselmouth.Sound(audio_path)
    pitch = sound.to_pitch()

    pitch_values = pitch.selected_array['frequency']
    pitch_values = pitch_values[pitch_values > 0]

    if len(pitch_values) == 0:
        return None

    avg_f0 = np.mean(pitch_values)

    return "Male" if avg_f0 < 150 else "Female"