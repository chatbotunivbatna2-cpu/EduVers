from functools import wraps
from flask import session, jsonify, request, redirect
from models.user import User
from extensions import db

def _is_api_request():
    """Check if request is an API/AJAX call vs a browser page navigation."""
    return (
        request.is_json
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.method != 'GET'
    )

def _get_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return db.session.get(User, uid)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if _is_api_request():
                return jsonify({'error': 'Login required'}), 401
            return redirect('/auth/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user()
        if not user:
            if _is_api_request():
                return jsonify({'error': 'Login required'}), 401
            return redirect('/auth/login')
        if not user.is_admin:
            if _is_api_request():
                return jsonify({'error': 'Access denied'}), 403
            return redirect('/chat/')
        return f(*args, **kwargs)
    return decorated

def require_role(min_role):
    # User must have at least the specified minimum role level
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = _get_user()
            if not user:
                return jsonify({'error': 'Login required'}), 401
            if not user.has_role(min_role):
                return jsonify({'error': 'Insufficient permissions. Required: ' + min_role}), 403
            return f(*args, current_user=user, **kwargs)
        return decorated
    return wrapper

def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user()
        if not user:
            return jsonify({'error': 'Login required'}), 401
        if not user.is_super_admin:
            return jsonify({'error': 'Not authorized'}), 403
        return f(*args, current_user=user, **kwargs)
    return decorated

def university_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user()
        if not user:
            return jsonify({'error': 'Login required'}), 401
        if not user.has_role('university_admin'):
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, current_user=user, **kwargs)
    return decorated

def faculty_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user()
        if not user:
            return jsonify({'error': 'Login required'}), 401
        if not user.has_role('faculty_admin'):
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, current_user=user, **kwargs)
    return decorated

def department_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user()
        if not user:
            return jsonify({'error': 'Login required'}), 401
        if not user.has_role('department_admin'):
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, current_user=user, **kwargs)
    return decorated
