from extensions import db
from datetime import datetime, timezone
class Chat(db.Model):
    __tablename__ = 'chats'

    __table_args__ = (
        db.Index('ix_chat_user_active', 'user_id', 'is_active'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), default='New Conversation')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True, index=True)

    messages = db.relationship(
        'Message', backref='chat', lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Message.created_at'
    )

    def msg_count(self):
        return self.messages.count()

    def last_msg(self):
        return self.messages.order_by(None).order_by(db.text('created_at DESC')).first()

    def touch(self):
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self):
        last = self.last_msg()
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'message_count': self.msg_count(),
            'last_message': last.to_dict() if last else None,
        }

    def __repr__(self):
        return f'<Chat {self.id}: {self.title[:30]}>'