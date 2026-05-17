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
    "ar": "العربية",
    "en": "English",
    "fr": "Français",
}

TEXTS = {
    "ar": {
        "choose_lang": "مرحبا!\nيرجى اختيار اللغة المفضلة للمتابعة:",
        "welcome": "مرحبا{name}!\n\nانا المساعد الاكاديمي الجامعي. يمكنني مساعدتك في:\n- التسجيل والقبول\n- الرسوم والمدفوعات\n- النتائج والسجلات الاكاديمية\n- الامتحانات والجداول الزمنية\n- المرافق الجامعية\n- الخدمات الطلابية\n\nيدعم النظام العربية والانجليزية والفرنسية.\n\nيرجى الضغط على الزر ادناه لاختيار جامعتك وكليتك.",
        "setup_btn": "اعداد الملف الشخصي",
        "change_btn": "تغيير الاختيارات",
        "help_title": "المساعد الاكاديمي الجامعي - المساعدة",
        "session_info": "معلومات الجلسة الحالية:",
        "help_topics": "المواضيع المتاحة:\n- التسجيل والقبول\n- الرسوم والمدفوعات\n- النتائج والمعدل التراكمي\n- المرافق الجامعية\n- الامتحانات والمواعيد\n- البطاقة الطلابية والوثائق\n- اللوائح والاجراءات",
        "commands": "الاوامر:\n/start - بدء الاعداد\n/change - تغيير الاختيار\n/status - عرض معلومات الجلسة\n/lang - تغيير اللغة\n/reset - مسح الجلسة\n/help - هذه الرسالة",
        "ask_hint": "اكتب سؤالك مباشرة.",
        "no_session": "لا توجد جلسة نشطة. استخدم /start اولا.",
        "status_title": "تفاصيل الجلسة",
        "reset_done": "تم مسح الجلسة.",
        "previous": "السابق:",
        "nothing": "(لا شيء)",
        "messages_count": "رسالة/رسائل",
        "use_start": "استخدم /start للبدء من جديد.",
        "change_title": "تغيير الاختيار",
        "history_kept": "تم الاحتفاظ بسجل المحادثة.",
        "change_hint": "يرجى الضغط على الزر ادناه لتغيير اختياراتك.",
        "lang_title": "اعدادات اللغة",
        "lang_current": "الحالية:",
        "lang_choose": "اختر اللغة المفضلة:",
        "lang_set": "تم تعيين اللغة الى: {lang}",
        "lang_change_hint": "استخدم /lang للتغيير في اي وقت.",
        "uni_not_found": "الجامعة غير موجودة. استخدم /start مجددا.",
        "fac_not_found": "الكلية غير موجودة. استخدم /start مجددا.",
        "dept_not_found": "القسم غير موجود. استخدم /start مجددا.",
        "setup_complete": "تم الاعداد بنجاح.",
        "no_faculties": "لا توجد كليات مسجلة حاليا.",
        "step_2": "الخطوة 2 من 3 - اختر كليتك:",
        "step_3": "الخطوة 3 من 3 - اختر قسمك:",
        "profile_incomplete": "الملف الشخصي غير مكتمل. استخدم /start اولا.",
        "error_occurred": "حدث خطا. حاول مجددا او استخدم /reset.",
        "error_generic": "حدث خطا. استخدم /start مجددا.",
        "webapp_error": "WEBAPP_URL غير مهيأ.",
        "unknown_action": "اجراء غير معروف. استخدم /start.",
        "unknown_lang": "لغة غير معروفة.",
        "error_selection": "حدث خطا في معالجة الاختيار.",
        "university": "الجامعة",
        "faculty": "الكلية",
        "department": "القسم",
        "language": "اللغة",
        "duration": "المدة",
        "exchanges": "المحادثات",
        "min": "دقيقة",
        "not_selected": "غير محدد",
        "skip": "تخطي (بدون قسم محدد)",
        "confirm_btn": "تاكيد الاختيار",
        "webapp_title": "اعداد الملف الشخصي",
        "webapp_subtitle": "الرجاء اختيار جامعتك وكليتك للمتابعة",
        "select_uni": "يرجى اختيار الجامعة",
        "select_fac": "يرجى اختيار الكلية",
        "no_fac_registered": "لا توجد كليات مسجلة",
        "skip_dept": "تخطي (بدون قسم محدد)",
        "loading": "جاري التحميل...",
        "load_error": "حدث خطا في التحميل",
        "dept_label": "القسم (اختياري):",
        "welcome_back": "مرحبا مجددا{name}!\n\nجلستك الحالية:\n{card}\n\nاكتب سؤالك مباشرة.\n\n_/change لتغيير الاختيارات | /reset للبدء من جديد_",
    },
    "en": {
        "choose_lang": "Hello!\nPlease choose your preferred language to continue:",
        "welcome": "Hello{name}!\n\nI am your University Academic Assistant. I can help you with:\n- Registration and admissions\n- Tuition and payments\n- Grades and academic records\n- Exams and schedules\n- Campus facilities\n- Student services\n\nThe system supports Arabic, English and French.\n\nPlease press the button below to select your university and faculty.",
        "setup_btn": "Setup Profile",
        "change_btn": "Change Selection",
        "help_title": "University Academic Assistant - Help",
        "session_info": "Current session information:",
        "help_topics": "Available topics:\n- Registration and enrollment\n- Tuition fees and payments\n- Grades and GPA\n- Campus facilities\n- Exams and deadlines\n- Student cards and documents\n- Regulations and procedures",
        "commands": "Commands:\n/start - Setup wizard\n/change - Change selection\n/status - View session info\n/lang - Set language\n/reset - Clear session\n/help - This message",
        "ask_hint": "Just type your question.",
        "no_session": "No active session. Use /start first.",
        "status_title": "Session Details",
        "reset_done": "Session cleared.",
        "previous": "Previous:",
        "nothing": "(nothing)",
        "messages_count": "message(s)",
        "use_start": "Use /start to begin again.",
        "change_title": "Change Selection",
        "history_kept": "Your conversation history is preserved.",
        "change_hint": "Please press the button below to change your selection.",
        "lang_title": "Language Settings",
        "lang_current": "Currently:",
        "lang_choose": "Choose your preferred language:",
        "lang_set": "Language set to: {lang}",
        "lang_change_hint": "Use /lang to change anytime.",
        "uni_not_found": "University not found. Use /start again.",
        "fac_not_found": "Faculty not found. Use /start again.",
        "dept_not_found": "Department not found. Use /start again.",
        "setup_complete": "Setup complete.",
        "no_faculties": "No faculties registered yet.",
        "step_2": "Step 2 of 3 - Select your faculty:",
        "step_3": "Step 3 of 3 - Select your department:",
        "profile_incomplete": "Profile not complete. Use /start first.",
        "error_occurred": "Something went wrong. Try again or use /reset.",
        "error_generic": "Error. Use /start again.",
        "webapp_error": "WEBAPP_URL is not configured.",
        "unknown_action": "Unknown action. Use /start.",
        "unknown_lang": "Unknown language.",
        "error_selection": "Error processing your selection.",
        "university": "University",
        "faculty": "Faculty",
        "department": "Department",
        "language": "Language",
        "duration": "Duration",
        "exchanges": "Exchanges",
        "min": "min",
        "not_selected": "Not selected",
        "skip": "Skip (no specific department)",
        "confirm_btn": "Confirm Selection",
        "webapp_title": "Profile Setup",
        "webapp_subtitle": "Please select your university and faculty to continue",
        "select_uni": "Please select a university",
        "select_fac": "Please select a faculty",
        "no_fac_registered": "No faculties registered",
        "skip_dept": "Skip (no specific department)",
        "loading": "Loading...",
        "load_error": "Error loading data",
        "dept_label": "Department (optional):",
        "welcome_back": "Welcome back{name}!\n\nYour current session:\n{card}\n\nJust type your question.\n\n_/change to update | /reset to start fresh_",
    },
    "fr": {
        "choose_lang": "Bonjour!\nVeuillez choisir votre langue preferee pour continuer:",
        "welcome": "Bonjour{name}!\n\nJe suis votre Assistant Academique Universitaire. Je peux vous aider avec:\n- Inscription et admissions\n- Frais de scolarite et paiements\n- Notes et dossiers academiques\n- Examens et emplois du temps\n- Installations du campus\n- Services etudiants\n\nLe systeme supporte l'arabe, l'anglais et le francais.\n\nVeuillez appuyer sur le bouton ci-dessous pour selectionner votre universite et faculte.",
        "setup_btn": "Configurer le profil",
        "change_btn": "Modifier la selection",
        "help_title": "Assistant Academique Universitaire - Aide",
        "session_info": "Informations de la session actuelle:",
        "help_topics": "Sujets disponibles:\n- Inscription et admission\n- Frais de scolarite et paiements\n- Notes et moyenne generale\n- Installations du campus\n- Examens et dates limites\n- Cartes etudiantes et documents\n- Reglements et procedures",
        "commands": "Commandes:\n/start - Assistant de configuration\n/change - Modifier la selection\n/status - Voir les infos de session\n/lang - Definir la langue\n/reset - Effacer la session\n/help - Ce message",
        "ask_hint": "Tapez votre question directement.",
        "no_session": "Aucune session active. Utilisez /start d'abord.",
        "status_title": "Details de la session",
        "reset_done": "Session effacee.",
        "previous": "Precedent:",
        "nothing": "(rien)",
        "messages_count": "message(s)",
        "use_start": "Utilisez /start pour recommencer.",
        "change_title": "Modifier la selection",
        "history_kept": "L'historique de conversation est conserve.",
        "change_hint": "Veuillez appuyer sur le bouton ci-dessous pour modifier votre selection.",
        "lang_title": "Parametres de langue",
        "lang_current": "Actuelle:",
        "lang_choose": "Choisissez votre langue preferee:",
        "lang_set": "Langue definie sur: {lang}",
        "lang_change_hint": "Utilisez /lang pour changer a tout moment.",
        "uni_not_found": "Universite non trouvee. Utilisez /start a nouveau.",
        "fac_not_found": "Faculte non trouvee. Utilisez /start a nouveau.",
        "dept_not_found": "Departement non trouve. Utilisez /start a nouveau.",
        "setup_complete": "Configuration terminee.",
        "no_faculties": "Aucune faculte enregistree pour le moment.",
        "step_2": "Etape 2 sur 3 - Selectionnez votre faculte:",
        "step_3": "Etape 3 sur 3 - Selectionnez votre departement:",
        "profile_incomplete": "Profil incomplet. Utilisez /start d'abord.",
        "error_occurred": "Une erreur s'est produite. Reessayez ou utilisez /reset.",
        "error_generic": "Erreur. Utilisez /start a nouveau.",
        "webapp_error": "WEBAPP_URL n'est pas configure.",
        "unknown_action": "Action inconnue. Utilisez /start.",
        "unknown_lang": "Langue inconnue.",
        "error_selection": "Erreur lors du traitement de votre selection.",
        "university": "Universite",
        "faculty": "Faculte",
        "department": "Departement",
        "language": "Langue",
        "duration": "Duree",
        "exchanges": "Echanges",
        "min": "min",
        "not_selected": "Non selectionne",
        "skip": "Passer (pas de departement specifique)",
        "confirm_btn": "Confirmer la selection",
        "webapp_title": "Configuration du profil",
        "webapp_subtitle": "Veuillez selectionner votre universite et faculte pour continuer",
        "select_uni": "Veuillez selectionner une universite",
        "select_fac": "Veuillez selectionner une faculte",
        "no_fac_registered": "Aucune faculte enregistree",
        "skip_dept": "Passer (pas de departement specifique)",
        "loading": "Chargement...",
        "load_error": "Erreur de chargement",
        "dept_label": "Departement (optionnel):",
        "welcome_back": "Bon retour{name}!\n\nVotre session actuelle:\n{card}\n\nTapez votre question directement.\n\n_/change pour modifier | /reset pour recommencer_",
    },
}

