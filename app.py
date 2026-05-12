from dotenv import load_dotenv
load_dotenv()
import os
import logging
from flask import Flask, render_template, jsonify
from config import get_config
from extensions import db, limiter, csrf

# Create app
def create_app(config_class=None):
    app = Flask(__name__)

    cfg = config_class or get_config()
    app.config.from_object(cfg)
    cfg.configure_logging()

    log = logging.getLogger(__name__)

    db.init_app(app)

    csrf.init_app(app)

    from routes.auth import auth_bp
    from routes.chat import chat_bp
    from routes.admin import admin_bp
    from routes.webapp import webapp_bp

    # Must be CSRF exempt, otherwise external POST requests will fail
    csrf.exempt(auth_bp)
    csrf.exempt(chat_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(webapp_bp)

    limiter._storage_uri = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    limiter.init_app(app)

    if app.config.get('RATELIMIT_ENABLED') is False or app.config.get('TESTING'):
        app.config['RATELIMIT_ENABLED'] = False

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(webapp_bp, url_prefix='/webapp')

    @app.after_request
    def add_security_headers(resp):
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        # Telegram Web Apps need to be displayed in an iframe
        from flask import request
        if not request.path.startswith('/webapp'):
            resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
        resp.headers['X-XSS-Protection'] = '1; mode=block'
        resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if app.config.get('SESSION_COOKIE_SECURE'):
            resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return resp

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({'error': 'Too many requests. Please slow down.'}), 429

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        log.error('500 error: ' + str(error), exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.route('/')
    def index():
        return render_template('landing.html')

    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'ok',
        }), 200

    with app.app_context():
        db.create_all()
        log.info('Database tables ready.')

        # Auto-sync seed data on every startup
        from sync_data import sync_all
        sync_all()

        # Reload FAQs from the updated JSON file
        from services.faq_service import faq_matcher, load_faqs
        faq_matcher.faqs = load_faqs()
        log.info(f'FAQs reloaded: {len(faq_matcher.faqs)} entries')

    return app
    
app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000)