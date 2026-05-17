from flask import Blueprint, request, jsonify, render_template, session, redirect
from models.user import User
from models.chat import Chat
from models.message import Message
from models.university import University
from models.department import Department
from models.knowledge_base import KnowledgeBase
from extensions import db
from utils.decorators import (
    _get_user,
    admin_required,
    super_admin_required,
    university_admin_required,
    faculty_admin_required,
    department_admin_required,
)
from sqlalchemy import func, or_
from models.faculty import Faculty
from services.knowledge_service import knowledge_service

admin_bp = Blueprint('admin', __name__)
get_current_user = _get_user

def _scoped_faculty_query(current_user):
    # Search faculties list based on the admin's role
    q = Faculty.query
    if current_user.is_super_admin:
        return q
    if current_user.is_university_admin:
        return q.filter_by(university_id=current_user.university_id)
    if current_user.faculty_id:
        return q.filter_by(id=current_user.faculty_id)
    return q.filter(False)

def _scoped_department_query(current_user):
    q = Department.query
    if current_user.is_super_admin:
        return q
    if current_user.is_university_admin:
        return q.filter_by(university_id=current_user.university_id)
    if current_user.is_faculty_admin:
        return q.filter_by(faculty_id=current_user.faculty_id)
    if current_user.department_id:
        return q.filter_by(id=current_user.department_id)
    return q.filter(False)

def _scoped_knowledge_query(current_user):
    q = KnowledgeBase.query.filter_by(is_active=True)
    if current_user.is_super_admin:
        return q
    if current_user.is_university_admin:
        # University admin can see all knowledge entries for their university
        return q.filter_by(university_id=current_user.university_id)
    if current_user.is_faculty_admin:
        # Faculty admin can see faculty-level and university-level knowledge
        return q.filter(
            KnowledgeBase.university_id == current_user.university_id,
            or_(
                KnowledgeBase.faculty_id == current_user.faculty_id,
                db.and_(
                    KnowledgeBase.faculty_id.is_(None),
                    KnowledgeBase.department_id.is_(None)
                )
            )
        )
    if current_user.is_department_admin:
        # Department admin can see department-level, faculty-level and university-level knowledge
        return q.filter(
            KnowledgeBase.university_id == current_user.university_id,
            or_(
                KnowledgeBase.department_id == current_user.department_id,
                db.and_(
                    KnowledgeBase.faculty_id == current_user.faculty_id,
                    KnowledgeBase.department_id.is_(None)
                ),
                db.and_(
                    KnowledgeBase.faculty_id.is_(None),
                    KnowledgeBase.department_id.is_(None)
                )
            )
        )
    return q.filter(False)

def _scoped_admins_count(current_user):
    """Count admins visible to the current user based on their role scope."""
    admin_roles = ['super_admin', 'university_admin', 'faculty_admin', 'department_admin']
    q = User.query.filter(User.role.in_(admin_roles))
    if current_user.is_super_admin:
        return q.count()
    if current_user.is_university_admin:
        return q.filter_by(university_id=current_user.university_id).count()
    if current_user.is_faculty_admin:
        return q.filter_by(faculty_id=current_user.faculty_id).count()
    if current_user.is_department_admin:
        return q.filter_by(department_id=current_user.department_id).count()
    return 0

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    current_user = get_current_user()
    if not current_user:
        return redirect('/auth/login')

    templates = {
        'super_admin': 'admin/super_admin_dashboard.html',
        'university_admin': 'admin/university_admin_dashboard.html',
        'faculty_admin': 'admin/faculty_admin_dashboard.html',
        'department_admin': 'admin/department_admin_dashboard.html',
    }
    template = templates.get(current_user.role)
    if not template:
        return redirect('/auth/login')
    return render_template(template)