def t(lang, key):
    return TEXTS.get(lang, TEXTS["ar"]).get(key, TEXTS["ar"].get(key, key))

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
    lang: str = None
    history: list = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    last_msg: datetime = field(default_factory=datetime.now)
    msg_count: int = 0

    @property
    def ready(self):
        return bool(self.uni_id and self.fac_id)

    @property
    def lang_ready(self):
        return self.lang is not None and self.lang in LANGS

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

    def _t(self, key):
        return t(self.lang or "ar", key)

    def summary(self):
        L = self.lang or "ar"
        parts = []
        if self.uni_name:
            parts.append(t(L, "university") + " : " + self.uni_name)
        if self.fac_name:
            parts.append(t(L, "faculty") + " : " + self.fac_name)
        if self.dept_name:
            parts.append(t(L, "department") + " : " + self.dept_name)
        parts.append(t(L, "language") + " : " + LANGS.get(self.lang, "—"))
        return "\n".join(parts) if parts else t(L, "no_session")

    def card(self):
        L = self.lang or "ar"
        ns = t(L, "not_selected")
        return (
            "*" + t(L, "university") + "*  : " + (self.uni_name or "—") + "\n"
            "*" + t(L, "faculty") + "*  : " + (self.fac_name or ns) + "\n"
            "*" + t(L, "department") + "*  : " + (self.dept_name or ns) + "\n"
            "*" + t(L, "language") + "*  : " + LANGS.get(self.lang, "—") + "\n"
            "*" + t(L, "duration") + "*  : " + str(self.minutes) + " " + t(L, "min") + "\n"
            "*" + t(L, "exchanges") + "*  : " + str(self.msg_count)
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
                u.name + (f"  ({u.city})" if u.city else ""),
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
            [InlineKeyboardButton(f.name, callback_data=f"{CB_FAC}_{f.id}")]
            for f in facs
        ]
        return InlineKeyboardMarkup(rows)

