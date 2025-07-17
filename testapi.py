from dotenv import load_dotenv
load_dotenv()
import os
print("GOOGLE_REDIRECT_URI:", os.getenv("GOOGLE_REDIRECT_URI"))