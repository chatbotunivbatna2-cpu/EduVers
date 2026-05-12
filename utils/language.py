import re

def detect_language(text):

    if not text:
        return 'en'
    
    # Search for Arabic characters in the text
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F]', text))
    if arabic_chars > 1:
        return 'ar'
        
    # Search for French accented characters and keywords
    french_markers = len(re.findall(r'[àâçéèêëîïôùûüÿœæÀÂÇÉÈÊËÎÏÔÙÛÜ]', text))
    french_words = len(re.findall(
        r'\b(je|tu|il|elle|nous|vous|ils|le|la|les|un|une|des|du|de|et|est|'
        r'en|au|avec|pour|sur|dans|par|que|qui|comment|quand|où|bonjour|merci|'
        r'inscription|frais|cours|examens|comment|puis|je)\b',
        text.lower()
    ))
    
    total_words = max(len(text.split()), 1)
    
    if (french_markers + french_words) / total_words > 0.15 or french_words >= 2:
        return 'fr'
        
    return 'en'
