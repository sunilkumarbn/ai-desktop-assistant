import glob
import os
import random
import re
import subprocess
import time
import urllib.parse
import webbrowser
import ollama
import pyautogui
import pyperclip
from AppOpener import close as close_app
from AppOpener import open as open_app
from config import MUSIC_DIR, OLLAMA_MODEL
from ai_handler import generate_contextual_message, parse_llm_json
from calendar_service import get_todays_google_meet_link
from rapidfuzz import process, fuzz
import asyncio
from ollama import AsyncClient
from config import OLLAMA_MODEL
import pygetwindow as gw
from config import OLLAMA_MODEL, WHATSAPP_LAUNCH_DELAY, SEARCH_DELAY

def play_local_music(song_name: str = "") -> str:
    if not os.path.exists(MUSIC_DIR):
        return f"Music directory not found at {MUSIC_DIR}."

    if isinstance(song_name, dict):
        song_name = song_name.get("song_name") or song_name.get("query") or ""

    if not isinstance(song_name, str):
        song_name = str(song_name)

    audio_extensions = ("*.mp3", "*.wav", "*.flac", "*.m4a")
    files = []
    for ext in audio_extensions:
        files.extend(glob.glob(os.path.join(MUSIC_DIR, "**", ext), recursive=True))

    if not files:
        return "No audio files found in your Music folder."

    song_name = song_name.lower().strip()
    filler_words = ["play", "another", "song", "music", "a", "track", "different"]
    words = [w for w in song_name.split() if w not in filler_words]
    clean_query = " ".join(words[:3]).strip()

    target_file = None
    if clean_query:
        for file in files:
            if clean_query in os.path.basename(file).lower():
                target_file = file
                break

    if not target_file:
        target_file = random.choice(files)

    os.startfile(target_file)
    full_filename = os.path.basename(target_file)
    file_title_only = os.path.splitext(full_filename)[0]
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', file_title_only)
    title_words = ' '.join(clean_title.split()).split()
    short_title = " ".join(title_words[:4]) if title_words else "track"

    return f"Playing: {short_title}"

def stop_music() -> str:
    players = ["wmplayer.exe", "Music.UI.exe", "Groove.exe", "vlc.exe", "spotify.exe"]
    stopped_any = False
    for player in players:
        try:
            result = subprocess.run(f"taskkill /f /im {player}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                stopped_any = True
        except Exception:
            pass
    try:
        pyautogui.press('playpause')
        stopped_any = True
    except Exception:
        pass
    
    return "Music stopped." if stopped_any else "No active media player found to stop."

def next_music() -> str:
    stop_music()
    time.sleep(0.3)
    return play_local_music()

def previous_music() -> str:
    try:
        pyautogui.press('prevtrack')
        return "Going to previous track."
    except Exception as e:
        return f"Could not go to previous track: {e}"

def change_music(song_name: str = "") -> str:
    stop_music()
    time.sleep(0.5)
    return play_local_music(song_name)

def open_application(app_name: str = "") -> str:
    app_name = app_name.lower().strip()
    if not app_name:
        return "Please specify an application to open."

    try:
        open_app(app_name, match_closest=True, output=False)
        return f"Opening {app_name}."
    except Exception:
        pass

    web_services = {
        "youtube": "https://www.youtube.com",
        "reddit": "https://www.reddit.com",
        "github": "https://www.github.com",
        "google": "https://www.google.com",
        "whatsapp": "whatsapp:",
    }

    for service, url in web_services.items():
        if service in app_name:
            if url.endswith(":"):
                subprocess.run(f'cmd /c start {url}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(url)
            return f"Opening {service.capitalize()}."

    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(app_name)}")
    return f"Searching online for '{app_name}'."


APP_ALIASES = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "whatsapp": "whatsapp",
    "chrome": "chrome",
    "notepad": "notepad",
}

