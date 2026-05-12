import re
import logging
from typing import List, Dict, Optional
from models.knowledge_base import KnowledgeBase
from models.university import University
from extensions import db
from utils.language import detect_language
from services.cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)

def _score_entry(entry: KnowledgeBase, query_lower: str, query_tokens: List[str], lang: str) -> float:
    content = entry.content or ''
    content_ar = entry.content_ar or ''
    title = entry.title or ''
    tags_str = ' '.join(entry.tags) if entry.tags else ''
    
    full_text = f"{title} {content} {content_ar} {tags_str}".lower()
    
    score = 0.0
    
    if query_lower in title.lower():
        score += 0.5
    
    for token in query_tokens:
        if token in title.lower():
            score += 0.2
        if token in content.lower():
            score += 0.1
        if token in content_ar.lower():
            score += 0.1
        if token in tags_str.lower():
            score += 0.15
            
    priority_norm = (entry.priority or 5) / 10.0
    score += priority_norm * 0.10
    
    return score

class KnowledgeService:

    SEARCH_THRESHOLD = 0.15
    FAC_BOOST = 0.15
    DEPT_BOOST = 0.25

    def search_knowledge(self, query: str, university_id: int,
                        faculty_id: int = None, department_id: int = None,
                        limit: int = 5) -> List[Dict]:
        if not university_id or not query:
            return []

        cache_key = f"kb:{university_id}:{faculty_id}:{department_id}:{query.lower().strip()}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        lang = detect_language(query)
        results = self._search_db(query, university_id, faculty_id, department_id, limit, lang)

        if results:
            cache_set(cache_key, results, ttl=120)
        return results

    def get_all_categories(self, university_id: int) -> List[str]:
        rows = (
            KnowledgeBase.query
            .filter_by(university_id=university_id, is_active=True)
            .with_entities(KnowledgeBase.category)
            .distinct()
            .all()
        )
        cats = [r[0] for r in rows if r[0]]
        return cats

    def get_university_context(self, university_id: int) -> str:
        university = db.session.get(University, university_id)
        if not university:
            return ''

        parts = [f'University: {university.name}']
        if university.name_ar:
            parts.append(f'Arabic name: {university.name_ar}')
        if university.city:
            parts.append(f'Location: {university.city}')
        if university.website:
            parts.append(f'Website: {university.website}')
        if university.email:
            parts.append(f'Contact: {university.email}')

        cats = self.get_all_categories(university_id)
        if cats:
            parts.append(f'Knowledge categories: {", ".join(cats[:8])}')

        context = '\n'.join(parts)
        return context

    def add_knowledge(self, university_id: int, title: str, content: str,
                    category: str = None, tags=None,
                    content_ar: str = None, source_url: str = None,
                    priority: int = 5, created_by: int = None,
                    faculty_id: int = None,
                    department_id: int = None) -> KnowledgeBase:

        entry = KnowledgeBase(
            university_id=university_id,
            faculty_id=faculty_id,
            department_id=department_id,
            title=title,
            content=content,
            content_ar=content_ar,
            category=category,
            source_url=source_url,
            priority=priority,
            created_by=created_by,
        )
        entry.tags = tags or []

        db.session.add(entry)
        db.session.commit()

        return entry

    def update_knowledge(self, entry_id: int, **kwargs) -> Optional[KnowledgeBase]:
        entry = db.session.get(KnowledgeBase, entry_id)
        if not entry:
            return None

        for key, value in kwargs.items():
            if key == 'tags':
                entry.tags = value
            elif hasattr(entry, key):
                setattr(entry, key, value)

        db.session.commit()
        return entry

    def delete_knowledge(self, entry_id: int) -> bool:
        entry = db.session.get(KnowledgeBase, entry_id)
        if not entry:
            return False

        entry.is_active = False
        db.session.commit()

        return True

    def _search_db(self, query: str, university_id: int,
                faculty_id: Optional[int], department_id: Optional[int],
                limit: int, lang: str) -> List[Dict]:
        all_entries = (
            KnowledgeBase.query
            .filter_by(university_id=university_id, is_active=True)
            .all()
        )

        if not all_entries:
            return []

        query_lower = query.lower().strip()
        query_tokens = [t for t in re.split(r'\W+', query_lower) if len(t) > 2]

        scored = []
        for entry in all_entries:
            score = _score_entry(entry, query_lower, query_tokens, lang)

            is_fac = faculty_id and entry.faculty_id == faculty_id
            is_dept = department_id and entry.department_id == department_id

            if is_dept:
                score += self.DEPT_BOOST
            elif is_fac:
                score += self.FAC_BOOST

            if score >= self.SEARCH_THRESHOLD:
                if is_dept:
                    scope = 'department'
                elif is_fac:
                    scope = 'faculty'
                else:
                    scope = 'university'
                scored.append({
                    'score': round(score, 3),
                    'title': entry.title,
                    'content': entry.content,
                    'content_ar': entry.content_ar,
                    'category': entry.category,
                    'source_url': entry.source_url,
                    'priority': entry.priority,
                    'scope': scope,
                })
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]

knowledge_service = KnowledgeService()