# ml/translation.py
from deep_translator import GoogleTranslator
from types import SimpleNamespace

def translate_segments(segments, target_lang='en'):
    """
    Приймає список сегментів від Whisper і повертає їх з перекладеним текстом.
    """
    translator = GoogleTranslator(source='auto', target=target_lang)
    translated_segments = []
    
    print(f"🌍 Переклад сегментів на мову: {target_lang}...")
    
    for s in segments:
        try:
            translation = translator.translate(s.text)
            # Створюємо копію сегмента з новим текстом
            translated_segments.append(SimpleNamespace(
                start=s.start, 
                end=s.end, 
                text=translation
            ))
            # Для відладки в терміналі
            print(f"   [Текст]: {s.text[:30]}... -> {translation[:30]}...")
        except Exception as e:
            print(f"⚠️ Помилка перекладу сегмента: {e}")
            translated_segments.append(s)
            
    return translated_segments