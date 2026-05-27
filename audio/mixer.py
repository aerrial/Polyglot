# audio/mixer.py
import os
import subprocess
from typing import List
from core.project import TimelineSegment


def mix_audio_fast(background_path: str, segments: List[TimelineSegment], video_duration: float, output_path: str) -> str:
    """
    [WINDOWS SAFE & LOUD] Високопродуктивне зведення аудіо через FFmpeg з нормалізацією 
    гучності за стандартом EBU R128 (loudnorm). Повністю захищено від багів шляхів Windows.
    """
    print("[FFMPEG Mixer] Початок побудови фільтр-графа з очищенням шляхів Windows...")

    inputs = []
    filter_parts = []
    
    # Готуємо вихідний шлях для FFmpeg, замінюючи зворотні слеші на прямі
    output_path_clean = os.path.abspath(output_path).replace('\\', '/')

    # -------------------------
    # 1. Додаємо оригінальний фоновий супровід
    # -------------------------
    has_bg = background_path and os.path.exists(background_path)
    if has_bg:
        bg_path_clean = os.path.abspath(background_path).replace('\\', '/')
        inputs += ["-i", bg_path_clean]
        filter_parts.append(f"[0:a]volume=1.0[bg_scaled]")
        voice_start_input_idx = 1
    else:
        voice_start_input_idx = 0

    # -------------------------
    # 2. Додаємо звукові файли реплік
    # -------------------------
    active_voice_labels = []
    added_voice_count = 0

    for seg in segments:
        if not seg.audio_path or not os.path.exists(seg.audio_path):
            continue  

        # Критично важливо: чистимо шлях кожного ШІ-сегмента для фільтра
        seg_path_clean = os.path.abspath(seg.audio_path).replace('\\', '/')
        inputs += ["-i", seg_path_clean]
        
        actual_ffmpeg_input_idx = voice_start_input_idx + added_voice_count
        delay_ms = int(seg.start * 1000)
        
        raw_label = f"[delayed_v_{added_voice_count}]"
        boosted_label = f"[boosted_v_{added_voice_count}]"
        
        # 1. Робимо затримку репліки по таймлайну
        filter_parts.append(f"[{actual_ffmpeg_input_idx:d}:a]adelay={delay_ms:d}|{delay_ms:d}{raw_label}")
        # 2. Даємо індивідуальний буст кожній репліці перед змішуванням
        filter_parts.append(f"{raw_label}volume=2.5{boosted_label}")
        
        active_voice_labels.append(boosted_label)
        added_voice_count += 1

    # -------------------------
    # 3. Фінальне мікшування та ТВ-нормалізація (loudnorm)
    # -------------------------
    if added_voice_count == 0:
        print("[FFMPEG Mixer] Активних ШІ-реплік для зведення не виявлено.")
        return background_path if has_bg else ""

    mix_inputs_string = ""
    if has_bg:
        mix_inputs_string += "[bg_scaled]"
    
    mix_inputs_string += "".join(active_voice_labels)
    total_amix_inputs = added_voice_count + (1 if has_bg else 0)

    # Використовуємо фільтр loudnorm з інтегрованою гучністю -14 LUFS (стандарт YouTube / Spotify)
    # i=-14: цільова гучність
    # tp=-1.5: піковий лімітер, щоб звук не хрипів
    # LOUDNORM автоматично витягне загальний тихий потік до повноцінного гучного звуку
    filter_parts.append(
        f"{mix_inputs_string}amix=inputs={total_amix_inputs:d}:duration=first:dropout_transition=0:normalize=0,"
        f"loudnorm=i=-14:tp=-1.5:measured_i=-30[aout]"
    )

    filter_complex_string = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex_string,
        "-map", "[aout]",
        "-c:a", "pcm_s16le",  
        "-ar", "44100",
        "-ac", "2",
        output_path_clean
    ]

    print(f"[FFMPEG Mixer] Запуск виправленої команди нормалізації...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[FFMPEG Mixer] Зведення завершено! Файл збережено: {output_path_clean}")

    return output_path_clean