def close_application(app_name: str) -> str:
    """Closes an application by process name, AppOpener alias, or window title."""
    if not app_name:
        return "No application name provided to close."

    clean_name = app_name.lower().strip()
    target = APP_ALIASES.get(clean_name, clean_name)

    try:
        # 1. Attempt graceful close via AppOpener
        close(target, match_closest=True, output=False)
        return f"Closed {app_name}."
    except Exception:
        pass

    try:
        # 2. Fallback: Force kill via Windows taskkill process matching
        result = subprocess.run(
            f"taskkill /f /im {target}.exe",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            return f"Closed {app_name}."

        # 3. Fallback: Find matching window title and close it
        windows = [w for w in gw.getAllWindows() if clean_name in w.title.lower()]
        if windows:
            for win in windows:
                win.close()
            return f"Closed window matching '{app_name}'."

    except Exception as e:
        return f"Failed to close {app_name}: {e}"

    return f"Could not find a running process for '{app_name}'."

# Define your known contacts and group names here
CONTACTS_LIST = {
    "adarsh": "Adarsh",
    "stage 1": "STAGE-1",
    "stage 2": "STAGE-2",
    "genai": "GENAI-AGENTIC-AI",
}

def find_matching_contact(contact_name: str, score_cutoff: int = 60) -> str:
    if not contact_name:
        return ""

    clean_input = contact_name.lower().strip()

    # 1. Direct exact or dictionary key match
    if clean_input in CONTACTS_LIST:
        return CONTACTS_LIST[clean_input]

    # 2. Fuzzy match against registered contacts
    choices = list(CONTACTS_LIST.keys())
    match = process.extractOne(clean_input, choices, scorer=fuzz.WRatio)

    if match:
        best_key, score, _ = match
        if score >= score_cutoff:
            return CONTACTS_LIST[best_key]

    # 3. Fallback: return capitalized input if no match in dictionary
    return contact_name.strip().title()

async def analyze_single_message_async(client: AsyncClient, message_text: str) -> dict:
    """Asynchronously sends a single message to Ollama for spam/phishing classification."""
    prompt = (
        f"Analyze this chat message for spam, phishing, scam, or aggressive promotional content: '{message_text}'. "
        "Return ONLY a valid JSON object with keys: "
        "'is_spam' (boolean), 'confidence' (float 0.0 to 1.0), and 'reason' (short string)."
    )
    
    try:
        response = await client.chat(
            model=OLLAMA_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        content = response["message"]["content"].strip()
        parsed = parse_llm_json(content)
        return {
            "text": message_text,
            "is_spam": parsed.get("is_spam", False),
            "confidence": parsed.get("confidence", 0.0),
            "reason": parsed.get("reason", "No reason provided")
        }
    except Exception as e:
        return {"text": message_text, "is_spam": False, "confidence": 0.0, "reason": str(e)}


async def batch_scan_messages_async(message_list: list) -> list:
    """Scans multiple chat messages concurrently across available CPU threads."""
    client = AsyncClient()
    tasks = [analyze_single_message_async(client, msg) for msg in message_list]
    results = await asyncio.gather(*tasks)
    return results


def send_whatsapp_to_contact(contact_name: str = "", message: str = "", original_command: str = "", speak_func=None, confirm_callback=None) -> str:
    """
    Sends a WhatsApp message using PyAutoGUI. Bypasses LLM parsing if contact_name 
    is provided directly (e.g. broadcasts), otherwise parses raw voice strings via Ollama.
    """
    # 1. Contact and Message Resolution
    if contact_name and contact_name.strip():
        # Direct call: Bypass Ollama LLM extraction completely
        clean_contact = find_matching_contact(contact_name.strip())
        message = message or f"Hello {clean_contact}!"
    else:
        # Voice command call: Extract target and payload via Ollama
        try:
            target_text = original_command or contact_name
            if not target_text:
                return "No voice command or contact name provided."

            prompt = (
                f"Analyze this voice command for sending a WhatsApp message: '{target_text}'. "
                "Extract two fields: 'recipient' (the name of the person or group being messaged) and 'message_body' (what to say). "
                "If no clear, valid person or group name is provided, set 'recipient' to 'NONE'. "
                "Return ONLY a valid JSON object with keys 'recipient' and 'message_body'."
            )
            
            response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
            parsed = parse_llm_json(response["message"]["content"].strip())
            
            extracted_contact = parsed.get("recipient", "NONE").strip()
            extracted_message = parsed.get("message_body", "").strip()

            if not extracted_contact or extracted_contact.upper() == "NONE" or len(extracted_contact) < 2:
                return "I couldn't identify a valid contact or group name to send the message to."

            clean_contact = find_matching_contact(extracted_contact)
            
            if not message:
                message = extracted_message if extracted_message else f"Hello {clean_contact}!"
            else:
                message = generate_contextual_message(clean_contact, message)

        except Exception as e:
            return f"Failed during message preparation: {e}"

    # 2. Confirmation Check
    if confirm_callback:
        confirmed = confirm_callback(f"I am about to send a message to '{clean_contact}'. Shall I proceed?")
        if not confirmed:
            return f"Message to {clean_contact} was cancelled for safety."

    # 3. Protected GUI Automation Execution
    with UIStateGuard():
        try:
            subprocess.run('cmd /c start whatsapp:', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not focus_whatsapp_window(timeout=10.0):
                return "Failed to focus WhatsApp window."

            time.sleep(WHATSAPP_LAUNCH_DELAY)

            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

            pyperclip.copy(clean_contact)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(SEARCH_DELAY)

            pyautogui.press('down')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.5)

            pyperclip.copy(message)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')

            return f"Successfully sent message to {clean_contact}."

        except Exception as e:
            return f"Automation interrupted: {e}"
    
def clear_whatsapp_chat(contact_name: str, confirm_callback=None) -> str:
    try:
        clean_contact = contact_name.replace("whatsapp", "").strip()
        if not clean_contact:
            return "Please specify whose chat history you want to clear."

        if confirm_callback:
            confirmed = confirm_callback(f"Are you sure you want to clear the entire chat history with {clean_contact}?")
            if not confirmed:
                return "Clearing chat cancelled."

        subprocess.run('cmd /c start whatsapp:', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.5)

        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.3)

        pyperclip.copy(clean_contact)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.5)

        pyautogui.press('down')
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(1.0)

        pyautogui.hotkey('ctrl', 'shift', 'd')
        time.sleep(0.8)
        pyautogui.press('enter')

        return f"Chat history with {clean_contact} has been cleared."
    except Exception as e:
        return f"Failed to clear chat history: {e}"

