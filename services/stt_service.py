# services/stt_service.py
import os
import torch
import torchaudio
from ml.speech_to_text import get_whisper_model, get_diarization_pipeline
from core.project import TimelineSegment


class STTService:
    def __init__(self):
        self.whisper_model = None
        self.diarization_pipeline = None

    def load_models(self):
        """Lazy load з мінімальним VRAM usage"""
        if not self.whisper_model:
            self.whisper_model = get_whisper_model()

        if not self.diarization_pipeline:
            self.diarization_pipeline = get_diarization_pipeline()

            try:
                self.diarization_pipeline.to(torch.device("cpu"))
                print("[STT] Diarization moved to CPU to save VRAM")
            except Exception:
                pass

    async def process(self, audio_path, source_lang="uk", progress_callback=None):
        self.load_models()

        if progress_callback:
            progress_callback(5)  # Емулюємо старт

        # ---------------------------
        # 1. LOAD AUDIO 
        # ---------------------------
        waveform, sample_rate = torchaudio.load(audio_path)

        # ---------------------------
        # 2. DIARIZATION 
        # ---------------------------
        if progress_callback:
            progress_callback(15)
            
        with torch.no_grad():
            diarization = self.diarization_pipeline(
                {"waveform": waveform, "sample_rate": sample_rate}
            )

        if progress_callback:
            progress_callback(35)

        # ---------------------------
        # 3. WHISPER TRANSCRIPTION 
        # ---------------------------
        segments, info = self.whisper_model.transcribe(
            audio_path,
            language=source_lang if source_lang != "auto" else None,
            
            # Параметри для покращення якості:
            beam_size=2,            
            best_of=3,              # Генерує кілька кандидатів і обирає топ
            vad_filter=True,        # Вирізає фоновий шум і тишу, щоб Whisper не галюцинував
            
            # Налаштування проти зациклення звуку 
            temperature=0.0,        # 0.0 робить генерацію тексту суворою та стабільною
            compression_ratio_threshold=2.4, 
            no_speech_threshold=0.6
        )

        segments_list = []
        for seg in segments:
            segments_list.append(seg)
            if progress_callback and info.duration > 0:
                percent = 35 + int((seg.end / info.duration) * 55)
                progress_callback(min(percent, 90))

        # ---------------------------
        # 4. MATCH SPEAKERS & EXTRACT VOICE SAMPLES
        # ---------------------------
        timeline_segments = []
        speaker_samples = {}

        cache_dir = os.path.abspath(os.path.join("projects", "speaker_samples"))
        os.makedirs(cache_dir, exist_ok=True)

        for i, seg in enumerate(segments_list):
            best_speaker = "Unknown"
            max_overlap = 0

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap = min(seg.end, turn.end) - max(seg.start, turn.start)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker

            new_seg = TimelineSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                original_text=seg.text.strip(),
                speaker_id=best_speaker,
                status="transcribed"
            )
            timeline_segments.append(new_seg)

            if best_speaker != "Unknown" and best_speaker not in speaker_samples:
                start_sample = int(seg.start * sample_rate)
                end_sample = int(seg.end * sample_rate)
                
                # Вирізаємо аудіо-шматок
                speaker_wav_tensor = waveform[:, start_sample:end_sample]
                
                # Тільки якщо репліка довша за 1.5 секунди (щоб еталон голосу був якісним)
                if (seg.end - seg.start) > 1.5:
                    sample_file_key = best_speaker.lower().replace(" ", "_")
                    sample_path = os.path.join(cache_dir, f"{sample_file_key}.wav")
                    
                    # Зберігаємо нарізаний шматочок на диск
                    torchaudio.save(sample_path, speaker_wav_tensor, sample_rate)
                    speaker_samples[best_speaker] = sample_path

        # Якщо для якогось спікера всі репліки були надто короткими, робимо фолбек на першу ліпшу
        for seg in timeline_segments:
            if seg.speaker_id != "Unknown" and seg.speaker_id not in speaker_samples:
                speaker_samples[seg.speaker_id] = audio_path  # Фолбек на повний вокал

        del waveform
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        if progress_callback:
            progress_callback(100)

        print(f"[STT] Успішно виділено спікерів: {list(speaker_samples.keys())}")
        return timeline_segments, speaker_samples