@admin_bp.route('/system-stats', methods=['GET'])
@super_admin_required
def get_system_stats(current_user):
    try:
        return jsonify({
            'universities_count': University.query.count(),
            'active_universities_count': University.query.filter_by(is_active=True).count(),
            'faculties_count': Faculty.query.count(),
            'active_faculties_count': Faculty.query.filter_by(is_active=True).count(),
            'departments_count': Department.query.count(),
            'active_departments_count': Department.query.filter_by(is_active=True).count(),
            'users_count': User.query.count(),
            'verified_users_count': User.query.filter_by(is_verified=True).count(),
            'admins_count': User.query.filter(
                User.role.in_(['university_admin', 'faculty_admin', 'department_admin', 'super_admin'])
            ).count(),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    try:
        current_user = get_current_user()
        university_id = request.args.get('university_id', type=int)

        if current_user.is_university_admin:
            university_id = current_user.university_id
        elif current_user.is_faculty_admin:
            university_id = current_user.university_id
        elif current_user.is_department_admin:
            university_id = current_user.university_id

        fac_query = _scoped_faculty_query(current_user)
        dept_query = _scoped_department_query(current_user)
        user_query = User.query.filter(User.role == 'student')
        kb_query = _scoped_knowledge_query(current_user)

        if university_id and current_user.is_super_admin:
            fac_query = fac_query.filter_by(university_id=university_id)
            dept_query = dept_query.filter_by(university_id=university_id)
            user_query = user_query.filter_by(university_id=university_id)
            kb_query = kb_query.filter_by(university_id=university_id)

        if current_user.is_super_admin:
            unis_count = University.query.count()
            active_unis_count = University.query.filter_by(is_active=True).count()
        else:
            unis_count = 1
            active_unis_count = 1

        return jsonify({
            'universities_count': unis_count,
            'active_universities_count': active_unis_count,
            'faculties_count': fac_query.count(),
            'active_faculties_count': fac_query.filter_by(is_active=True).count(),
            'departments_count': dept_query.count(),
            'active_departments_count': dept_query.filter_by(is_active=True).count(),
            'users_count': user_query.count(),
            'verified_users_count': user_query.filter_by(is_verified=True).count(),
            'students_count': user_query.count(),
            'admins_count': _scoped_admins_count(current_user),
            'knowledge_count': kb_query.count(),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q = User.query

    if current_user.is_super_admin:
        uid = request.args.get('university_id', type=int)
        if uid:
            q = q.filter_by(university_id=uid)
    elif current_user.is_university_admin:
        q = q.filter_by(university_id=current_user.university_id)
    elif current_user.is_faculty_admin:
        q = q.filter_by(faculty_id=current_user.faculty_id)
    elif current_user.is_department_admin:
        q = q.filter_by(department_id=current_user.department_id)
    else:
        return jsonify({'error': 'Access denied'}), 403

    verified_param = request.args.get('verified')
    status_param = request.args.get('status')
    if verified_param == 'true' or status_param == 'verified':
        q = q.filter_by(is_verified=True)
    elif verified_param == 'false' or status_param == 'unverified':
        q = q.filter_by(is_verified=False)

    pagination = q.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    }), 200

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if current_user.is_university_admin and user.university_id != current_user.university_id:
        return jsonify({'error': 'Access denied'}), 403
    if current_user.is_faculty_admin and user.faculty_id != current_user.faculty_id:
        return jsonify({'error': 'Access denied'}), 403
    if current_user.is_department_admin and user.department_id != current_user.department_id:
        return jsonify({'error': 'Access denied'}), 403

    chat_count = Chat.query.filter_by(user_id=user_id, is_active=True).count()
    message_count = db.session.query(Message).join(Chat).filter(Chat.user_id == user_id).count()
    total_tokens = db.session.query(func.sum(Message.token_count)).join(Chat).filter(
        Chat.user_id == user_id
    ).scalar() or 0

    data = user.to_dict()
    data['stats'] = {
        'chat_count': chat_count,
        'message_count': message_count,
        'total_tokens': total_tokens
    }
    return jsonify({'user': data}), 200

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400

    # Prevent deleting users with equal or higher role level
    if User.ROLE_HIERARCHY.get(user.role, 0) >= User.ROLE_HIERARCHY.get(current_user.role, 0):
        return jsonify({'error': 'Cannot delete a user at the same or higher role level'}), 403

    if current_user.is_university_admin and user.university_id != current_user.university_id:
        return jsonify({'error': 'Access denied'}), 403
    if current_user.is_faculty_admin and user.faculty_id != current_user.faculty_id:
        return jsonify({'error': 'Access denied'}), 403
    if current_user.is_department_admin and user.department_id != current_user.department_id:
        return jsonify({'error': 'Access denied'}), 403

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User removed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not delete user'}), 500

@admin_bp.route('/users/create-admin', methods=['POST'])
@admin_required
def create_subordinate_admin():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    role_below = {
        'super_admin': 'university_admin',
        'university_admin': 'faculty_admin',
        'faculty_admin': 'department_admin',
    }.get(current_user.role)

    if not role_below:
        return jsonify({'error': 'Your role cannot create admin accounts'}), 403

    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    university_id = data.get('university_id')
    faculty_id = data.get('faculty_id')
    department_id = data.get('department_id')

    if role_below == 'university_admin':
        if not university_id:
            return jsonify({'error': 'university_id is required'}), 400
        if not db.session.get(University, university_id):
            return jsonify({'error': 'University not found'}), 404
        faculty_id = None
        department_id = None

    elif role_below == 'faculty_admin':
        university_id = current_user.university_id
        if not faculty_id:
            return jsonify({'error': 'faculty_id is required'}), 400
        faculty = db.session.get(Faculty, faculty_id)
        if not faculty or faculty.university_id != university_id:
            return jsonify({'error': 'Faculty not found or not in your university'}), 404
        department_id = None

    elif role_below == 'department_admin':
        university_id = current_user.university_id
        faculty_id = current_user.faculty_id
        if not department_id:
            return jsonify({'error': 'department_id is required'}), 400
        dept = db.session.get(Department, department_id)
        if not dept or dept.faculty_id != faculty_id:
            return jsonify({'error': 'Department not found or not in your faculty'}), 404

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    try:
        user = User(
            username=username, email=email, full_name=full_name,
            university_id=university_id, faculty_id=faculty_id, department_id=department_id,
            role=role_below, is_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': role_below + ' created', 'user': user.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create admin: ' + str(e)}), 500

@admin_bp.route('/admins', methods=['GET'])
@admin_required
def list_admins():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    if current_user.is_super_admin:
        admins = User.query.filter(
            User.role.in_(['super_admin', 'university_admin', 'faculty_admin', 'department_admin'])
        ).all()
    elif current_user.is_university_admin:
        admins = User.query.filter(
            User.role.in_(['faculty_admin', 'department_admin']),
            User.university_id == current_user.university_id
        ).all()
    elif current_user.is_faculty_admin:
        admins = User.query.filter(
            User.role == 'department_admin',
            User.faculty_id == current_user.faculty_id
        ).all()
    else:
        admins = []

    return jsonify({'admins': [a.to_dict() for a in admins]}), 200

@admin_bp.route('/admins/<int:admin_id>', methods=['GET'])
@admin_required
def get_admin(admin_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401
    admin = db.session.get(User, admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404

    # Scope check: admins can only view admins within their scope
    if not current_user.is_super_admin:
        if current_user.is_university_admin and admin.university_id != current_user.university_id:
            return jsonify({'error': 'Access denied'}), 403
        if current_user.is_faculty_admin and admin.faculty_id != current_user.faculty_id:
            return jsonify({'error': 'Access denied'}), 403
        if current_user.is_department_admin and admin.department_id != current_user.department_id:
            return jsonify({'error': 'Access denied'}), 403

    return jsonify({'admin': admin.to_dict()}), 200

@admin_bp.route('/admins', methods=['POST'])
@super_admin_required
def create_admin(current_user):
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'university_admin')
    university_id = data.get('university_id')
    faculty_id = data.get('faculty_id')
    department_id = data.get('department_id')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    if role not in User.VALID_ROLES or role == 'super_admin':
        return jsonify({'error': 'Invalid role for admin creation'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    try:
        user = User(
            username=username, email=email, full_name=full_name,
            university_id=university_id, faculty_id=faculty_id, department_id=department_id,
            role=role, is_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Admin account created', 'admin': user.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create admin: ' + str(e)}), 500

@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@super_admin_required
def update_admin(admin_id, current_user):
    admin = db.session.get(User, admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    if admin.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own account here'}), 400

    data = request.get_json()
    try:
        for field in ('username', 'email', 'full_name', 'role', 'university_id', 'faculty_id', 'department_id'):
            if field in data:
                val = data[field]
                if field == 'email':
                    setattr(admin, field, val.strip().lower())
                elif isinstance(val, str):
                    setattr(admin, field, val.strip())
                else:
                    setattr(admin, field, val)
        if 'password' in data and data['password']:
            admin.set_password(data['password'])
        db.session.commit()
        return jsonify({'message': 'Admin updated', 'admin': admin.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Update error: ' + str(e)}), 500

@admin_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@admin_required
def delete_admin(admin_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    admin = db.session.get(User, admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    if admin.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    # Ensure admin cannot delete another admin of equal or higher level
    if User.ROLE_HIERARCHY.get(admin.role, 0) >= User.ROLE_HIERARCHY.get(current_user.role, 0):
        return jsonify({'error': 'Cannot delete a user at the same or higher role level'}), 403

    if current_user.is_university_admin:
        if admin.university_id != current_user.university_id:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.is_faculty_admin:
        if admin.faculty_id != current_user.faculty_id:
            return jsonify({'error': 'Access denied'}), 403

    try:
        db.session.delete(admin)
        db.session.commit()
        return jsonify({'message': 'Admin deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Delete error'}), 500

@admin_bp.route('/universities', methods=['GET'])
@admin_required
def list_universities():
    current_user = get_current_user()
    if current_user.is_super_admin:
        unis = University.query.order_by(University.name).all()
    else:
        uni = db.session.get(University, current_user.university_id)
        if uni:
            unis = [uni]
        else:
            unis = []
    return jsonify({'universities': [u.to_dict() for u in unis]}), 200

@admin_bp.route('/universities', methods=['POST'])
@super_admin_required
def create_university(current_user):
    data = request.get_json()
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()

    if not name or not code:
        return jsonify({'error': 'Name and code are required'}), 400
    if University.query.filter_by(code=code).first():
        return jsonify({'error': 'University code already exists'}), 409

    try:
        university = University(
            name=name,
            name_ar=data.get('name_ar', '').strip(),
            code=code,
            city=data.get('city', '').strip(),
            province=data.get('province', '').strip(),
            website=data.get('website', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            address=data.get('address', '').strip(),
            description=data.get('description', '').strip(),
            is_active=data.get('is_active', True),
        )
        db.session.add(university)
        db.session.commit()
        return jsonify({'message': 'University added', 'university': university.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create university: ' + str(e)}), 500

@admin_bp.route('/universities/<int:university_id>', methods=['GET'])
@admin_required
def get_university(university_id):
    current_user = get_current_user()
    if not current_user.can_access_university(university_id):
        return jsonify({'error': 'Access denied'}), 403
    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404
    return jsonify({'university': uni.to_dict()}), 200


@admin_bp.route('/universities/<int:university_id>', methods=['PUT'])
@admin_required
def update_university(university_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401
    if not current_user.has_role('university_admin'):
        return jsonify({'error': 'Access denied'}), 403
    if not current_user.can_access_university(university_id):
        return jsonify({'error': 'Access denied'}), 403

    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404

    data = request.get_json()
    try:
        for field in ('name', 'name_ar', 'city', 'province', 'website', 'email', 'phone', 'address', 'description'):
            if field in data:
                setattr(uni, field, data[field].strip())
        if 'is_active' in data and current_user.is_super_admin:
            uni.is_active = data['is_active']
        db.session.commit()
        return jsonify({'message': 'University updated', 'university': uni.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Update failed: ' + str(e)}), 500

@admin_bp.route('/universities/<int:university_id>', methods=['DELETE'])
@super_admin_required
def delete_university(university_id, current_user):
    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404
    try:
        db.session.delete(uni)
        db.session.commit()
        return jsonify({'message': 'University deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Delete failed'}), 500

@admin_bp.route('/faculties', methods=['GET'])
@admin_required
def list_faculties():
    current_user = get_current_user()
    university_id = request.args.get('university_id', type=int)

    q = _scoped_faculty_query(current_user)
    if current_user.is_super_admin and university_id:
        q = q.filter_by(university_id=university_id)

    return jsonify({'faculties': [f.to_dict() for f in q.all()]}), 200

@admin_bp.route('/faculties/<int:faculty_id>', methods=['GET'])
@admin_required
def get_faculty(faculty_id):
    current_user = get_current_user()
    faculty = db.session.get(Faculty, faculty_id)
    if not faculty:
        return jsonify({'error': 'Faculty not found'}), 404
    if not current_user.can_access_faculty(faculty.id, faculty.university_id):
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'faculty': faculty.to_dict()}), 200


@admin_bp.route('/faculties', methods=['POST'])
@university_admin_required
def create_faculty(current_user):
    data = request.get_json()
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()
    if current_user.is_super_admin:
        university_id = data.get('university_id')
    else:
        university_id = current_user.university_id

    if not name or not code:
        return jsonify({'error': 'Name and code are required'}), 400
    if not university_id:
        return jsonify({'error': 'University ID is required'}), 400

    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404
    if Faculty.query.filter_by(university_id=university_id, code=code).first():
        return jsonify({'error': 'Faculty code already exists for this university'}), 409

    try:
        faculty = Faculty(
            name=name,
            name_ar=data.get('name_ar', '').strip(),
            name_fr=data.get('name_fr', '').strip(),
            code=code,
            university_id=university_id,
            dean=data.get('dean', '').strip(),
            building=data.get('building', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            official_website=data.get('official_website', '').strip(),
            description=data.get('description', '').strip(),
            is_active=data.get('is_active', True),
        )
        db.session.add(faculty)
        db.session.commit()
        return jsonify({'message': 'Faculty added', 'faculty': faculty.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create faculty: ' + str(e)}), 500

@admin_bp.route('/faculties/<int:faculty_id>', methods=['PUT'])
@faculty_admin_required
def update_faculty(faculty_id, current_user):
    faculty = db.session.get(Faculty, faculty_id)
    if not faculty:
        return jsonify({'error': 'Faculty not found'}), 404
    if not current_user.can_access_faculty(faculty.id, faculty.university_id):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    try:
        for field in ('name', 'name_ar', 'name_fr', 'dean', 'building', 'email', 'phone', 'official_website', 'description'):
            if field in data:
                val = data[field]
                if isinstance(val, str):
                    setattr(faculty, field, val.strip())
                else:
                    setattr(faculty, field, val)
        if 'is_active' in data:
            faculty.is_active = data['is_active']
        db.session.commit()
        return jsonify({'message': 'Faculty updated', 'faculty': faculty.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Update failed: ' + str(e)}), 500

@admin_bp.route('/faculties/<int:faculty_id>', methods=['DELETE'])
@university_admin_required
def delete_faculty(faculty_id, current_user):
    faculty = db.session.get(Faculty, faculty_id)
    if not faculty:
        return jsonify({'error': 'Faculty not found'}), 404
    if not current_user.can_access_faculty(faculty.id, faculty.university_id):
        return jsonify({'error': 'Access denied'}), 403
    try:
        db.session.delete(faculty)
        db.session.commit()
        return jsonify({'message': 'Faculty deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Delete failed'}), 500

@admin_bp.route('/departments', methods=['GET'])
@department_admin_required
def list_departments(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    q = _scoped_department_query(current_user)

    faculty_id = request.args.get('faculty_id', type=int)
    university_id = request.args.get('university_id', type=int)
    if faculty_id and (current_user.is_super_admin or current_user.is_university_admin):
        q = q.filter_by(faculty_id=faculty_id)
    if university_id and current_user.is_super_admin:
        q = q.filter_by(university_id=university_id)

    pagination = q.order_by(Department.name).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'departments': [d.to_dict() for d in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    }), 200

@admin_bp.route('/departments/<int:department_id>', methods=['GET'])
@department_admin_required
def get_department(department_id, current_user):
    dept = db.session.get(Department, department_id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    if not current_user.can_access_department(dept.id, dept.faculty_id, dept.university_id):
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'department': dept.to_dict()}), 200

@admin_bp.route('/departments', methods=['POST'])
@faculty_admin_required
def create_department(current_user):
    data = request.get_json()
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()

    if not name or not code:
        return jsonify({'error': 'Name and code are required'}), 400

    if current_user.is_faculty_admin:
        university_id = current_user.university_id
        faculty_id = current_user.faculty_id
    else:
        university_id = data.get('university_id') or current_user.university_id
        faculty_id = data.get('faculty_id')
        if not faculty_id:
            return jsonify({'error': 'faculty_id is required'}), 400

    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404

    faculty = db.session.get(Faculty, faculty_id)
    if not faculty or faculty.university_id != int(university_id):
        return jsonify({'error': 'Faculty not found or does not belong to this university'}), 404

    if not current_user.can_access_faculty(faculty.id, faculty.university_id):
        return jsonify({'error': 'Access denied for this faculty'}), 403

    if Department.query.filter_by(university_id=university_id, code=code).first():
        return jsonify({'error': 'Department code already exists for this university'}), 409

    try:
        dept = Department(
            name=name,
            name_ar=data.get('name_ar', '').strip(),
            code=code,
            university_id=university_id,
            faculty_id=faculty_id,
            description=data.get('description', '').strip(),
            building=data.get('building', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            official_website=data.get('official_website', '').strip(),
            head_of_department=data.get('head_of_department', '').strip(),
        )
        db.session.add(dept)
        db.session.commit()
        return jsonify({'message': 'Department added', 'department': dept.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create department: ' + str(e)}), 500

@admin_bp.route('/departments/<int:department_id>', methods=['PUT'])
@department_admin_required
def update_department(department_id, current_user):
    dept = db.session.get(Department, department_id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    if current_user.is_department_admin and dept.id != current_user.department_id:
        return jsonify({'error': 'Access denied'}), 403
    if not current_user.can_access_department(dept.id, dept.faculty_id, dept.university_id):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    try:
        for field in ('name', 'name_ar', 'description', 'building', 'email', 'phone',
                    'official_website', 'head_of_department'):
            if field in data:
                val = data[field]
                if isinstance(val, str):
                    setattr(dept, field, val.strip())
                else:
                    setattr(dept, field, val)
        if 'is_active' in data:
            dept.is_active = data['is_active']
        db.session.commit()
        return jsonify({'message': 'Department updated', 'department': dept.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Update error: ' + str(e)}), 500


@admin_bp.route('/departments/<int:department_id>', methods=['DELETE'])
@faculty_admin_required
def delete_department(department_id, current_user):
    dept = db.session.get(Department, department_id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    if not current_user.can_access_department(dept.id, dept.faculty_id, dept.university_id):
        return jsonify({'error': 'Access denied'}), 403
    try:
        db.session.delete(dept)
        db.session.commit()
        return jsonify({'message': 'Department deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Delete error'}), 500

@admin_bp.route('/knowledge', methods=['GET'])
@department_admin_required
def list_knowledge(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    university_id = request.args.get('university_id', type=int)
    category = request.args.get('category')
    department_id = request.args.get('department_id', type=int)

    q = _scoped_knowledge_query(current_user)
    if current_user.is_super_admin and university_id:
        q = q.filter_by(university_id=university_id)
    if department_id:
        q = q.filter_by(department_id=department_id)
    if category:
        q = q.filter_by(category=category)

    pagination = q.order_by(KnowledgeBase.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'knowledge': [e.to_dict() for e in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    }), 200

@admin_bp.route('/knowledge', methods=['POST'])
@department_admin_required
def create_knowledge(current_user):
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    if current_user.is_department_admin:
        university_id = current_user.university_id
        faculty_id = current_user.faculty_id
        department_id = current_user.department_id
    elif current_user.is_faculty_admin:
        university_id = current_user.university_id
        faculty_id = current_user.faculty_id
        department_id = None  
    elif current_user.is_university_admin:
        university_id = current_user.university_id
        faculty_id = None     
        department_id = None   
    elif current_user.is_super_admin:
        university_id = data.get('university_id')
        faculty_id = data.get('faculty_id')
        department_id = data.get('department_id')
    else:
        return jsonify({'error': 'Access denied'}), 403

    if not university_id:
        return jsonify({'error': 'university_id is required'}), 400

    uni = db.session.get(University, university_id)
    if not uni:
        return jsonify({'error': 'University not found'}), 404

    try:
        entry = knowledge_service.add_knowledge(
            university_id=university_id,
            faculty_id=faculty_id,
            department_id=department_id,
            title=title,
            content=content,
            content_ar=data.get('content_ar', '').strip(),
            category=data.get('category', '').strip(),
            tags=data.get('tags', '').strip(),
            source_url=data.get('source_url', '').strip(),
            priority=data.get('priority', 5),
            created_by=session.get('user_id'),
        )
        return jsonify({'message': 'Entry added', 'knowledge': entry.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not save entry: ' + str(e)}), 500

@admin_bp.route('/knowledge/<int:knowledge_id>', methods=['PUT'])
@department_admin_required
def update_knowledge(knowledge_id, current_user):
    entry = db.session.get(KnowledgeBase, knowledge_id)
    if not entry:
        return jsonify({'error': 'Knowledge entry not found'}), 404

    if current_user.is_department_admin:
        if entry.department_id != current_user.department_id:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.is_faculty_admin:
        if entry.faculty_id != current_user.faculty_id or entry.department_id is not None:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.is_university_admin:
        if entry.university_id != current_user.university_id or entry.faculty_id is not None or entry.department_id is not None:
            return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    # Prevent changing scope fields
    for blocked_field in ('university_id', 'faculty_id', 'department_id'):
        data.pop(blocked_field, None)

    try:
        updated = knowledge_service.update_knowledge(knowledge_id, **data)
        if not updated:
            return jsonify({'error': 'Knowledge entry not found'}), 404
        return jsonify({'message': 'Entry updated', 'knowledge': updated.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Update failed: ' + str(e)}), 500


@admin_bp.route('/knowledge/<int:knowledge_id>', methods=['DELETE'])
@department_admin_required
def delete_knowledge(knowledge_id, current_user):
    entry = db.session.get(KnowledgeBase, knowledge_id)
    if not entry:
        return jsonify({'error': 'Knowledge entry not found'}), 404

    if current_user.is_department_admin:
        if entry.department_id != current_user.department_id:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.is_faculty_admin:
        if entry.faculty_id != current_user.faculty_id or entry.department_id is not None:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.is_university_admin:
        if entry.university_id != current_user.university_id or entry.faculty_id is not None or entry.department_id is not None:
            return jsonify({'error': 'Access denied'}), 403

    try:
        success = knowledge_service.delete_knowledge(knowledge_id)
        if not success:
            return jsonify({'error': 'Knowledge entry not found'}), 404
        return jsonify({'message': 'Knowledge entry deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete knowledge entry: ' + str(e)}), 500

@admin_bp.route('/knowledge/categories', methods=['GET'])
@department_admin_required
def get_knowledge_categories(current_user):
    university_id = request.args.get('university_id', type=int)
    if not current_user.is_super_admin:
        university_id = current_user.university_id
    if not university_id:
        return jsonify({'error': 'University ID is required'}), 400
    categories = knowledge_service.get_all_categories(university_id)
    return jsonify({'categories': categories, 'university_id': university_id}), 200
