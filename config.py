import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment Configs
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
MUSIC_DIR = os.getenv("MUSIC_DIR", "C:/Users/Public/Music")
WHATSAPP_LAUNCH_DELAY = float(os.getenv("WHATSAPP_LAUNCH_DELAY", "2.5"))
SEARCH_DELAY = float(os.getenv("SEARCH_DELAY", "1.5"))