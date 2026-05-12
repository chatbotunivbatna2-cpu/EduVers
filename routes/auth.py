from flask import Blueprint, request, jsonify, session, render_template
from models.user import User
from models.university import University
from models.faculty import Faculty
from models.department import Department
from extensions import db, limiter
from services.email_service import send_verification_email
from utils.validators import validate_email, validate_password
from datetime import datetime, timezone
import logging

auth_bp = Blueprint('auth', __name__)
log = logging.getLogger(__name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("20 per hour", methods=["POST"])
def signup():
    if request.method == 'GET':
        return render_template('auth/signup.html')

    try:
        data = request.get_json() if request.is_json else request.form

        user = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        pwd = data.get('password', '')
        name = data.get('full_name', '').strip()
        dept_id = data.get('department_id')
        fac_id = data.get('faculty_id')
        stud_id = data.get('student_id', '').strip()
        uni_id = data.get('university_id')

        if not user or not email or not pwd:
            return jsonify({'error': 'All fields are required'}), 400
        if not uni_id:
            return jsonify({'error': 'Please select a university'}), 400
        if not fac_id:
            return jsonify({'error': 'Please select a faculty'}), 400
        if not dept_id:
            return jsonify({'error': 'Please select a department'}), 400

        uni = db.session.get(University, uni_id)
        if not uni or not uni.is_active:
            return jsonify({'error': 'Invalid university selected'}), 400

        fac = db.session.get(Faculty, fac_id)
        if not fac or fac.university_id != int(uni_id) or not fac.is_active:
            return jsonify({'error': 'Invalid faculty selected'}), 400

        if dept_id:
            dept = db.session.get(Department, dept_id)
            if not dept or dept.faculty_id != int(fac_id) or dept.university_id != int(uni_id) or not dept.is_active:
                return jsonify({'error': 'Invalid department selected'}), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        valid, pwd_error = validate_password(pwd)
        if not valid:
            return jsonify({'error': pwd_error}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        if User.query.filter_by(username=user).first():
            return jsonify({'error': 'Username already taken'}), 409

        new_user = User(
            username=user,
            email=email,
            full_name=name,
            university_id=uni_id,
            faculty_id=fac_id,
            department_id=dept_id,
            student_id=stud_id,
            role='student'
        )
        new_user.set_password(pwd)
        new_user.generate_verification_token()

        db.session.add(new_user)
        db.session.commit()

        try:
            send_verification_email(new_user)
        except Exception as e:
            log.warning(f"Failed to send email: {e}")

        return jsonify({
            'message': 'Account created successfully. Please check your email.',
            'user': new_user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error("Signup error: " + str(e), exc_info=True)
        return jsonify({'error': 'Failed to create account'}), 500

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute;50 per hour")
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    data = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip().lower()
    pwd = data.get('password', '')

    if not email or not pwd:
        return jsonify({'error': 'Email and password are required'}), 400

    u = User.query.filter_by(email=email).first()

    if not u or not u.check_password(pwd):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not u.is_verified:
        return jsonify({'error': 'Please verify your email first'}), 403

    u.last_login = datetime.now(timezone.utc)
    db.session.commit()

    session['user_id'] = u.id
    session['username'] = u.username
    session['is_admin'] = u.is_admin
    session['faculty_id'] = u.faculty_id
    session['department_id'] = u.department_id
    session['role'] = u.role
    session['university_id'] = u.university_id
    session.permanent = True

    return jsonify({
        'message': 'Login successful',
        'user': u.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

@auth_bp.route('/verify/<token>')
def verify_email(token):
    u = User.query.filter_by(verification_token=token).first()

    if not u:
        return render_template('auth/verification_failed.html', message='Invalid token')

    if u.is_verified:
        return render_template('auth/verification_success.html', message='Email already verified')

    u.verify_email()
    db.session.commit()
    return render_template('auth/verification_success.html', message='Verified! You can log in now.')

@auth_bp.route('/me')
def get_me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    u = db.session.get(User, session['user_id'])
    if not u:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': u.to_dict()}), 200

@auth_bp.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    u = db.session.get(User, session['user_id'])
    if not u:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if 'full_name' in data:
        u.full_name = data['full_name'].strip()
    if 'department_id' in data:
        u.department_id = data['department_id']
    if 'student_id' in data:
        u.student_id = data['student_id'].strip()

    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated', 'user': u.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        log.error("Update profile error: " + str(e))
        return jsonify({'error': 'Failed to update'}), 500

@auth_bp.route('/universities', methods=['GET'])
def get_unis():
    unis = University.query.filter_by(is_active=True).order_by(University.name).all()
    return jsonify({'universities': [u.to_dict() for u in unis]}), 200

@auth_bp.route('/universities/<int:uni_id>/faculties', methods=['GET'])
def get_facs(uni_id):
    u = db.session.get(University, uni_id)
    if not u:
        return jsonify({'error': 'University not found'}), 404

    facs = Faculty.query.filter_by(university_id=uni_id, is_active=True).order_by(Faculty.name).all()
    return jsonify({'faculties': [f.to_dict() for f in facs], 'university': u.to_dict()}), 200

@auth_bp.route('/faculties/<int:fac_id>/departments', methods=['GET'])
def get_fac_depts(fac_id):
    f = db.session.get(Faculty, fac_id)
    if not f:
        return jsonify({'error': 'Faculty not found'}), 404

    depts = Department.query.filter_by(faculty_id=fac_id, is_active=True).order_by(Department.name).all()
    return jsonify({'departments': [d.to_dict() for d in depts], 'faculty': f.to_dict()}), 200
