# ml/tts.py
import edge_tts
import config

async def generate_voice(text, output_path, voice=config.DEFAULT_VOICE_MALE, rate="+0%"):
    """Генерує аудіофайл із тексту за допомогою Edge-TTS."""
    print(f"🎙️ Синтез мовлення (Edge-TTS): {voice}...")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path