import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "a_default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "a_default_refresh_secret_key")
REFRESH_TOKEN_EXPIRE_DAYS = 7


# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI must be set in environment variables.") 

ZEPTOMAIL_API_KEY = os.getenv("ZEPTOMAIL_API_KEY")
ZEPTOMAIL_DOMAIN = os.getenv("ZEPTOMAIL_DOMAIN")  # Your verified domain in ZeptoMail
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@yourdomain.com")  # Must be from verified domain
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Chaat App")


SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.zoho.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

EMAIL_VERIFICATION_EXPIRE_HOURS = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

USE_ZEPTOMAIL = os.getenv("USE_ZEPTOMAIL", "true").lower() == "true"

if USE_ZEPTOMAIL:
    if not ZEPTOMAIL_API_KEY:
        print("Warning: ZEPTOMAIL_API_KEY not configured. Email features will be disabled.")
else:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Warning: SMTP credentials not configured. Email features will be disabled.") 

