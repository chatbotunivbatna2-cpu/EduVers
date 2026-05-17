import json
import os
import logging

from extensions import db
from models import University, Faculty, Department, KnowledgeBase
from models.user import User

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

        # Ensure admin accounts exist
        _ensure_admin_accounts(uni_refs, refs)

        logger.info('[sync_data] Data sync complete!')

    except Exception as e:
        db.session.rollback()
        logger.error(f'[sync_data] Data sync failed: {e}', exc_info=True)


def _ensure_admin_accounts(uni_refs, refs):
    """Create default admin accounts if they don't exist."""
    created = 0

    # Super Admin
    if not User.query.filter_by(email='superadmin@system.com').first():
        u = User(username='superadmin', email='superadmin@system.com',
                 full_name='Super Admin', is_verified=True, role='super_admin')
        u.set_password('Super123!')
        db.session.add(u)
        created += 1

    # Batna 2 admins
    batna2 = uni_refs.get('batna2')
    if batna2:
        domain = 'univ-batna2.dz'

        # University Admin
        if not User.query.filter_by(email=f'admin@{domain}').first():
            u = User(username='admin_batna2', email=f'admin@{domain}',
                     full_name='Batna 2 Admin', university_id=batna2.id,
                     is_verified=True, role='university_admin')
            u.set_password('Admin123!')
            db.session.add(u)
            created += 1

        # Faculty Admins
        for code, obj in refs.items():
            if isinstance(obj, Faculty):
                fname = f'fadmin_{code.lower()}'
                email = f'{fname}@{domain}'
                if not User.query.filter_by(email=email).first():
                    u = User(username=fname, email=email,
                             full_name=f'{obj.name} Admin',
                             university_id=batna2.id, faculty_id=obj.id,
                             is_verified=True, role='faculty_admin')
                    u.set_password('Faculty123!')
                    db.session.add(u)
                    created += 1

                # Department Admins
                for code2, obj2 in refs.items():
                    if isinstance(obj2, Department) and obj2.faculty_id == obj.id:
                        dname = f'dadmin_{code2.lower()}'
                        demail = f'{dname}@{domain}'
                        if not User.query.filter_by(email=demail).first():
                            u = User(username=dname, email=demail,
                                     full_name=f'{obj2.name} Admin',
                                     university_id=batna2.id, faculty_id=obj.id,
                                     department_id=obj2.id,
                                     is_verified=True, role='department_admin')
                            u.set_password('Dept123!')
                            db.session.add(u)
                            created += 1

        # Test Student
        if not User.query.filter_by(email=f'student@{domain}').first():
            fac_ref = refs.get('MI_BATNA2')
            dept_ref = refs.get('CS_BATNA2')
            if fac_ref and dept_ref:
                u = User(username='test_student', email=f'student@{domain}',
                         full_name='Test Student',
                         university_id=batna2.id, faculty_id=fac_ref.id,
                         department_id=dept_ref.id,
                         is_verified=True, role='student')
                u.set_password('Test123!')
                db.session.add(u)
                created += 1

    if created:
        db.session.commit()
        logger.info(f'[sync_data]  Admin accounts: {created} created')
    else:
        logger.info('[sync_data]  Admin accounts: all exist')