def dept_keyboard(fac_id, lang="ar"):
    with app_ctx():
        depts = Department.query.filter_by(faculty_id=fac_id, is_active=True).order_by(Department.name).all()
        if not depts:
            return None
        rows = [
            [InlineKeyboardButton(d.name, callback_data=f"{CB_DEPT}_{d.id}")]
            for d in depts
        ]
        rows.append([InlineKeyboardButton(t(lang, "skip"), callback_data=CB_SKIP)])
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
    s = get_session(uid)

    # If user already has a complete session, welcome them back
    if s.lang_ready and s.ready:
        L = s.lang
        name = f", {user.first_name}" if user.first_name else ""
        text = t(L, "welcome_back").format(name=name, card=s.card())

        webapp_url = os.getenv("WEBAPP_URL")
        if webapp_url:
            separator = "&" if "?" in webapp_url else "?"
            webapp_url_with_lang = f"{webapp_url}{separator}lang={L}"
            markup = ReplyKeyboardMarkup(
                [[KeyboardButton(t(L, "change_btn"), web_app=WebAppInfo(url=webapp_url_with_lang))]],
                resize_keyboard=True
            )
        else:
            markup = ReplyKeyboardRemove()

        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
        logger.info("User %s returned with active session.", uid)
        return

    # New user or incomplete session - start fresh
    new_session(uid)

    # First step: language selection
    await update.message.reply_text(
        "*EduVerse AI*\n\n"
        "مرحبا / Hello / Bonjour\n\n"
        "يرجى اختيار اللغة المفضلة:\n"
        "Please choose your preferred language:\n"
        "Veuillez choisir votre langue preferee:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=lang_keyboard(),
    )
    logger.info("User %s started - awaiting language selection.", uid)

