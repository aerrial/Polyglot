# core/project.py
import os
import json
from dataclasses import dataclass, asdict
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
    status: str = "pending"  # 'pending', 'transcribed', 'modified', 'rendered'

    def is_modified(self) -> bool:
        return self.status == "modified"

    @property
    def duration(self) -> float:
        return self.end - self.start


class Project:
    def __init__(self, video_path: str, source_lang: str = "auto", target_lang: str = "en"):
        self.video_path = os.path.abspath(video_path)
        self.project_name = os.path.splitext(os.path.basename(video_path))[0]
        
        self.source_lang = source_lang 
        self.target_lang = target_lang 
        
        self.vocals_path: Optional[str] = None
        self.background_path: Optional[str] = None
        self.segments: List[TimelineSegment] = []
        self.output_video_path = os.path.abspath(settings.OUTPUT_FILE)
        self.speaker_voice_map: dict = {}

    def add_segment(self, segment: TimelineSegment):
        self.segments.append(segment)

    def get_modified_segments(self) -> List[TimelineSegment]:
        return [seg for seg in self.segments if seg.status == "modified"]

    def save_to_json(self, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"projects/{self.project_name}_data.json"
            
        os.makedirs("projects", exist_ok=True)
        
        project_data = {
            "video_path": self.video_path,
            "project_name": self.project_name,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "vocals_path": self.vocals_path,
            "background_path": self.background_path,
            "output_video_path": self.output_video_path,
            "speaker_voice_map": self.speaker_voice_map,
            "segments": [asdict(seg) for seg in self.segments]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=4)
        
        print(f"[Project] Стан проєкту успішно збережено у {filename}")
        return filename

    @classmethod
    def load_from_json(cls, filename: str) -> 'Project':
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        project = cls(data["video_path"], data["source_lang"], data["target_lang"])
        project.project_name = data["project_name"]
        project.vocals_path = data["vocals_path"]
        project.background_path = data["background_path"]
        project.output_video_path = data["output_video_path"]
        project.speaker_voice_map = data.get("speaker_voice_map", {})
        
        project.segments.clear()
        for seg_dict in data["segments"]:
            segment = TimelineSegment(**seg_dict)
            project.add_segment(segment)
            
        print(f"[Project] Проєкт {project.project_name} успішно відновлено.")
        return project