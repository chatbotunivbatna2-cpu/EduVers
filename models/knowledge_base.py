from extensions import db
from datetime import datetime, timezone
import json
class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_base'

    __table_args__ = (
        db.Index('ix_kb_uni_active', 'university_id', 'is_active'),
        db.Index('ix_kb_uni_fac', 'university_id', 'faculty_id'),
        db.Index('ix_kb_uni_dept', 'university_id', 'department_id'),
        db.Index('ix_kb_uni_cat', 'university_id', 'category'),
    )

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('universities.id'), nullable=False, index=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=True, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True, index=True)

    faculty = db.relationship('Faculty', backref='knowledge_entries', lazy=True)
    department = db.relationship('Department', backref='knowledge_entries', lazy=True)

    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    content_ar = db.Column(db.Text)

    category = db.Column(db.String(100), index=True)
    _tags = db.Column('tags', db.Text)

    source_type = db.Column(db.String(50))
    source_url = db.Column(db.String(500))
    priority = db.Column(db.Integer, default=5)

    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    @property
    def tags(self):
        if not self._tags:
            return []
        try:
            return json.loads(self._tags)
        except (ValueError, TypeError):
            return [t.strip() for t in self._tags.split(',') if t.strip()]

    @tags.setter
    def tags(self, val):
        if isinstance(val, list):
            self._tags = json.dumps(val)
        elif isinstance(val, str):
            items = [t.strip() for t in val.split(',') if t.strip()]
            self._tags = json.dumps(items)
        else:
            self._tags = json.dumps([])

    def to_dict(self):
        data = {
            'id': self.id,
            'university_id': self.university_id,
            'faculty_id': self.faculty_id,
            'department_id': self.department_id,
            'title': self.title,
            'content': self.content,
            'content_ar': self.content_ar,
            'category': self.category,
            'tags': self.tags,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'priority': self.priority,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }
        data['faculty_name'] = self.faculty.name if self.faculty else None
        if self.department:
            data['department_name'] = self.department.name
        elif self.faculty:
            data['department_name'] = 'Faculty-wide'
        else:
            data['department_name'] = 'University-wide'
        return data

    def __repr__(self):
        return f'<KnowledgeBase {self.id}: {self.title[:40]}>'