async def _send_welcome(update_or_query, uid, is_callback=False):
    """Send the welcome message with webapp button after language is selected."""
    s = get_session(uid)
    L = s.lang or "ar"

    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url:
        msg = t(L, "webapp_error")
        if is_callback:
            await update_or_query.edit_message_text(msg)
        else:
            await update_or_query.message.reply_text(msg)
        return

    # Append lang parameter to webapp URL
    separator = "&" if "?" in webapp_url else "?"
    webapp_url_with_lang = f"{webapp_url}{separator}lang={L}"

    markup = ReplyKeyboardMarkup(
        [[KeyboardButton(t(L, "setup_btn"), web_app=WebAppInfo(url=webapp_url_with_lang))]],
        resize_keyboard=True
    )

    user = None
    if is_callback:
        user = update_or_query.from_user
    else:
        user = update_or_query.effective_user

    name = f", {user.first_name}" if user.first_name else ""
    text = t(L, "welcome").format(name=name)

    if is_callback:
        await update_or_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        # Send a separate message with the reply keyboard
        chat_id = update_or_query.message.chat_id
        from telegram import Bot
        bot = update_or_query.get_bot()
        await bot.send_message(
            chat_id=chat_id,
            text=t(L, "ask_hint"),
            reply_markup=markup,
        )
    else:
        await update_or_query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    logger.info("User %s welcomed with lang=%s.", uid, L)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    L = s.lang or "ar"
    await update.message.reply_text(
        f"*{t(L, 'help_title')}*\n\n"
        f"*{t(L, 'session_info')}*\n{s.summary()}\n\n"
        f"*{t(L, 'help_topics')}*\n\n"
        f"*{t(L, 'commands')}*\n\n"
        f"{t(L, 'ask_hint')}",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    L = s.lang or "ar"
    if not s.uni_id:
        await update.message.reply_text(
            f"*{t(L, 'no_session')}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    await update.message.reply_text(
        f"*{t(L, 'status_title')}*\n\n{s.card()}\n\n_/change  |  /reset_",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    old = get_session(uid)
    L = old.lang or "ar"
    lines = []
    if old.uni_name:
        lines.append(f"  - {old.uni_name}")
    if old.fac_name and old.fac_name != "N/A":
        lines.append(f"  - {old.fac_name}")
    if old.dept_name and old.dept_name not in (None, "N/A"):
        lines.append(f"  - {old.dept_name}")
    if old.msg_count:
        lines.append(f"  - {old.msg_count} {t(L, 'messages_count')}")
    new_session(uid)
    summary = "\n".join(lines) if lines else f"  {t(L, 'nothing')}"
    await update.message.reply_text(
        f"*{t(L, 'reset_done')}*\n\n*{t(L, 'previous')}*\n{summary}\n\n{t(L, 'use_start')}",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("User %s reset session.", uid)

async def cmd_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    L = s.lang or "ar"

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
        await update.message.reply_text(t(L, "webapp_error"))
        return

    separator = "&" if "?" in webapp_url else "?"
    webapp_url_with_lang = f"{webapp_url}{separator}lang={L}"

    markup = ReplyKeyboardMarkup(
        [[KeyboardButton(t(L, "change_btn"), web_app=WebAppInfo(url=webapp_url_with_lang))]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        f"*{t(L, 'change_title')}*\n\n{t(L, 'history_kept')}\n{t(L, 'change_hint')}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=markup,
    )

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = get_session(uid)
    L = s.lang or "ar"
    cur = LANGS.get(s.lang, "—")
    await update.message.reply_text(
        f"*{t(L, 'lang_title')}*\n\n{t(L, 'lang_current')} *{cur}*\n\n{t(L, 'lang_choose')}",
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
        await q.edit_message_text(t(get_session(uid).lang or "ar", "unknown_action"))

async def on_uni(q, uid, uni_id):
    s = get_session(uid)
    L = s.lang or "ar"
    try:
        with app_ctx():
            uni = db.session.get(University, uni_id)
            if not uni or not uni.is_active:
                await q.edit_message_text(t(L, "uni_not_found"))
                return
            s.uni_id = uni.id
            s.uni_name = uni.name
            s.fac_id = None
            s.fac_name = None
            s.dept_id = None
            s.dept_name = None

        markup = fac_keyboard(uni_id)
        if markup is None:
            await q.edit_message_text(
                f"*{t(L, 'university')}:* {uni.name}\n\n{t(L, 'no_faculties')}\n{t(L, 'ask_hint')}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await q.edit_message_text(
            f"*{t(L, 'university')}:* {uni.name}\n\n*{t(L, 'step_2')}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    except Exception:
        logger.exception("Error uni selection user %s", uid)
        await q.edit_message_text(t(L, "error_generic"))

async def on_fac(q, uid, fac_id):
    s = get_session(uid)
    L = s.lang or "ar"
    try:
        with app_ctx():
            fac = db.session.get(Faculty, fac_id)
            if not fac or not fac.is_active:
                await q.edit_message_text(t(L, "fac_not_found"))
                return
            s.fac_id = fac.id
            s.fac_name = fac.name
            s.dept_id = None
            s.dept_name = None
            uni_name = s.uni_name

        markup = dept_keyboard(fac_id, lang=L)
        if markup is None:
            await q.edit_message_text(
                f"*{t(L, 'university')}:* {uni_name}\n*{t(L, 'faculty')}:* {fac.name}\n\n{t(L, 'no_faculties')}\n{t(L, 'ask_hint')}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await q.edit_message_text(
            f"*{t(L, 'university')}:* {uni_name}\n*{t(L, 'faculty')}:* {fac.name}\n\n*{t(L, 'step_3')}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    except Exception:
        logger.exception("Error fac selection user %s", uid)
        await q.edit_message_text(t(L, "error_generic"))

async def on_dept(q, uid, dept_id):
    s = get_session(uid)
    L = s.lang or "ar"
    try:
        with app_ctx():
            dept = db.session.get(Department, dept_id)
            if not dept or not dept.is_active:
                await q.edit_message_text(t(L, "dept_not_found"))
                return
            s.dept_id = dept.id
            s.dept_name = dept.name

        await q.edit_message_text(
            f"*{t(L, 'setup_complete')}*\n\n{s.card()}\n\n{t(L, 'ask_hint')}\n\n_/status | /change | /lang_",
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info("User %s setup done: uni=%s fac=%s dept=%s", uid, s.uni_id, s.fac_id, s.dept_id)
    except Exception:
        logger.exception("Error dept selection user %s", uid)
        await q.edit_message_text(t(L, "error_generic"))

async def on_skip(q, uid):
    s = get_session(uid)
    L = s.lang or "ar"
    s.dept_id = None
    s.dept_name = None
    await q.edit_message_text(
        f"*{t(L, 'setup_complete')}*\n\n{s.card()}\n\n{t(L, 'ask_hint')}\n\n_/status | /change | /lang_",
        parse_mode=ParseMode.MARKDOWN,
    )

async def on_lang(q, uid, code):
    if code not in LANGS:
        await q.edit_message_text(t("ar", "unknown_lang"))
        return
    s = get_session(uid)
    first_time = s.lang is None
    s.lang = code
    logger.info("User %s lang set to %s", uid, code)

    if first_time:
        # First time selecting language during /start flow - send welcome
        await _send_welcome(q, uid, is_callback=True)
    else:
        await q.edit_message_text(
            t(code, "lang_set").format(lang=LANGS[code]) + "\n\n_" + t(code, "lang_change_hint") + "_",
            parse_mode=ParseMode.MARKDOWN,
        )

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

            s = get_session(uid)
            L = s.lang or "ar"

            if not uni:
                await update.message.reply_text(t(L, "uni_not_found"))
                return

            s.uni_id = uni.id
            s.uni_name = uni.name
            s.fac_id = fac.id if fac else None
            s.fac_name = fac.name if fac else None
            s.dept_id = dept.id if dept else None
            s.dept_name = dept.name if dept else None

        await update.message.reply_text(
            f"*{t(L, 'setup_complete')}*\n\n{s.card()}\n\n{t(L, 'ask_hint')}\n\n_/status | /change | /lang_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info("User %s setup via webapp: uni=%s fac=%s dept=%s", uid, s.uni_id, s.fac_id, s.dept_id)
    except Exception:
        logger.exception("Error handling webapp data for %s", uid)
        await update.message.reply_text(t(get_session(uid).lang or "ar", "error_selection"))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text.strip()
    s = get_session(uid)
    L = s.lang or "ar"

    if not s.lang_ready:
        await update.message.reply_text(
            "*EduVerse AI*\n\n"
            "مرحبا / Hello / Bonjour\n\n"
            "يرجى اختيار اللغة المفضلة:\n"
            "Please choose your preferred language:\n"
            "Veuillez choisir votre langue preferee:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=lang_keyboard(),
        )
        return

    if not s.ready:
        await update.message.reply_text(
            f"*{t(L, 'profile_incomplete')}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        resp, src = build_response(s, msg)
        s.add_turn(msg, resp)
        
        # Clean markdown to avoid Telegram ParseMode.MARKDOWN errors
        clean_resp = resp.replace('**', '*')
        clean_resp = clean_resp.replace('\n* ', '\n- ')
        clean_resp = clean_resp.replace(' * ', ' - ')
        
        try:
            await update.message.reply_text(safe_text(clean_resp), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Markdown parsing failed, falling back to plain text: {e}")
            await update.message.reply_text(safe_text(resp))
            
        logger.info("Sent | user=%s src=%s count=%d", uid, src, s.msg_count)
    except Exception:
        logger.exception("Pipeline error user %s", uid)
        await update.message.reply_text(t(L, "error_occurred"))

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
