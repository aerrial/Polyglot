# ml/tts.py
import asyncio
import edge_tts
import logging
import os

logger = logging.getLogger(__name__)


async def generate_voice(text, output_path, voice):
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)

            await asyncio.wait_for(
                communicate.save(output_path),
                timeout=20
            )

            if not os.path.exists(output_path):
                raise RuntimeError("TTS output missing")

            if os.path.getsize(output_path) == 0:
                raise RuntimeError("TTS output empty")

            return True

        except Exception as e:
            logger.warning(
                f"TTS attempt {attempt + 1} failed: {e}"
            )

            await asyncio.sleep(1)

    return False