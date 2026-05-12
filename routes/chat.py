from flask import Blueprint, request, jsonify, session, render_template
from models.user import User
from models.chat import Chat
from models.message import Message
from models.university import University
from models.faculty import Faculty
from models.department import Department
from extensions import db
from services.gemini_service import generate_chat_response, count_tokens, generate_chat_title
from services.knowledge_service import knowledge_service
from services.faq_service import search_faq
from services.translation_service import get_all_translations
from utils.decorators import login_required
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def _compute_ai_confidence(kb_results, uni_ctx, dept_ctx, is_error):
    if is_error:
        return 0.15

    score = 0.10

    if kb_results:
        avg_relevance = sum(r.get('score', 0) for r in kb_results) / len(kb_results)
        score += min(avg_relevance, 1.0) * 0.40

    if uni_ctx:
        score += 0.30

    if dept_ctx:
        score += 0.20

    return min(score, 1.0)

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
@login_required
def chat_page():
    return render_template('chat/chat.html')

@chat_bp.route('/user-info')
@login_required
def user_info():
    u = db.session.get(User, session['user_id'])
    return jsonify(u.to_dict())

@chat_bp.route('/new', methods=['POST'])
@login_required
def create_chat():
    uid = session.get('user_id')
    data = request.get_json()
    title = data.get('title', 'New Conversation')

    c = Chat(user_id=uid, title=title)
    try:
        db.session.add(c)
        db.session.commit()
        return jsonify({'chat': c.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create chat'}), 500

@chat_bp.route('/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    c = db.session.get(Chat, chat_id)
    if not c or c.user_id != session.get('user_id'):
        return jsonify({'error': 'Chat not found'}), 404
    try:
        db.session.delete(c)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete chat'}), 500

@chat_bp.route('/list', methods=['GET'])
@login_required
def list_chats():
    uid = session.get('user_id')
    chats = Chat.query.filter_by(user_id=uid, is_active=True).order_by(Chat.updated_at.desc()).all()
    return jsonify({'chats': [c.to_dict() for c in chats]}), 200

@chat_bp.route('/<int:chat_id>', methods=['GET'])
@login_required
def get_chat(chat_id):
    uid = session.get('user_id')
    c = Chat.query.filter_by(id=chat_id, user_id=uid).first()
    if not c:
        return jsonify({'error': 'Chat not found'}), 404

    return jsonify({
        'chat': c.to_dict(),
        'messages': [m.to_dict() for m in c.messages]
    }), 200

@chat_bp.route('/<int:chat_id>/message', methods=['POST'])
@login_required
def send_message(chat_id):
    uid = session.get('user_id')
    c = Chat.query.filter_by(id=chat_id, user_id=uid).first()
    if not c:
        return jsonify({'error': 'Chat not found'}), 404

    data = request.get_json()
    msg_text = data.get('message', '').strip()

    if not msg_text:
        return jsonify({'error': 'Message cannot be empty'}), 400

    try:
        u = db.session.get(User, uid)
        uni_ctx = None
        kb_ctx = None
        dept_ctx = None
        fac_ctx = None
        kb_results = []

        if u and u.university_id:
            uni_ctx = knowledge_service.get_university_context(u.university_id)

            if u.faculty_id:
                fac = db.session.get(Faculty, u.faculty_id)
                if fac:
                    fac_ctx = f"Faculty: {fac.name}\nArabic name: {fac.name_ar or 'N/A'}\nCode: {fac.code}\nDean: {fac.dean or 'N/A'}\nWebsite: {fac.official_website or 'N/A'}\nEmail: {fac.email or 'N/A'}\nBuilding: {fac.building or 'N/A'}"

            if u.department_id:
                dept = db.session.get(Department, u.department_id)
                if dept:
                    dept_ctx = f"Department: {dept.name}\nArabic name: {dept.name_ar or 'N/A'}\nCode: {dept.code}\nWebsite: {dept.official_website or 'N/A'}\nEmail: {dept.email or 'N/A'}\nBuilding: {dept.building or 'N/A'}\nHead: {dept.head_of_department or 'N/A'}"

            kb_results = knowledge_service.search_knowledge(msg_text, u.university_id, faculty_id=u.faculty_id, department_id=u.department_id, limit=3)
            logger.info(f"[KB DEBUG] Query: {msg_text[:50]} | Found {len(kb_results)} results")
            for r in kb_results:
                logger.info(f"  [KB HIT] score={r['score']} title={r['title']}")
            if kb_results:
                kb_ctx = "\n".join([f"- {r['title']}: {r['content']} | ARABIC: {r.get('content_ar', '')}" for r in kb_results])

        is_first_message = c.msg_count() == 0

        u_msg = Message(chat_id=chat_id, content=msg_text, role='user', token_count=count_tokens(msg_text))
        db.session.add(u_msg)

        uni_obj = db.session.get(University, u.university_id) if u and u.university_id else None
        faq = search_faq(msg_text, university=uni_obj)
        faq_used = False
        model = 'faq'

        if faq.get('found') and faq.get('confidence', 0) >= 0.35:
            resp_text = faq['answer']
            faq_used = True
        else:
            hist = [{'role': m.role, 'content': m.content} for m in c.messages]
            hist.append({'role': 'user', 'content': msg_text})

            resp_text, model = generate_chat_response(hist, university_context=uni_ctx, knowledge_context=kb_ctx, department_context=dept_ctx, faculty_context=fac_ctx)

        is_err = False
        if not faq_used:
            err_keywords = ["Error:", "⚠️", "I apologize", "unable to respond", "contact the administrator"]
            if any(k in resp_text for k in err_keywords):
                is_err = True

        ai_msg = Message(chat_id=chat_id, content=resp_text, role='assistant', token_count=count_tokens(resp_text), model=model)
        db.session.add(ai_msg)

        c.updated_at = datetime.now(timezone.utc)

        if is_first_message and len(msg_text) > 0:
            gen_title = generate_chat_title(msg_text)
            c.title = gen_title if gen_title else (msg_text[:50] + '...' if len(msg_text) > 50 else msg_text)

        db.session.commit()

        if faq_used:
            confidence = faq.get('confidence', 0)
            source = 'faq'
        else:
            confidence = _compute_ai_confidence(kb_results, uni_ctx, dept_ctx, is_err)
            source = 'ai'

        resp_data = {
            'user_message': u_msg.to_dict(),
            'ai_message': ai_msg.to_dict(),
            'chat_title': c.title,
            'source': source,
            'confidence': round(confidence, 2),
        }
        if is_err:
            resp_data['warning'] = 'API_ERROR'

        return jsonify(resp_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to process message: ' + str(e)}), 500

@chat_bp.route('/clear-all', methods=['DELETE'])
@login_required
def clear_all_chats():
    uid = session.get('user_id')
    try:
        Chat.query.filter_by(user_id=uid).update({Chat.is_active: False})
        db.session.commit()
        return jsonify({'message': 'All chats cleared'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to clear chats'}), 500

@chat_bp.route('/translations/<lang>', methods=['GET'])
def get_trans(lang):
    return jsonify({'translations': get_all_translations(lang), 'language': lang}), 200