# pipeline.py
import os
import sys
import asyncio
import torch
import config

# Шлях до FFmpeg
ffmpeg_path = r'C:\ffmpeg\bin'
if ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]

from moviepy import VideoFileClip
from pydub import AudioSegment

from audio.separation import separate_vocals
from ml.speech_to_text import transcribe_audio, diarize_audio
from ml.translation import translate_segments
from ml.tts import generate_voice
from ml.audio_analysis import analyze_gender

from audio.pipeline import process_segment
from audio.mixer import mix_audio_fast
from video.export import export_final

shared_data = {}
_current_event = None

def extract_segment_audio(audio_path, start_sec, end_sec, speaker_id="unknown"):
    """Вирізає фрагмент аудіо для аналізу статі спікера."""
    audio = AudioSegment.from_file(audio_path)
    start_ms, end_ms = int(start_sec * 1000), int(end_sec * 1000)
    segment = audio[start_ms:end_ms]
    
    chunk_filename = f"speaker_sample_{speaker_id}.wav"
    chunk_path = os.path.join(config.TEMP_DIR, chunk_filename)
    segment.export(chunk_path, format="wav")
    return chunk_path

async def run_localization_pipeline(video_path, output_path, target_lang_code, progress_callback=None):
    global _current_event
    _current_event = asyncio.Event()

    # 1. Екстракція та розділення
    if progress_callback: progress_callback("🎬 Extracting audio...")
    video = VideoFileClip(video_path)
    temp_audio = os.path.join(config.TEMP_DIR, "temp.mp3")
    video.audio.write_audiofile(temp_audio, logger=None)
    
    if progress_callback: progress_callback("🎧 Separating vocals...")
    bg_path, vocals_path = separate_vocals(temp_audio)

    # 2. Транскрипція та Діаризація
    if progress_callback: progress_callback("🧠 Transcribing...")
    segments = transcribe_audio(vocals_path)
    torch.cuda.empty_cache() # Звільняємо місце для Pyannote

    if progress_callback: progress_callback("👥 Identifying speakers...")
    speaker_turns = diarize_audio(vocals_path)

    # 3. Мапінг спікерів до тексту
    for seg in segments:
        best_speaker, max_overlap = "Unknown", 0
        for turn in speaker_turns:
            overlap = min(seg.end, turn["end"]) - max(seg.start, turn["start"])
            if overlap > max_overlap:
                max_overlap, best_speaker = overlap, turn["speaker"]
        seg.speaker = best_speaker

    # 4. Аналіз статі для кожного унікального спікера
    speaker_genders = {}
    unique_speakers = list(set(seg.speaker for seg in segments))
    
    if progress_callback: progress_callback("🎤 Analyzing voices...")
    for spk_id in unique_speakers:
        spk_segments = [s for s in segments if s.speaker == spk_id]
        # Беремо найдовший фрагмент для точного аналізу
        longest_seg = max(spk_segments, key=lambda s: s.end - s.start)
        
        chunk_path = extract_segment_audio(vocals_path, longest_seg.start, longest_seg.end, spk_id)
        gender = analyze_gender(chunk_path)
        speaker_genders[spk_id] = gender

    for seg in segments:
        seg.gender = speaker_genders.get(seg.speaker, "Female")

    # 4.5 РОЗПОДІЛ КОНКРЕТНИХ ГОЛОСІВ МІЖ СПІКЕРАМИ
    speaker_to_voice_map = {}
    for spk_id, gender in speaker_genders.items():
        available_voices = config.VOICE_PROFILES[target_lang_code].get(gender, config.VOICE_PROFILES[target_lang_code]["Female"])
        
        # Вибираємо голос по черзі, щоб уникнути повторів, якщо спікерів багато
        voice_index = list(speaker_genders.keys()).index(spk_id) % len(available_voices)
        speaker_to_voice_map[spk_id] = available_voices[voice_index]

    # Тепер у tts_task використовуй мапу
    async def tts_task(seg, i):
        async with sem:
            try:
                # Отримуємо голос, закріплений за цим спікером
                voice = speaker_to_voice_map.get(seg.speaker, "uk-UA-PolinaNeural")
                path = os.path.join(config.TEMP_DIR, f"seg_{i}.mp3")

                if await asyncio.wait_for(generate_voice(seg.text, path, voice), timeout=25):
                    return await process_segment(seg, path)
                return None
            except Exception as e:
                print(f"⚠️ TTS error {i}: {e}")
                return None

    # 5. Переклад та очікування UI
    if progress_callback: progress_callback("🌍 Translating...")
    translated_segments = translate_segments(segments, target_lang_code)

    if progress_callback:
        progress_callback(("WAIT_FOR_EDIT", translated_segments))

    _current_event.clear()
    await _current_event.wait()
    segments = shared_data.get("segments", translated_segments)

    # 6. Генерація голосу (Паралельно)
    if progress_callback: progress_callback("🎙️ Generating voice...")
    sem = asyncio.Semaphore(3)

    async def tts_task(seg, i):
        async with sem:
            try:
                voice = config.VOICE_PROFILES[target_lang_code].get(seg.gender, config.VOICE_PROFILES[target_lang_code]["Female"])
                path = os.path.join(config.TEMP_DIR, f"seg_{i}.mp3")
                
                if await asyncio.wait_for(generate_voice(seg.text, path, voice), timeout=25):
                    return await process_segment(seg, path)
                return None
            except Exception as e:
                print(f"⚠️ TTS error {i}: {e}")
                return None

    voice_results = await asyncio.gather(*(tts_task(seg, i) for i, seg in enumerate(segments)))
    voice_results = [v for v in voice_results if v is not None]

    # 7. Зведення та Експорт
    if progress_callback: progress_callback("🎚️ Mixing and Rendering...")
    final_audio = mix_audio_fast(bg_path, voice_results, video.duration)
    export_final(video_path, final_audio, output_path)
    video.close()

    if progress_callback: 
        progress_callback(100)
        progress_callback("✨ DONE!")