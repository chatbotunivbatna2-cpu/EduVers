from extensions import db
from datetime import datetime, timezone

class University(db.Model):
    __tablename__ = 'universities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    name_ar = db.Column(db.String(200))
    code = db.Column(db.String(50), unique=True, nullable=False)

    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    website = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    description = db.Column(db.Text)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = db.relationship('User', backref='university', lazy=True)
    knowledge_base = db.relationship('KnowledgeBase', backref='university', lazy=True, cascade='all, delete-orphan')
    faculties = db.relationship('Faculty', backref='university', lazy=True, cascade='all, delete-orphan')
    departments = db.relationship('Department', backref='university', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'code': self.code,
            'city': self.city,
            'province': self.province,
            'website': self.website,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'description': self.description,
            'is_active': self.is_active,
            'faculties_count': len(self.faculties),
            'departments_count': len(self.departments),
            'users_count': len(self.users),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<University {self.name}>'