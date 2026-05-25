# services/stt_service.py
import torch
import torchaudio
from ml.speech_to_text import get_whisper_model, get_diarization_pipeline
from core.project import TimelineSegment

class STTService:
    def __init__(self):
        self.whisper_model = None
        self.diarization_pipeline = None

    def load_models(self):
        """Завантажує моделі у VRAM лише за потреби (Lazy Loading)"""
        if not self.whisper_model:
            self.whisper_model = get_whisper_model()
        if not self.diarization_pipeline:
            self.diarization_pipeline = get_diarization_pipeline()

    async def process(self, audio_path, source_lang="uk"):
        """
        Виконує повний цикл аналізу голосу.
        Повертає список готових об'єктів TimelineSegment.
        """
        self.load_models()

        # 1. Транскрипція (Whisper)
        # Використовуємо source_lang для точного розпізнавання
        segments, info = self.whisper_model.transcribe(
            audio_path, 
            language=source_lang if source_lang != "auto" else None, 
            beam_size=5,
            vad_filter=True
        )
        segments = list(segments)

        # 2. Діаризація (Pyannote)
        # Використовуємо твій стабільний фікс із waveform
        waveform, sample_rate = torchaudio.load(audio_path)
        diarization = self.diarization_pipeline({"waveform": waveform, "sample_rate": sample_rate})

        # 3. Мапінг та створення TimelineSegment
        timeline_segments = []
        
        for i, seg in enumerate(segments):
            # Знаходимо спікера через overlap
            best_speaker = "Unknown"
            max_overlap = 0
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap = min(seg.end, turn.end) - max(seg.start, turn.start)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker

            # Створюємо наш професійний об'єкт сегмента
            new_seg = TimelineSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                original_text=seg.text.strip(),
                speaker_id=best_speaker,
                status="transcribed"
            )
            timeline_segments.append(new_seg)

        # Звільняємо кеш після важких обчислень
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return timeline_segments