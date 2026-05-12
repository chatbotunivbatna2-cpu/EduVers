from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
from datetime import datetime
import json
from dataclasses import dataclass, field

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from models.university import University
from models.faculty import Faculty
from models.department import Department
from services.knowledge_service import knowledge_service
from services.faq_service import search_faq
from services.gemini_service import generate_chat_response

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

MAX_HIST = 12
FAQ_CONF = 0.50
SESSION_TIMEOUT = 120
MAX_MSG_LEN = 4096

CB_UNI = "uni"
CB_FAC = "fac"
CB_DEPT = "dept"
CB_SKIP = "skip_dept"
CB_LANG = "lang"

LANGS = {
    "ar":   "Arabic (العربية)",
    "en":   "English",
    "fr":   "Français",
    "auto": "Auto-detect",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@dataclass
class Session:
    uni_id: int = None
    uni_name: str = None
    fac_id: int = None
    fac_name: str = None
    dept_id: int = None
    dept_name: str = None
    lang: str = "auto"
    history: list = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    last_msg: datetime = field(default_factory=datetime.now)
    msg_count: int = 0

    @property
    def ready(self):
        return bool(self.uni_id and self.fac_id)

    @property
    def minutes(self):
        return int((datetime.now() - self.created).total_seconds() / 60)

    @property
    def expired(self):
        idle = (datetime.now() - self.last_msg).total_seconds() / 60
        return idle > SESSION_TIMEOUT

    def touch(self):
        self.last_msg = datetime.now()

    def add_turn(self, user_msg, bot_msg):
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": bot_msg})
        # Remove the old records to preserve memory
        if len(self.history) > MAX_HIST * 2:
            self.history = self.history[-(MAX_HIST * 2):]
        self.msg_count += 1
        self.touch()

    def summary(self):
        parts = []
        if self.uni_name:
            parts.append('🏛 University : ' + self.uni_name)
        if self.fac_name:
            parts.append('🏫 Faculty    : ' + self.fac_name)
        if self.dept_name:
            parts.append('📂 Department : ' + self.dept_name)
        parts.append('🌐 Language   : ' + LANGS.get(self.lang, 'Auto'))
        return "\n".join(parts) if parts else "No active session."

    def card(self):
        return (
            '🏛 *University*  : ' + (self.uni_name or '—') + '\n'
            '🏫 *Faculty*     : ' + (self.fac_name or 'Not selected') + '\n'
            '📂 *Department*  : ' + (self.dept_name or 'Not selected') + '\n'
            '🌐 *Language*    : ' + LANGS.get(self.lang, 'Auto') + '\n'
            '⏱ *Duration*    : ' + str(self.minutes) + ' min\n'
            '💬 *Exchanges*   : ' + str(self.msg_count)
        )


# Store sessions in a standard dictionary
_sessions: dict = {}

flask_app = None


def get_session(uid):
    if uid in _sessions and _sessions[uid].expired:
        logger.info("session expired for %s", uid)
        _sessions.pop(uid)
    if uid not in _sessions:
        _sessions[uid] = Session()
    return _sessions[uid]

def new_session(uid):
    _sessions[uid] = Session()
    return _sessions[uid]

def set_flask_app(app):
    global flask_app
    flask_app = app

def app_ctx():
    if flask_app is None:
        raise RuntimeError("Flask app not set. call set_flask_app() first.")
    return flask_app.app_context()

def uni_keyboard():
    with app_ctx():
        unis = University.query.filter_by(is_active=True).order_by(University.name).all()
        if not unis:
            return None
        rows = [
            [InlineKeyboardButton(
                f"🏛 {u.name}" + (f"  ({u.city})" if u.city else ""),
                callback_data=f"{CB_UNI}_{u.id}",
            )]
            for u in unis
        ]
        return InlineKeyboardMarkup(rows)


def fac_keyboard(uni_id):
    with app_ctx():
        facs = Faculty.query.filter_by(university_id=uni_id, is_active=True).order_by(Faculty.name).all()
        if not facs:
            return None
        rows = [
            [InlineKeyboardButton(f"🏫 {f.name}", callback_data=f"{CB_FAC}_{f.id}")]
            for f in facs
        ]
        return InlineKeyboardMarkup(rows)

def dept_keyboard(fac_id):
    with app_ctx():
        depts = Department.query.filter_by(faculty_id=fac_id, is_active=True).order_by(Department.name).all()
        if not depts:
            return None
        rows = [
            [InlineKeyboardButton(f"📂 {d.name}", callback_data=f"{CB_DEPT}_{d.id}")]
            for d in depts
        ]
        rows.append([InlineKeyboardButton("⏭ Skip (no specific department)", callback_data=CB_SKIP)])
        return InlineKeyboardMarkup(rows)

def lang_keyboard():
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{CB_LANG}_{code}")]
        for code, label in LANGS.items()
    ]
    return InlineKeyboardMarkup(rows)

