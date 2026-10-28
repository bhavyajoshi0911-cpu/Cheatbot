import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    DEBUG = True
    DATABASE = BASE_DIR / 'database' / 'cheatbot.db'
    BASE_URL = 'http://127.0.0.1:5000'
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini').lower()
    LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-3.6-flash')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LLM_API_KEY = os.getenv('LLM_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
    ALLOWED_APPLICATIONS = {
        'vscode': r'C:\Users\DELL\AppData\Local\Programs\Microsoft VS Code\Code.exe',
        'code': r'C:\Users\DELL\AppData\Local\Programs\Microsoft VS Code\Code.exe',
        'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'notepad': r'C:\Windows\System32\notepad.exe',
        'calculator': r'C:\Windows\System32\calc.exe',
        'terminal': r'C:\Windows\System32\cmd.exe',
    }
    APP_ICON = '💻'
