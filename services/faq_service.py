import json
import os
import logging
from utils.language import detect_language

logger = logging.getLogger(__name__)

def build_placeholders(university=None):
    if university is None:
        return {
            'university_name': 'your university',
            'university_name_ar': 'جامعتك',
            'university_name_fr': 'votre université',
            'city':               '', 'city_ar': '', 'city_fr': '',
            'portal_url': 'the student portal',
            'website':            'the university website',
            'email_general': 'info@university.dz',
            'email_registrar': 'registrar@university.dz',
            'email_finance': 'finance@university.dz',
            'email_it': 'itsupport@university.dz',
            'email_student':  'studentaffairs@university.dz',
            'email_financial_aid':'financialaid@university.dz',
            'email_housing':  'housing@university.dz',
            'email_library':  'library@university.dz',
            'email_academic':  'academic@university.dz',
            'phone_main':  'the university main number',
            'address':            'the university campus',
        }

    name = university.name    or 'your university'
    name_ar = university.name_ar or 'جامعتك'
    city = university.city    or ''
    website = university.website or 'the university website'
    email = university.email   or 'info@university.dz'
    phone = university.phone   or 'the university main number'
    domain  = email.split('@')[-1] if '@' in email else 'university.dz'

    def sub(prefix): return prefix + '@' + domain

    return {
        'university_name':  name,
        'university_name_ar':  name_ar,
        'university_name_fr':  name,
        'city':                city,
        'city_ar':             city,
        'city_fr':             city,
        'portal_url':  website,
        'website':             website,
        'email_general':  email,
        'email_registrar':  sub('registrar'),
        'email_finance':  sub('finance'),
        'email_it':  sub('itsupport'),
        'email_student':   sub('studentaffairs'),
        'email_financial_aid': sub('financialaid'),
        'email_housing':   sub('housing'),
        'email_library':   sub('library'),
        'email_academic':   sub('academic'),
        'phone_main':   phone,
        'address':             university.address or 'Campus of ' + name + ', ' + city,
    }

def fill(template, ph):
    for key, val in ph.items():
        template = template.replace('{' + key + '}', val)
    return template

def load_faqs():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    faq_path = os.path.join(base_dir, 'data', 'faqs.json')
    try:
        with open(faq_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading FAQs: {e}")
        return []
class FAQMatcher:
    def __init__(self):
        self.faqs = load_faqs()

    def find_best_match(self, user_query):
        query = user_query.lower().strip()
        query_words = set(query.split())

        best_faq = None
        best_score = 0.0

        for faq in self.faqs:
            matches = 0
            for keyword in faq['keywords']:
                if keyword.lower() in query:
                    matches += 1
            
            score = matches / len(faq['keywords']) if faq['keywords'] else 0

            for variant in faq.get('variants', []):
                if variant.lower() == query:
                    score = 1.0
                    break
            
            if score > best_score:
                best_score = score
                best_faq = faq

        if best_score > 0.2:
            return {
                'faq': best_faq,
                'confidence': round(best_score, 2),
                'category': best_faq['category']
            }
        
        return None

faq_matcher = FAQMatcher()

def search_faq(query, university=None):
    lang = detect_language(query)
    match = faq_matcher.find_best_match(query)

    if match:
        faq = match['faq']
        answers = faq.get('answers', {})
        raw_answer = answers.get(lang) or answers.get('en', '')
        ph         = build_placeholders(university)
        answer = fill(raw_answer, ph)

        result = {
            'found': True,
            'answer': answer,
            'question': faq['question'],
            'confidence': match['confidence'],
            'category': match['category'],
            'language': lang,
        }
        return result

    result = {'found': False, 'language': lang, 'message': 'No FAQ match found. AI will respond.'}
    return result