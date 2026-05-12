import json
import os
import sys
from datetime import datetime, timezone
from app import app
from extensions import db
from models import User, University, Faculty, Department, KnowledgeBase

def load_json(filename):
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'data', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_user(role, username, email, name, password, uni_id=None, fac_id=None, dept_id=None):
    u = User(
        username=username,
        email=email,
        full_name=name,
        university_id=uni_id,
        faculty_id=fac_id,
        department_id=dept_id,
        is_verified=True,
        role=role
    )
    u.set_password(password)
    return u

def add_faculty(session, uni_id, fac_data, d1_data, d2_data):
    fac = Faculty(**fac_data, university_id=uni_id)
    session.add(fac)
    session.flush()

    d1 = Department(**d1_data, university_id=uni_id, faculty_id=fac.id)
    d2 = Department(**d2_data, university_id=uni_id, faculty_id=fac.id)
    session.add(d1)
    session.add(d2)
    session.flush()
    return fac, d1, d2

def init_db(drop=True):
    with app.app_context():
        if drop:
            print("Dropping tables...")
            db.session.execute(db.text('DROP SCHEMA public CASCADE'))
            db.session.execute(db.text('CREATE SCHEMA public'))
            db.session.commit()

        print("Creating tables...")
        db.create_all()

        unis = load_json('init_universities.json')
        facs = load_json('init_faculties.json')
        uni_map = load_json('init_uni_map.json')

        # Create all universities
        print(f"Adding {len(unis)} universities...")
        uni_refs = {}
        for u in unis:
            vname = u.pop('var_name')
            obj = University.query.filter_by(code=u['code']).first()
            if not obj:
                obj = University(**u)
                db.session.add(obj)
                db.session.flush()
            uni_refs[vname] = obj

        # Create faculties and departments for Batna 2 only
        print("Building faculties for Batna 2...")
        refs = {}

        for entry in facs:
            if entry['university_var'] != 'batna2':
                continue
            uni = uni_refs['batna2']
            fac = Faculty.query.filter_by(code=entry['faculty']['code'], university_id=uni.id).first()
            if not fac:
                fac, d1, d2 = add_faculty(db.session, uni.id, entry['faculty'], entry['dept1'], entry['dept2'])
            else:
                d1 = Department.query.filter_by(code=entry['dept1']['code'], faculty_id=fac.id).first()
                if not d1:
                    d1 = Department(**entry['dept1'], university_id=uni.id, faculty_id=fac.id)
                    db.session.add(d1)
                d2 = Department.query.filter_by(code=entry['dept2']['code'], faculty_id=fac.id).first()
                if not d2:
                    d2 = Department(**entry['dept2'], university_id=uni.id, faculty_id=fac.id)
                    db.session.add(d2)
                db.session.flush()
                
            refs[fac.code] = fac
            refs[d1.code] = d1
            refs[d2.code] = d2

        if drop:
            print("Adding admin users...")
            db.session.add(create_user('super_admin', 'superadmin', 'superadmin@system.com', 'Super Admin', 'Super123!'))

            batna2 = uni_refs.get('batna2')
            if batna2:
                domain = 'univ-batna2.dz'
                db.session.add(create_user('university_admin', 'admin_batna2', f'admin@{domain}', 'Batna 2 Admin', 'Admin123!', uni_id=batna2.id))

                for code, obj in refs.items():
                    if isinstance(obj, Faculty):
                        fname = f'fadmin_{code.lower()}'
                        db.session.add(create_user('faculty_admin', fname, f'{fname}@{domain}', f'{obj.name} Admin', 'Faculty123!', uni_id=batna2.id, fac_id=obj.id))

                        for code2, obj2 in refs.items():
                            if isinstance(obj2, Department) and obj2.faculty_id == obj.id:
                                dname = f'dadmin_{code2.lower()}'
                                db.session.add(create_user('department_admin', dname, f'{dname}@{domain}', f'{obj2.name} Admin', 'Dept123!', uni_id=batna2.id, fac_id=obj.id, dept_id=obj2.id))

                # Test student account
                fac_ref = refs.get('MI_BATNA2')
                dept_ref = refs.get('CS_BATNA2')
                if fac_ref and dept_ref:
                    s = User(
                        username='test_student',
                        email='student@univ-batna2.dz',
                        full_name='Test Student',
                        university_id=batna2.id,
                        faculty_id=fac_ref.id,
                        department_id=dept_ref.id,
                        is_verified=True,
                        role='student'
                    )
                    s.set_password('Test123!')
                    db.session.add(s)

        db.session.commit()

        # Knowledge Base seeding
        print("\nSeeding Knowledge Base...")
        kb_data = load_json('init_knowledge.json')
        kb_count = 0
        for entry in kb_data:
            uni_var = entry.get('university_var')
            uni_obj = uni_refs.get(uni_var)
            if not uni_obj:
                continue

            # resolve faculty_id (uni -> fac -> dept)
            fac_id = None
            fac_code = entry.get('faculty_code')
            if fac_code and fac_code in refs:
                fac_id = refs[fac_code].id

            dept_id = None
            dept_code = entry.get('dept_code')
            if dept_code and dept_code in refs:
                dept_id = refs[dept_code].id
                # auto-resolve faculty from department if not set
                if not fac_id and hasattr(refs[dept_code], 'faculty_id'):
                    fac_id = refs[dept_code].faculty_id

            kb = KnowledgeBase.query.filter_by(title=entry['title'], university_id=uni_obj.id).first()
            if kb:
                kb.content = entry['content']
                kb.content_ar = entry.get('content_ar')
                kb.category = entry.get('category')
                kb.tags = entry.get('tags', [])
                kb.priority = entry.get('priority', 5)
                kb.source_url = entry.get('source_url')
                kb.faculty_id = fac_id
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
                    source_url=entry.get('source_url')
                )
                db.session.add(kb)
            kb_count += 1
            print(f"  [KB] {entry['title']}")

        db.session.commit()
        print(f"\n✅ DB INIT DONE! ({kb_count} KB entries seeded)")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        init_db(drop=False)
    else:
        init_db(drop=True)
