# ml/translation.py
from deep_translator import GoogleTranslator
from models.segment import Segment


def translate_segments(segments, target_lang='en'):
    translator = GoogleTranslator(source='auto', target=target_lang)

    texts = [s.text for s in segments]
    translated_texts = translator.translate_batch(texts)

    result = []

    for original, translated_text in zip(segments, translated_texts):
        result.append(
            Segment(
                start=original.start,
                end=original.end,
                text=translated_text,
                gender=getattr(original, "gender", "unknown")
            )
        )

    return result