# audio/separation.py
import os
import torch
import torchaudio
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import convert_audio
import subprocess
import config


# кеш моделі (не перевантажує VRAM повторно)
_model = None


def get_demucs_model():
    global _model
    if _model is None:
        print("[Demucs] Loading lightweight model...")

        # lighter model than htdemucs
        _model = get_model("htdemucs")  # можна замінити на mdx_extra_q

        _model.to(config.DEVICE)

    return _model


def separate_vocals(audio_path):
    """
    Optimized Demucs separation (low VRAM mode)
    """
    print("[Demucs] Starting optimized separation...")

    # 1. Перевіряємо шлях до FFmpeg
    ffmpeg_bin = r'C:\ffmpeg\bin'
    if ffmpeg_bin not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

    # 2. Якщо на вхід прийшло відео (.mp4), витягуємо з нього аудіо в .wav
    if audio_path.lower().endswith('.mp4'):
        print("[Demucs] Input is MP4. Extracting audio track via FFmpeg...")
        temp_wav_path = os.path.splitext(audio_path)[0] + "_temp_extracted.wav"
        
        # Команда FFmpeg для швидкого копіювання звуку без перекодування відео
        cmd = [
            'ffmpeg', '-y', 
            '-i', audio_path, 
            '-vn',  # вимкнути відео
            '-acodec', 'pcm_s16le',  # стандартний стабільний wav-кодек
            '-ar', '44100',  # частота дискретизації
            '-ac', '2',  # стерео
            temp_wav_path
        ]
        
        # Запускаємо приховано, щоб консоль не блимала
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Тепер робочим файлом стає наш чистий .wav
        working_audio_path = temp_wav_path
    else:
        working_audio_path = audio_path

    # 3. Завантажуємо модель
    model = get_demucs_model()

    # 4. Тепер torchaudio спокійно прочитає файл через дефолтний soundfile!
    wav, sr = torchaudio.load(working_audio_path)

    # -------------------------
    # FORCE MONO/STEREO CLEANUP
    # -------------------------
    wav = convert_audio(
        wav,
        sr,
        model.samplerate,
        model.audio_channels
    )

    wav = wav.to(config.DEVICE)

    # -------------------------
    # INFERENCE (NO GRAD)
    # -------------------------
    with torch.no_grad():
        sources = apply_model(
            model,
            wav[None],
            device=config.DEVICE,
            progress=False,
            split=True,
            overlap=0.25
        )[0]

    # -------------------------
    # CPU OUTPUT (free VRAM instantly)
    # -------------------------
    sources = sources.cpu()

    # ВИПРАВЛЕНО: Витягуємо чистий вокал
    vocals = sources[model.sources.index("vocals")]

    # ВИПРАВЛЕНО: Збираємо інструментал (no_vocals) вручну з наявних каналів
    instrumental_parts = []
    for name in ["drums", "bass", "other"]:
        if name in model.sources:
            instrumental_parts.append(sources[model.sources.index(name)])

    if instrumental_parts:
        no_vocals = torch.sum(torch.stack(instrumental_parts), dim=0)
    else:
        # Резервний варіант: від усього міксу віднімаємо вокал
        no_vocals = torch.sum(sources, dim=0) - vocals

    base = os.path.splitext(os.path.basename(audio_path))[0]

    out_dir = config.DEMUCS_OUTPUT
    os.makedirs(out_dir, exist_ok=True)

    bg_path = os.path.join(out_dir, f"{base}_no_vocals.wav")
    vocal_path = os.path.join(out_dir, f"{base}_vocals.wav")

    torchaudio.save(bg_path, no_vocals, model.samplerate)
    torchaudio.save(vocal_path, vocals, model.samplerate)

    # -------------------------
    # 🧹 ЧИСТИМО ТИМЧАСОВИЙ ФАЙЛ
    # -------------------------
    if audio_path.lower().endswith('.mp4') and os.path.exists(working_audio_path):
        try:
            del wav  # спочатку звільняємо дескриптор файлу в пайтоні
            os.remove(working_audio_path)
        except Exception as e:
            print(f"[Demucs] Warning: could not remove temp wav: {e}")

    del sources

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    print("[Demucs] Separation done (optimized)")

    return bg_path, vocal_path