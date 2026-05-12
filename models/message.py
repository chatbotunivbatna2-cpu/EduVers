from extensions import db
from datetime import datetime, timezone
class Message(db.Model):
    __tablename__ = 'messages'

    __table_args__ = (
        db.Index('ix_msg_chat_created', 'chat_id', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    token_count = db.Column(db.Integer)
    model = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'content': self.content,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'token_count': self.token_count,
            'model': self.model,
        }

    def __repr__(self):
        return f'<Message {self.id} [{self.role}]>'