async def check_and_clean_spam_messages(speak_func=None, confirm_callback=None) -> str:
    """Scans open WhatsApp chats for spam/phishing messages using GUI automation and Ollama."""
    if speak_func:
        speak_func("Scanning your recent WhatsApp chats for spam and phishing messages...")

    scanned_messages = []

    with UIStateGuard():
        subprocess.run('cmd /c start whatsapp:', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not focus_whatsapp_window(timeout=10.0):
            return "Failed to focus WhatsApp window."

        time.sleep(WHATSAPP_LAUNCH_DELAY)

        # Coordinates/positions for recent top chat items
        chat_y_positions = [200, 270, 340, 410, 480]

        for pos_y in chat_y_positions:
            try:
                # Click chat in sidebar
                pyautogui.click(x=300, y=pos_y)
                time.sleep(0.8)

                # Click message pane, select all text, copy to clipboard
                pyautogui.click(x=900, y=500)
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.4)

                content = pyperclip.paste().strip()
                if content and len(content) >= 5:
                    scanned_messages.append({"text": content[:1000]})
            except Exception as e:
                print(f"Failed scanning chat position {pos_y}: {e}")

    if not scanned_messages:
        return "No readable chat content found to scan."

    # Analyze extracted content via Ollama
    flagged_messages = []
    for item in scanned_messages:
        prompt = (
            f"Analyze this chat snippet for spam, phishing, scams, or suspicious links:\n'{item['text']}'\n"
            "Return JSON: {\"is_spam\": true/false, \"reason\": \"brief reason\"}"
        )
        try:
            response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
            parsed = parse_llm_json(response["message"]["content"].strip())
            if parsed.get("is_spam"):
                flagged_messages.append({"reason": parsed.get("reason", "Suspicious content"), "text": item["text"]})
        except Exception:
            continue

    if not flagged_messages:
        return f"Scan complete. Examined {len(scanned_messages)} recent chat threads — no security threats detected."

    summary = f"Scan complete. Flagged {len(flagged_messages)} suspicious chat(s):\n"
    for item in flagged_messages:
        summary += f"- Reason: {item['reason']} | Snippet: '{item['text'][:40]}...'\n"

    return summary

