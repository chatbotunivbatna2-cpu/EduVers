from flask import url_for, current_app
import requests
import logging

logger = logging.getLogger(__name__)

def send_verification_email(user):
    verification_url = url_for('auth.verify_email', token=user.verification_token, _external=True)

    subject = 'Verify Your EduVerse AI Account'

    display_name = user.full_name
    if not display_name:
        display_name = user.username

    html_body = """
    <!DOCTYPE html>
    <html dir="ltr">
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
                line-height: 1.6; 
                color: #0F172A; 
                background-color: #F8FAFC;
                margin: 0;
                padding: 0;
            }
            .wrapper {
                background-color: #F8FAFC;
                padding: 40px 20px;
            }
            .container { 
                max-width: 600px; 
                margin: 0 auto; 
                background: #ffffff;
                border-radius: 24px;
                overflow: hidden;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            }
            .header { 
                background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%); 
                padding: 50px 40px; 
                text-align: center; 
            }
            .header h1 {
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.02em;
            }
            .content { 
                padding: 45px 40px; 
                background: #ffffff;
            }
            .content p {
                margin-bottom: 20px;
                font-size: 16px;
                color: #475569;
            }
            .button-container {
                text-align: center;
                margin: 35px 0;
            }
            .button { 
                display: inline-block; 
                padding: 16px 36px; 
                background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%); 
                color: #ffffff !important; 
                text-decoration: none; 
                border-radius: 14px; 
                font-weight: 700; 
                font-size: 16px;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
                transition: transform 0.2s ease;
            }
            .link-box {
                background: #F1F5F9;
                padding: 15px;
                border-radius: 12px;
                word-break: break-all;
                font-size: 13px;
                color: #2563EB;
                border: 1px solid #E2E8F0;
            }
            .footer { 
                text-align: center; 
                padding: 30px; 
                color: #94A3B8; 
                font-size: 13px; 
            }
            .divider {
                height: 1px;
                background: #E2E8F0;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="header">
                    <h1>Welcome to EduVerse AI</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>""" + display_name + """</strong>,</p>
                    <p>Welcome to EduVerse AI Chatbot! We're excited to have you join our academic community. To get started, please verify your email address by clicking the button below:</p>
                    
                    <div class="button-container">
                        <a href=\"""" + verification_url + """\" class="button">Verify My Account</a>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <p style="font-size: 14px;">If the button doesn't work, you can also copy and paste this link into your browser:</p>
                    <div class="link-box">""" + verification_url + """</div>
                    
                    <p style="margin-top: 25px; font-size: 14px; color: #94A3B8;">If you didn't create an account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 EduVerse AI. All rights reserved.<br>Empowering education through AI.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": current_app.config['BREVO_API_KEY'],
            "content-type": "application/json"
        }
        payload = {
            "sender": {
                "name": current_app.config.get('BREVO_SENDER_NAME', 'EduVerse AI Chatbot'),
                "email": current_app.config['BREVO_SENDER_EMAIL']
            },
            "to": [
                {
                    "email": user.email,
                    "name": display_name
                }
            ],
            "subject": subject,
            "htmlContent": html_body
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to send verification email: " + str(e))
        return False