def build_response(session, msg):
    # Logic Order: FAQ first, if not found then KB, if still not found then AI
    with app_ctx():
        uni_ctx = knowledge_service.get_university_context(session.uni_id)
        uni_obj = db.session.get(University, session.uni_id)

        faq = search_faq(msg, university=uni_obj)
        if faq.get("found") and faq.get("confidence", 0) >= FAQ_CONF:
            return faq["answer"], "faq"

        kb = knowledge_service.search_knowledge(msg, session.uni_id, faculty_id=session.fac_id, department_id=session.dept_id, limit=5)
        kb_ctx = None
        if kb:
            kb_ctx = "\n".join([f"- {r['title']}: {r['content']} | ARABIC: {r.get('content_ar', '')}" for r in kb])

        fac_ctx = None
        if session.fac_id:
            fac = db.session.get(Faculty, session.fac_id)
            if fac:
                fac_ctx = f"Faculty: {fac.name}\nArabic name: {fac.name_ar or 'N/A'}\nCode: {fac.code}\nDean: {fac.dean or 'N/A'}\nWebsite: {fac.official_website or 'N/A'}\nEmail: {fac.email or 'N/A'}\nBuilding: {fac.building or 'N/A'}"

        dept_ctx = None
        if session.dept_id:
            dept = db.session.get(Department, session.dept_id)
            if dept:
                dept_ctx = f"Department: {dept.name}\nArabic name: {dept.name_ar or 'N/A'}\nCode: {dept.code}\nEmail: {dept.email or 'N/A'}\nBuilding: {dept.building or 'N/A'}\nHead: {dept.head_of_department or 'N/A'}"

        hist = list(session.history)
        hist.append({"role": "user", "content": msg})

        resp, _ = generate_chat_response(hist, university_context=uni_ctx, knowledge_context=kb_ctx, department_context=dept_ctx, faculty_context=fac_ctx)
        return resp, "ai"

