"""
DidiGov — Translation Service (Phase 2)
Uses `deep-translator` to translate text using the language code detected by Whisper.
"""

from deep_translator import GoogleTranslator
import logging

logger = logging.getLogger("didi.translation")

# Map Whisper's full language names to ISO 639-1 codes for deep-translator
WHISPER_TO_ISO_MAP = {
    "hindi": "hi",
    "english": "en",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "bengali": "bn",
    "gujarati": "gu",
    "kannada": "kn",
    "malayalam": "ml",
    "punjabi": "pa",
    "urdu": "ur",
    "odia": "or"
}

def standardize_language_code(whisper_lang: str) -> str:
    """
    Converts Whisper's verbose language output (e.g., 'Telugu', 'hindi') 
    into a standard 2-letter ISO 639-1 code (e.g., 'te', 'hi').
    Defaults to 'auto' if unknown, letting Google Translate auto-detect.
    """
    if not whisper_lang:
        return "auto"
    
    clean_lang = whisper_lang.strip().lower()
    
    # If it's already a 2-letter code, return it
    if len(clean_lang) == 2:
        return clean_lang
        
    return WHISPER_TO_ISO_MAP.get(clean_lang, "auto")


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translates text to English from a source language detected by Whisper.
    If the source language is already 'en', returns the original text.
    """
    iso_lang = standardize_language_code(source_lang)
    
    if iso_lang == "en":
        return text

    try:
        # Check if text is empty or simply whitespace
        if not text or not text.strip():
            return text

        translator = GoogleTranslator(source=iso_lang, target="en")
        translated_text = translator.translate(text)
        logger.info(f"Translated '{iso_lang}' -> 'en': {translated_text!r}")
        return translated_text
    except Exception as e:
        logger.error(f"Translation to English failed: {e}")
        # In case of failure, return the original text so the pipeline doesn't break
        return text

def translate_to_language(text: str, target_lang: str) -> str:
    """
    Translates English text back to the user's language.
    If the target language is 'en', returns the original text.
    """
    iso_lang = standardize_language_code(target_lang)
    
    if iso_lang == "en":
        return text

    try:
        if not text or not text.strip():
            return text

        translator = GoogleTranslator(source="en", target=iso_lang)
        translated_text = translator.translate(text)
        logger.info(f"Translated 'en' -> '{iso_lang}': {translated_text!r}")
        return translated_text
    except Exception as e:
        logger.error(f"Translation to {iso_lang} failed: {e}")
        return text
