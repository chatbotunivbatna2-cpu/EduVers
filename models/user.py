from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import secrets


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    is_verified = db.Column(db.Boolean, default=False, index=True)
    verification_token = db.Column(db.String(100), unique=True)

    full_name = db.Column(db.String(120))
    student_id = db.Column(db.String(50))

    university_id = db.Column(db.Integer, db.ForeignKey('universities.id'), nullable=True, index=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=True, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    role = db.Column(db.String(50), default='student', nullable=False, index=True)

    chats = db.relationship('Chat', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    ROLE_HIERARCHY = {
        'super_admin': 5,
        'university_admin': 4,
        'faculty_admin': 3,
        'department_admin': 2,
        'student': 1,
    }

    ADMIN_ROLES = {'super_admin', 'university_admin', 'faculty_admin', 'department_admin'}
    VALID_ROLES = set(ROLE_HIERARCHY.keys())

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_university_admin(self):
        return self.role == 'university_admin'

    @property
    def is_faculty_admin(self):
        return self.role == 'faculty_admin'

    @property
    def is_department_admin(self):
        return self.role == 'department_admin'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_admin(self):
        return self.role in self.ADMIN_ROLES

    def has_role(self, role):
        return self.ROLE_HIERARCHY.get(self.role, 0) >= self.ROLE_HIERARCHY.get(role, 0)

    def can_manage_role(self, target):
        my_lvl = self.ROLE_HIERARCHY.get(self.role, 0)
        t_lvl = self.ROLE_HIERARCHY.get(target, 0)
        if self.is_super_admin:
            return target != 'super_admin'
        return my_lvl == t_lvl + 1

    def can_access_university(self, uni_id):
        if self.is_super_admin:
            return True
        return self.university_id == uni_id

    def can_access_faculty(self, fac_id, fac_uni_id):
        if self.is_super_admin:
            return True
        if self.is_university_admin:
            return self.university_id == fac_uni_id
        return self.faculty_id == fac_id

    def can_access_department(self, dept_id, dept_fac_id, dept_uni_id):
        if self.is_super_admin:
            return True
        if self.is_university_admin:
            return self.university_id == dept_uni_id
        if self.is_faculty_admin:
            return self.faculty_id == dept_fac_id
        return self.department_id == dept_id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token

    def verify_email(self):
        self.is_verified = True
        self.verification_token = None

    def to_dict(self):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'student_id': self.student_id,
            'university_id': self.university_id,
            'faculty_id': self.faculty_id,
            'department_id': self.department_id,
            'is_verified': self.is_verified,
            'role': self.role,
            'is_admin': self.is_admin,
            'is_super_admin': self.is_super_admin,
            'is_university_admin': self.is_university_admin,
            'is_faculty_admin': self.is_faculty_admin,
            'is_department_admin': self.is_department_admin,
            'is_student': self.is_student,
        }

        data['university'] = {'id': self.university.id, 'name': self.university.name} if self.university else None
        data['faculty'] = {'id': self.faculty_info.id, 'name': self.faculty_info.name} if self.faculty_info else None
        data['department'] = {'id': self.department_info.id, 'name': self.department_info.name} if self.department_info else None

        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['last_login'] = self.last_login.isoformat() if self.last_login else None

        return data

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'