def safe_text(text):
    if len(text) <= MAX_MSG_LEN:
        return text
    return text[:MAX_MSG_LEN - 80] + "\n\n_[Message truncated. Ask for more details.]_"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    new_session(uid)

    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url:
        await update.message.reply_text("⚠️ `WEBAPP_URL` is not configured in .env file.")
        return

    markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⚙️ إعداد الملف الشخصي (اختيار الجامعة)", web_app=WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )

    name = f", {user.first_name}" if user.first_name else ""
    await update.message.reply_text(
        f"🎓 *Welcome{name}!*\n\n"
        "I'm your University Academic Assistant. I can help with:\n"
        "📚 Course registration \n💰 Tuition & payments\n"
        "📊 Grades & records\n📝 Exams & schedules\n"
        "🏢 Campus facilities\n🎫 Student services\n\n"
        "🌐 *Supports Arabic, English and French.*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "يرجى الضغط على الزر أدناه لاختيار جامعتك وكليتك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=markup,
    )
    logger.info("User %s started.", uid)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    await update.message.reply_text(
        "🤖 *University Academic Assistant — Help*\n\n"
        f"*Your current session:*\n{s.summary()}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*What I can help with:*\n"
        "📚 Course registration & enrollment\n"
        "💰 Tuition fees & payment methods\n"
        "📊 Grades, GPA & academic records\n"
        "🏢 Campus facilities & opening hours\n"
        "📝 Exam schedules & important deadlines\n"
        "🎫 Student cards & official documents\n"
        "📋 University regulations & procedures\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*Commands:*\n"
        "/start   — Setup wizard\n"
        "/change  — Change selection\n"
        "/status  — View session info\n"
        "/lang    — Set language\n"
        "/reset   — Clear session\n"
        "/help    — This message\n\n"
        "💬 Just type your question!",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    if not s.uni_id:
        await update.message.reply_text("❌ *No active session.*\n\nUse /start first.", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(
        f"📊 *Session Details*\n\n{s.card()}\n\n_/change to update  •  /reset to start fresh_",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    old = get_session(uid)
    lines = []
    if old.uni_name:
        lines.append(f"  • {old.uni_name}")
    if old.fac_name and old.fac_name != "N/A":
        lines.append(f"  • {old.fac_name}")
    if old.dept_name and old.dept_name not in (None, "N/A"):
        lines.append(f"  • {old.dept_name}")
    if old.msg_count:
        lines.append(f"  • {old.msg_count} message(s)")
    new_session(uid)
    summary = "\n".join(lines) if lines else "  (nothing)"
    await update.message.reply_text(
        f"🔄 *Session cleared.*\n\n*Previous:*\n{summary}\n\nUse /start to begin again.",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("User %s reset session.", uid)

async def cmd_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)

    hist = list(s.history)
    lang = s.lang
    count = s.msg_count

    new_session(uid)
    ns = get_session(uid)
    ns.history = hist
    ns.lang = lang
    ns.msg_count = count

    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url:
        await update.message.reply_text("⚠️ `WEBAPP_URL` is not configured in .env file.")
        return

    markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⚙️ إعداد الملف الشخصي (تغيير الجامعة)", web_app=WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🔄 *Change your selection*\n\nYour history is preserved.\nيرجى الضغط على الزر أدناه لتغيير اختياراتك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=markup,
    )

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    cur = LANGS.get(s.lang, "Auto")
    await update.message.reply_text(
        f"🌐 *Language Settings*\n\nCurrently: *{cur}*\n\nChoose preferred language.\n_Auto = respond in same language as your message._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=lang_keyboard(),
    )

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data.startswith(f"{CB_UNI}_"):
        await on_uni(q, uid, int(data.split("_", 1)[1]))
    elif data.startswith(f"{CB_FAC}_"):
        await on_fac(q, uid, int(data.split("_", 1)[1]))
    elif data.startswith(f"{CB_DEPT}_"):
        await on_dept(q, uid, int(data.split("_", 1)[1]))
    elif data == CB_SKIP:
        await on_skip(q, uid)
    elif data.startswith(f"{CB_LANG}_"):
        await on_lang(q, uid, data.split("_", 1)[1])
    else:
        await q.edit_message_text("❓ Unknown action. Use /start.")

async def on_uni(q, uid, uni_id):
    try:
        with app_ctx():
            uni = db.session.get(University, uni_id)
            if not uni or not uni.is_active:
                await q.edit_message_text("❌ University not found. /start again.")
                return
            s = get_session(uid)
            s.uni_id = uni.id
            s.uni_name = uni.name
            s.fac_id = None
            s.fac_name = None
            s.dept_id = None
            s.dept_name = None

        markup = fac_keyboard(uni_id)
        if markup is None:
            await q.edit_message_text(
                f"✅ *University:* {uni.name}\n\nNo faculties yet.\nAsk me anything! 🎓",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await q.edit_message_text(
            f"✅ *University:* {uni.name}\n\n*Step 2 of 3 — Select your faculty:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    except Exception:
        logger.exception("Error uni selection user %s", uid)
        await q.edit_message_text("❌ Error. /start again.")

async def on_fac(q, uid, fac_id):
    try:
        with app_ctx():
            fac = db.session.get(Faculty, fac_id)
            if not fac or not fac.is_active:
                await q.edit_message_text("❌ Faculty not found. /start again.")
                return
            s = get_session(uid)
            s.fac_id = fac.id
            s.fac_name = fac.name
            s.dept_id = None
            s.dept_name = None
            uni_name = s.uni_name

        markup = dept_keyboard(fac_id)
        if markup is None:
            await q.edit_message_text(
                f"✅ *University:* {uni_name}\n✅ *Faculty:* {fac.name}\n\nNo departments yet.\nAsk me anything! 🎓",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await q.edit_message_text(
            f"✅ *University:* {uni_name}\n✅ *Faculty:* {fac.name}\n\n*Step 3 of 3 — Select your department:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    except Exception:
        logger.exception("Error fac selection user %s", uid)
        await q.edit_message_text("❌ Error. /start again.")

async def on_dept(q, uid, dept_id):
    try:
        with app_ctx():
            dept = db.session.get(Department, dept_id)
            if not dept or not dept.is_active:
                await q.edit_message_text("❌ Department not found. /start again.")
                return
            s = get_session(uid)
            s.dept_id = dept.id
            s.dept_name = dept.name

        await q.edit_message_text(
            f"🎉 *Setup complete!*\n\n{s.card()}\n\nJust type your question!\n\n_/status • /change • /lang_",
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info("User %s setup done: uni=%s fac=%s dept=%s", uid, s.uni_id, s.fac_id, s.dept_id)
    except Exception:
        logger.exception("Error dept selection user %s", uid)
        await q.edit_message_text("❌ Error. /start again.")

async def on_skip(q, uid):
    s = get_session(uid)
    s.dept_id = None
    s.dept_name = None
    await q.edit_message_text(
        f"✅ *Setup complete!*\n\n{s.card()}\n\nJust type your question!\n\n_/status • /change • /lang_",
        parse_mode=ParseMode.MARKDOWN,
    )

async def on_lang(q, uid, code):
    if code not in LANGS:
        await q.edit_message_text("❓ Unknown language.")
        return
    s = get_session(uid)
    s.lang = code
    await q.edit_message_text(
        f"✅ Language set to *{LANGS[code]}*\n\n_Use /lang to change anytime._",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("User %s lang set to %s", uid, code)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data_str = update.message.web_app_data.data
    try:
        data = json.loads(data_str)
        uni_id = data.get("uni_id")
        fac_id = data.get("fac_id")
        dept_id = data.get("dept_id")

        with app_ctx():
            uni = db.session.get(University, uni_id) if uni_id else None
            fac = db.session.get(Faculty, fac_id) if fac_id else None
            dept = db.session.get(Department, dept_id) if dept_id else None

            if not uni:
                await update.message.reply_text("❌ University not found. /start again.")
                return

            s = get_session(uid)
            s.uni_id = uni.id
            s.uni_name = uni.name
            s.fac_id = fac.id if fac else None
            s.fac_name = fac.name if fac else None
            s.dept_id = dept.id if dept else None
            s.dept_name = dept.name if dept else None

        await update.message.reply_text(
            f"🎉 *Setup complete!*\n\n{s.card()}\n\nJust type your question!\n\n_/status • /change • /lang_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info("User %s setup via webapp: uni=%s fac=%s dept=%s", uid, s.uni_id, s.fac_id, s.dept_id)
    except Exception:
        logger.exception("Error handling webapp data for %s", uid)
        await update.message.reply_text("❌ Error processing your selection.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text.strip()
    s = get_session(uid)

    if not s.ready:
        await update.message.reply_text(
            "⚠️ *Profile not complete.*\n\nUse /start first.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        resp, src = build_response(s, msg)
        s.add_turn(msg, resp)
        await update.message.reply_text(safe_text(resp), parse_mode=ParseMode.MARKDOWN)
        logger.info("Sent | user=%s src=%s count=%d", uid, src, s.msg_count)
    except Exception:
        logger.exception("Pipeline error user %s", uid)
        await update.message.reply_text(
            "❌ Something went wrong.\nTry again or /reset if it keeps happening."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error: %s", context.error, exc_info=context.error)

def run_bot(app=None):
    global flask_app
    if app is not None:
        flask_app = app

    if flask_app is None:
        raise RuntimeError("Flask app not set. Pass app= to run_bot()")

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN missing — bot cannot start.")
        return

    import ssl
    import certifi
    from telegram.request import HTTPXRequest

    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    req = HTTPXRequest(
        connection_pool_size=8,
        http_version="1.1",
        connect_timeout=60.0,
        read_timeout=60.0,
    )

    tg = Application.builder().token(BOT_TOKEN).request(req).build()

    tg.add_handler(CommandHandler("start", cmd_start))
    tg.add_handler(CommandHandler("help", cmd_help))
    tg.add_handler(CommandHandler("status", cmd_status))
    tg.add_handler(CommandHandler("reset", cmd_reset))
    tg.add_handler(CommandHandler("change", cmd_change))
    tg.add_handler(CommandHandler("lang", cmd_lang))
    tg.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    tg.add_handler(CallbackQueryHandler(callback_router))
    tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    tg.add_error_handler(error_handler)

    logger.info("Bot started, waiting for messages...")
    tg.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    from app import app as flask_app
    run_bot(app=flask_app)

if __name__ == "__main__":
    main()
