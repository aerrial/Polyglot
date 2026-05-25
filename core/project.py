# core/project.py
import os
from dataclasses import dataclass
from typing import List, Optional
from core import settings

@dataclass
class TimelineSegment:
    id: int
    start: float
    end: float
    original_text: str = ""
    translated_text: str = ""
    speaker_id: str = "Unknown"
    gender: str = "Female"
    voice_id: str = None
    audio_path: Optional[str] = None
    status: str = "pending" 

    def is_modified(self) -> bool:
        """Повертає True, якщо сегмент був змінений користувачем"""
        return self.status == "modified"

    @property
    def duration(self) -> float:
        """Обчислення чистої тривалості репліки в секундах"""
        return self.end - self.start


class Project:
    def __init__(self, video_path: str, source_lang: str = "auto", target_lang: str = "en"):
        self.video_path = video_path
        self.project_name = os.path.basename(video_path).split('.')[0]
        
        # Мовні налаштування
        self.source_lang = source_lang 
        self.target_lang = target_lang 
        
        self.vocals_path: Optional[str] = None
        self.background_path: Optional[str] = None
        self.segments: List[TimelineSegment] = []
        self.output_video_path = settings.OUTPUT_FILE
        
        # Мапінг спікерів на голоси для зручного глобального керування в UI
        self.speaker_voice_map: dict[str, str] = {}

    def add_segment(self, segment: TimelineSegment):
        """Додавання нового сегмента до списку таймлайну"""
        self.segments.append(segment)

    def get_modified_segments(self) -> List[TimelineSegment]:
        """Фільтрація черги сегментів для алгоритму Partial Rerender"""
        return [seg for seg in self.segments if seg.status == "modified"]