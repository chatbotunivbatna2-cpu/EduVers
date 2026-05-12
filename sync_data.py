import json
import os
import logging

from extensions import db
from models import University, Faculty, Department, KnowledgeBase

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sync_all():
    try:
        logger.info('[sync_data] Starting data sync …')

        unis_raw = _load('init_universities.json')
        uni_refs = {}
        for u in unis_raw:
            vname = u.pop('var_name')
            obj = University.query.filter_by(code=u['code']).first()
            if obj:
                for k, v in u.items():
                    if k != 'code':
                        setattr(obj, k, v)
            else:
                obj = University(**u)
                db.session.add(obj)
                db.session.flush()
            uni_refs[vname] = obj

        logger.info(f'[sync_data]  Universities: {len(uni_refs)} synced')

        facs_raw = _load('init_faculties.json')
        refs = {}

        for entry in facs_raw:
            if entry['university_var'] != 'batna2':
                continue
            uni = uni_refs.get('batna2')
            if not uni:
                continue

            fac_data = entry['faculty']
            fac = Faculty.query.filter_by(code=fac_data['code'], university_id=uni.id).first()
            if fac:
                for k, v in fac_data.items():
                    if k != 'code':
                        setattr(fac, k, v)
            else:
                fac = Faculty(**fac_data, university_id=uni.id)
                db.session.add(fac)
                db.session.flush()

            refs[fac.code] = fac

            for dept_key in ('dept1', 'dept2'):
                dept_data = entry.get(dept_key)
                if not dept_data:
                    continue
                dept = Department.query.filter_by(code=dept_data['code'], faculty_id=fac.id).first()
                if dept:
                    for k, v in dept_data.items():
                        if k != 'code':
                            setattr(dept, k, v)
                else:
                    dept = Department(**dept_data, university_id=uni.id, faculty_id=fac.id)
                    db.session.add(dept)
                    db.session.flush()
                refs[dept.code] = dept

        logger.info(f'[sync_data]  Faculties/Depts: {len(refs)} synced')

        kb_raw = _load('init_knowledge.json')
        kb_count = 0
        for entry in kb_raw:
            uni_obj = uni_refs.get(entry.get('university_var'))
            if not uni_obj:
                continue

            fac_id = None
            fac_code = entry.get('faculty_code')
            if fac_code and fac_code in refs:
                fac_id = refs[fac_code].id

            dept_id = None
            dept_code = entry.get('dept_code')
            if dept_code and dept_code in refs:
                dept_id = refs[dept_code].id
                if not fac_id and hasattr(refs[dept_code], 'faculty_id'):
                    fac_id = refs[dept_code].faculty_id

            kb = KnowledgeBase.query.filter_by(
                title=entry['title'], university_id=uni_obj.id
            ).first()

            if kb:
                kb.content     = entry['content']
                kb.content_ar  = entry.get('content_ar')
                kb.category    = entry.get('category')
                kb.tags        = entry.get('tags', [])
                kb.priority    = entry.get('priority', 5)
                kb.source_url  = entry.get('source_url')
                kb.faculty_id  = fac_id
                kb.department_id = dept_id
            else:
                kb = KnowledgeBase(
                    university_id=uni_obj.id,
                    faculty_id=fac_id,
                    department_id=dept_id,
                    title=entry['title'],
                    content=entry['content'],
                    content_ar=entry.get('content_ar'),
                    category=entry.get('category'),
                    tags=entry.get('tags', []),
                    priority=entry.get('priority', 5),
                    source_url=entry.get('source_url'),
                )
                db.session.add(kb)
            kb_count += 1

        db.session.commit()
        logger.info(f'[sync_data]  Knowledge Base: {kb_count} entries synced')
        logger.info('[sync_data] ✅ Data sync complete!')

    except Exception as e:
        db.session.rollback()
        logger.error(f'[sync_data] ❌ Data sync failed: {e}', exc_info=True)
