import json
import re
import ollama
from config import OLLAMA_MODEL

def clean_repeated_speech(text: str) -> str:
    """Cleans up accidentally repeated words or phrases if the user says something multiple times."""
    if not text:
        return ""
    
    words = text.split()
    if len(words) >= 4:
        mid = len(words) // 2
        first_half = " ".join(words[:mid])
        second_half = " ".join(words[mid:])
        if first_half.lower() == second_half.lower():
            return first_half
            
    return text

def parse_llm_json(content: str) -> dict:
    """Robustly extracts and parses JSON from Ollama output, handling markdown fences and surrounding text."""
    try:
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{") and part.endswith("}"):
                    content = part
                    break
        
        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            content = match.group(0)

        return json.loads(content)
    except Exception:
        return {}

SYSTEM_PROMPT = (
    "Your name is SPARKY, a direct, witty, efficient, and loyal AI desktop assistant inspired by JARVIS. "
    "Always address the user as 'Boss'. "
    "Keep responses concise (1-2 sentences) so they sound natural when spoken."
)

# Maintain in-memory chat session context initialized with SPARKY persona
CHAT_HISTORY = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

def chat_with_llm(user_input: str) -> str:
    """Fallback handler for general conversation with multi-turn memory context."""
    global CHAT_HISTORY
    try:
        # Append user message to active history
        CHAT_HISTORY.append({"role": "user", "content": user_input})
        
        # Keep sliding context window to avoid memory bloat (System prompt + last 10 messages)
        if len(CHAT_HISTORY) > 11:
            CHAT_HISTORY = [CHAT_HISTORY[0]] + CHAT_HISTORY[-10:]

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=CHAT_HISTORY
        )
        
        reply = response['message']['content'].strip()
        # Append assistant response to history
        CHAT_HISTORY.append({"role": "assistant", "content": reply})
        return reply

    except Exception as e:
        return f"Apologies Boss, I encountered an issue processing that: {e}"

def generate_contextual_message(contact_name: str, original_command: str) -> str:
    """Polishes raw spoken intent into a clean, grammatically correct message."""
    try:
        prompt = (
            f"You are a professional writing assistant. The user wants to send a WhatsApp message to {contact_name}. "
            f"The user's raw instruction or message topic is: '{original_command}'. "
            "Task: Rewrite this into a clear, natural, grammatically correct WhatsApp message body. "
            "Fix grammar, remove fillers, and return ONLY the final message text."
        )
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"].strip().replace('"', '')
    except Exception:
        return original_command or f"Hey {contact_name}!"

def analyze_intent_with_llm(user_input: str) -> dict:
    """Analyzes complex user sentences to determine intent and extracted parameters."""
    try:
        prompt = (
            f"Analyze this user voice command: '{user_input}'. "
            "Classify the intent into one of these keywords if applicable: "
            "'STOP_MUSIC', 'NEXT_SONG', 'PREV_SONG', 'OPEN_APP', 'CLOSE_APP', 'SEND_WHATSAPP', 'CLEAR_CHAT', 'SPAM_CHECK', 'CLASS_SCHEDULE', or 'GENERAL'. "
            "Return a JSON object with keys 'intent' and 'parameter'."
        )
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        content = response["message"]["content"].strip()
        return parse_llm_json(content)
    except Exception:
        return {}