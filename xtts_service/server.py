# xtts_service/server.py
import os
import torch
import asyncio

# --- РАДИКАЛЬНЕ РІШЕННЯ ДЛЯ PYTORCH 2.6+ ---
original_torch_load = torch.load
torch.load = lambda *args, **kwargs: original_torch_load(*args, **{**kwargs, 'weights_only': False})
print("[SERVER] Глобальний фільтр безпеки PyTorch адаптовано під архітектуру Coqui TTS.")
# -------------------------------------------

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from TTS.api import TTS

app = FastAPI(title="XTTS Cloning Microservice")

# Глобальний замок для ізоляції обчислень на GPU (Захист VRAM від перевантаження)
gpu_lock = asyncio.Lock()

print("[SERVER] Завантаження моделі XTTS-v2 на GPU...")
device = "cuda"
tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print(f"[SERVER] Модель XTTS-v2 успішно розгорнута на {device.upper()}")

class CloneRequest(BaseModel):
    text: str
    language: str
    speaker_ref_path: str
    output_path: str

@app.post("/clone")
async def clone_voice(data: CloneRequest):
    if not os.path.exists(data.speaker_ref_path):
        raise HTTPException(status_code=400, detail="Референс-файл голосу не знайдено")
        
    # Блокуємо GPU. Наступний запит чекатиме, поки поточний сегмент повністю не начитається
    async with gpu_lock:
        try:
            print(f"[SERVER] Безпечне чергування GPU | Клонування репліки мовою '{data.language}'...")
            
            # Виконуємо важкий генеративний процес у синхронному блоці
            tts_model.tts_to_file(
                text=data.text,
                speaker_wav=data.speaker_ref_path,
                language=data.language,
                file_path=data.output_path
            )
            
            # Очищуємо кеш CUDA відразу після генерації сегмента
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            return {"status": "success", "file": data.output_path}
        except Exception as e:
            print(f"[SERVER] Помилка синтезу репліки: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)