import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'changeme123'
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email
    MAIL_SERVER = os.getenv('EMAIL_SMTP')
    MAIL_PORT = int(os.getenv('EMAIL_PORT', 25))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('EMAIL_USER')
    MAIL_PASSWORD = os.getenv('EMAIL_PASS')
    NOTIFY_EMAIL = os.getenv('NOTIFY_EMAIL')

    # Telegram
    TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
    TG_CHAT_ID = os.getenv('TG_CHAT_ID')

    # Case settings
    CASE_DUE_NOTIFY_DAYS = int(os.getenv('CASE_DUE_NOTIFY_DAYS', 3))
