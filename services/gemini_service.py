import re
import time
import logging
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger(__name__)

_client = None

def _ensure_configured():
    global _client
    if _client is not None:
        return True
    
    import os
    if os.environ.get('TESTING') == 'True':
        return True

    key = (Config.GEMINI_API_KEY or '').strip()
    if not key:
        logger.warning('GEMINI_API_KEY is missing or empty')
        return False
    try:
        _client = genai.Client(api_key=key)
        return True
    except Exception as e:
        logger.error('gemini config failed: ' + str(e))
        return False

_FACTUAL_PATTERNS = re.compile(
    r'\b(how much|when|deadline|date|hours?|fees?|contact|email|phone|'
    r'address|كم|متى|موعد|ساعات|رسوم|اتصال|combien|quand|horaire|frais)\b',
    re.IGNORECASE,
)

def _pick_temperature(message):
    if _FACTUAL_PATTERNS.search(message):
        return 0.3
    return 0.7

def _build_system_prompt(university_context=None, knowledge_context=None,
                        department_context=None, faculty_context=None):
    parts = [
        "You are an intelligent academic assistant for Algerian universities. "
        "Your role is to help students, faculty, and staff with academic, administrative, and campus-related questions.\n\n"
        "RULES:\n"
        "1. LANGUAGE ADAPTATION: ALWAYS reply in the exact language the user is writing in (Arabic, English, French, or Algerian Darja). "
        "If the user explicitly asks you to speak in Algerian Darja (الدارجة الجزائرية), you MUST respond in Algerian Darja. Do not mix languages unless necessary.\n"
        "2. TRANSLATION GUARANTEE: The Knowledge Base (KB) and University Info might be in a different language than the user's message. "
        "You MUST seamlessly translate the relevant information from the KB into the language the user is writing in before presenting it.\n"
        "3. Be accurate, concise, and helpful. Provide direct answers without unnecessary filler. "
        "Use organized formatting (bullet points, numbered lists) to keep responses clear and short.\n"
        "4. When knowledge base entries are provided, prioritize them as the source of truth. "
        "Quote specific details (dates, fees, deadlines, contacts) from the knowledge base when available, translating them as needed.\n"
        "5. If you are NOT sure about specific information (dates, fees, deadlines), say so clearly "
        "and advise the student to contact the relevant administration.\n"
        "6. Format your responses clearly: use bullet points or numbered lists for steps/options. "
        "Do NOT include any confidence percentages, confidence badges, or metadata (like 'Confidence: 100%') in your text response. Start your answer directly.\n"
        "7. You represent the student's specific university, faculty, and department. "
        "Tailor your responses to their institutional context when possible.\n"
        "8. For greetings or casual messages, respond warmly and briefly, then offer to help.",
    ]
    if university_context:
        parts.append("\n--- UNIVERSITY INFO ---\n" + university_context)
    if faculty_context:
        parts.append("\n--- FACULTY INFO ---\n" + faculty_context)
    if department_context:
        parts.append("\n--- DEPARTMENT INFO ---\n" + department_context)
    if knowledge_context:
        parts.append("\n--- KNOWLEDGE BASE (use as primary source) ---\n" + knowledge_context)
    return '\n'.join(parts)

def _with_retry(fn, retries=3, base_delay=1.0):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            wait = base_delay * (2 ** attempt)
            logger.warning('attempt ' + str(attempt + 1) + '/' + str(retries)
                        + ' failed: ' + str(e) + ', retry in ' + str(round(wait, 1)) + 's')
            time.sleep(wait)
    raise last_exc

def generate_chat_response(conversation_history, university_context=None,
                            knowledge_context=None, department_context=None,
                            faculty_context=None, model=None):
    if not _ensure_configured():
        return 'Service temporarily unavailable.', None

    model_name = model or Config.GEMINI_MODEL
    system_prompt = _build_system_prompt(university_context, knowledge_context, department_context, faculty_context)

    if conversation_history:
        last_message = conversation_history[-1]['content']
    else:
        last_message = ''
    temperature = _pick_temperature(last_message)

    gemini_history = []

    for msg in conversation_history[:-1]:
        role = 'model' if msg['role'] == 'assistant' else 'user'
        gemini_history.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])])
        )

    def _call():
        chat = _client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=Config.GEMINI_MAX_TOKENS,
            ),
            history=gemini_history
        )
        resp = chat.send_message(last_message)
        text = getattr(resp, 'text', '')
        if text:
            return text
        return 'Hmm, something went wrong on my end.'

    try:
        text = _with_retry(_call)
        return text, model_name
    except Exception as e:
        logger.error('all retries failed: ' + str(e))
        return 'Something went wrong, please try again.', None


def count_tokens(text):
    if not text:
        return 0
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_chars = len(text) - arabic_chars
    return (arabic_chars // 2) + (latin_chars // 4)


_STOP = re.compile(
    r'\b(the|a|an|is|are|was|were|i|my|me|can|you|how|what|when|where|why|'
    r'please|help|want|need|about|ال|في|من|على|هل|ما|كيف|متى|أين|'
    r'le|la|les|un|une|je|tu|il|comment|quoi|est|pour)\b',
    re.IGNORECASE,
)

def generate_chat_title(first_message, max_length=50):
    """Generate a short title from the first message without using the AI"""
    cleaned = _STOP.sub('', first_message).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    words = cleaned.split()

    title = ' '.join(words[:6]).strip(' .,!?؟،')
    if not title:
        title = first_message[:max_length]

    if len(title) > max_length:
        return title[:max_length - 3] + '…'
    return title