async def check_and_clean_promotional_chats(speak_func, confirm_callback) -> str:
    try:
        speak_func("Scanning your recent chats for business promotional and reminder messages.")
        subprocess.run('cmd /c start whatsapp:', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3.0)  

        chat_y_positions = [250, 320, 390, 460, 530]
        found_promotional = False

        for pos_y in chat_y_positions:
            pyautogui.click(x=300, y=pos_y)
            time.sleep(1.0)

            pyautogui.click(x=900, y=500)
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            
            scanned_text = pyperclip.paste().strip()
            if not scanned_text or len(scanned_text) < 5:
                continue

            prompt = (
                "Analyze the following chat content. Determine if it is a promotional message, "
                "an automated business notification, marketing offer, loan reminder, or junk spam. "
                "Reply with 'PROMOTIONAL: [reason]' if it is business promotion/spam/reminder, "
                "or reply with 'PERSONAL' if it is regular chat.\n\nContent:\n" + scanned_text[:1000]
            )
            
            response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
            analysis = response["message"]["content"].strip()

            if "PROMOTIONAL" in analysis.upper():
                found_promotional = True
                reason_text = analysis.replace("PROMOTIONAL:", "").strip()
                speak_func(f"Found promotional/reminder chat. Reason: {reason_text}")
                
                if confirm_callback("Do you want me to delete and clear this promotional business chat?"):
                    pyautogui.hotkey('ctrl', 'shift', 'd')
                    time.sleep(0.8)
                    pyautogui.press('enter')
                    speak_func("Promotional business chat deleted successfully.")
                else:
                    speak_func("Deletion skipped for this chat.")
                time.sleep(1.0)

        return "Finished scanning and cleaning promotional chats." if found_promotional else "No promotional chats found."
    except Exception as e:
        return f"Failed to clean promotional chats: {e}"

def send_class_schedule_now(speak_func, confirm_callback) -> str:
    target_groups = ["STAGE-2", "STAGE-1", "GENAI-AGENTIC-AI"]
    speak_func("Fetching today's Google Meet link and broadcasting to your study groups...")

    try:
        meet_link = get_todays_google_meet_link()
    except Exception:
        meet_link = "https://meet.google.com/rgx-ysrj-heo"

    message = (
        "Hey everyone! 🚀 Today's discussion session on Python will be at 7:00 PM. "
        f"\nJoin Link : {meet_link}"
    )

    success_count = 0  # Placed OUTSIDE the loop
    for group_name in target_groups:  # Single loop iteration
        try:
            result = send_whatsapp_to_contact(
                contact_name=group_name,
                message=message,
                speak_func=speak_func,
                confirm_callback=confirm_callback
            )
            print(f"Broadcast [{group_name}]: {result}")
            if "Successfully sent" in result:
                success_count += 1
            time.sleep(3.0)
        except Exception as e:
            print(f"Failed for {group_name}: {e}")

    return f"Class schedule link successfully sent to {success_count} groups!"

class UIStateGuard:
    """Ensures keyboard modifiers and global application states reset safely on exit/error."""
    def __enter__(self):
        # Save original clipboard content if needed
        self.original_clipboard = pyperclip.paste()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 1. Release all potentially stuck modifier keys
        for key in ['ctrl', 'alt', 'shift', 'win']:
            pyautogui.keyUp(key)

        # 2. Reset clipboard to prevent leaking sensitive messaging text
        try:
            pyperclip.copy("")
        except Exception:
            pass


def focus_whatsapp_window(timeout=10.0) -> bool:
    """Focuses the active WhatsApp Desktop window if running."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        windows = [w for w in gw.getAllWindows() if "whatsapp" in w.title.lower()]
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            return True
        time.sleep(0.5)
    return False
