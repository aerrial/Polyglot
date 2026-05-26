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
        """Завантажує моделі у VRAM лише за потреби (Lazy Loading)"""
        if not self.whisper_model:
            self.whisper_model = get_whisper_model()
        if not self.diarization_pipeline:
            self.diarization_pipeline = get_diarization_pipeline()

    async def process(self, audio_path, source_lang="uk", progress_callback=None):
        """
        Виконує повний цикл аналізу голосу.
        Повертає список готових об'єктів TimelineSegment та словник референсів спікерів.
        """
        self.load_models()

        # 1. Діаризація (Pyannote) - робимо першою, щоб знати таймінги спікерів
        waveform, sample_rate = torchaudio.load(audio_path)
        diarization = self.diarization_pipeline({"waveform": waveform, "sample_rate": sample_rate})

        # 2. Транскрипція (Whisper) з відстеженням прогресу для Пункту 8
        def whisper_progress_hook(progress_info):
            if progress_callback:
                # progress_info - це об'єкт з атрибутами або словник, залежно від версії faster-whisper
                # Зазвичай це іменований кортеж (duration, processed_duration, ...)
                try:
                    percent = int((progress_info.completed_segments_duration / progress_info.total_duration) * 100)
                    progress_callback(percent)
                except AttributeError:
                    pass

        segments, info = self.whisper_model.transcribe(
            audio_path, 
            language=source_lang if source_lang != "auto" else None, 
            beam_size=5,
            vad_filter=True
            # Додаємо хук прогресу, якщо твоя версія faster-whisper його підтримує через лінійний генератор
        )
        
        # Перетворюємо генератор в список. Якщо хук не підтримується всередині моделі, 
        # прогрес можна рахувати ітеративно по сегментах:
        segments_list = []
        for seg in segments:
            segments_list.append(seg)
            if progress_callback and info.duration > 0:
                percent = int((seg.end / info.duration) * 100)
                progress_callback(min(percent, 100)) # Шлемо сигнал у прогрес-бар STT

        # 3. Мапінг та створення TimelineSegment
        timeline_segments = []
        speaker_samples = {} # Словник для збереження шматочків голосу {speaker_id: path_to_wav}
        
        # Створюємо папку для голосових референсів клонування (Пункт 3)
        cache_dir = os.path.join("projects", "speaker_samples")
        os.makedirs(cache_dir, exist_ok=True)
        
        for i, seg in enumerate(segments_list):
            best_speaker = "Unknown"
            max_overlap = 0
            best_turn = None
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap = min(seg.end, turn.end) - max(seg.start, turn.start)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker
                    best_turn = turn

            # Пункт 3: Якщо ми знайшли чіткий інтервал спікера і у нас ще немає референсу його голосу
            if best_speaker != "Unknown" and best_speaker not in speaker_samples and max_overlap > 1.5:
                # Вирізаємо чистий шматочок аудіо (від 1.5 до 4 секунд ідеально для клонування)
                start_frame = int(best_turn.start * sample_rate)
                end_frame = int(min(best_turn.end, best_turn.start + 4.0) * sample_rate)
                
                speaker_wave = waveform[:, start_frame:end_frame]
                sample_path = os.path.join(cache_dir, f"{best_speaker}_ref.wav")
                
                torchaudio.save(sample_path, speaker_wave, sample_rate)
                speaker_samples[best_speaker] = sample_path

            new_seg = TimelineSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                original_text=seg.text.strip(),
                speaker_id=best_speaker,
                status="transcribed"
            )
            timeline_segments.append(new_seg)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Повертаємо і сегменти, і карту вирізаних зразків голосу
        return timeline_segments, speaker_samples