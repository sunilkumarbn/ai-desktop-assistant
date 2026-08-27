import json
import os
import socket
import time
import speech_recognition as sr
import pyttsx3
import pyaudio
import asyncio
import ollama
from vosk import KaldiRecognizer, Model
from config import OLLAMA_MODEL, MODEL_PATH
from ai_handler import clean_repeated_speech, analyze_intent_with_llm
from actions import (
    stop_music, next_music, previous_music, change_music, play_local_music,
    open_application, close_application, send_whatsapp_to_contact,
    clear_whatsapp_chat, check_and_clean_spam_messages, 
    check_and_clean_promotional_chats, send_class_schedule_now
)

# Initialize Vosk Model Offline if available
vosk_model = Model(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

def is_online() -> bool:
    """Checks if there is an active internet connection."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def speak(text: str):
    """Prints text to terminal and speaks it using native Windows SAPI5."""
    print(f"\nAssistant: {text}\n")
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()

def confirm_action(prompt_text: str) -> bool:
    """Uses Ollama to intelligently determine if the user's spoken response means 'Yes' or 'No'."""
    speak(f"{prompt_text}")
    time.sleep(0.5)
    
    print("Listening for your response...")
    response = clean_repeated_speech(listen_for_command().lower().strip())
    print(f"Debug - Heard response: '{response}'")
    
    if not response:
        try:
            fallback = input("Type 'y' for Yes or 'n' for No: ").lower().strip()
            return fallback in ["yes", "y", "correct", "true", "sure", "ok"]
        except Exception:
            return False

    try:
        system_prompt = (
            "You are an intent-parsing assistant for a voice-controlled desktop script. "
            "Analyze the user's response to a confirmation question. "
            "Determine if the user's intent is to approve/agree (Yes) or decline/cancel/modify (No). "
            "Reply with EXACTLY one word: either 'YES' or 'NO'."
        )
        chat_completion = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"The question was: '{prompt_text}'. The user's response was: '{response}'"}
            ],
        )
        decision = chat_completion["message"]["content"].strip().upper()
        
        if "YES" in decision:
            return True
        else:
            return False
    except Exception:
        if any(word in response for word in ["yes", "yeah", "yep", "sure", "send", "confirm", "ok", "okay", "right", "ya", "do it", "go ahead"]):
            return True
        return False

def listen_online() -> str:
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1.2  
    
    with sr.Microphone() as source:
        print("\nListening (Online - Google API)... Speak your command:")
        r.adjust_for_ambient_noise(source, duration=0.8)
        try:
            audio = r.listen(source, timeout=12, phrase_time_limit=25)
            command = r.recognize_google(audio)
            print(f"You said: {command}")
            return command
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            return ""
        except sr.RequestError:
            return ""

def listen_offline() -> str:
    if not vosk_model:
        return ""

    rec = KaldiRecognizer(vosk_model, 16000)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()

    print("\nListening (Offline - Vosk)... Speak your command:")
    command = ""
    start_time = time.time()

    while (time.time() - start_time) < 20.0:
        data = stream.read(4000, exception_on_overflow=False)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if result.get("text", "").strip():
                command = result.get("text", "").strip()
                break
        else:
            partial = json.loads(rec.PartialResult()).get("partial", "").strip()
            if partial:
                command = partial

    stream.stop_stream()
    stream.close()
    p.terminate()

    if command:
        print(f"You said: {command}")
    return command

def listen_for_command() -> str:
    raw_command = listen_online() if is_online() else listen_offline()
    return clean_repeated_speech(raw_command)

def process_command(user_input: str):
    text = user_input.lower().strip()

    # 1. LLM Complete-Sentence Context & Intent Analysis (First Pass)
    if len(text.split()) > 4:
        parsed = analyze_intent_with_llm(user_input)
        intent = parsed.get("intent", "").upper()
        param = parsed.get("parameter", "").strip()

        if intent == "CLASS_SCHEDULE":
            speak(send_class_schedule_now(speak, confirm_action))
            return
        elif intent == "SEND_WHATSAPP" and param:
            speak(send_whatsapp_to_contact(param, user_input, user_input, speak, confirm_action))
            return

    # 2. Standard Rule-Based Keyword Matching
    if any(phrase in text for phrase in ["stop music", "pause music", "turn off music"]):
        speak(stop_music())
        return

    if any(phrase in text for phrase in ["next song", "next track", "skip song"]):
        speak(next_music())
        return

    if any(phrase in text for phrase in ["previous song", "previous track"]):
        speak(previous_music())
        return

    if "change song" in text or "change music" in text:
        song = text.replace("change song", "").replace("change music", "").strip()
        speak(change_music(song))
        return

    if any(word in text for word in ["open", "launch", "start"]):
        for verb in ["open", "launch", "start"]:
            if verb in text:
                target = text.split(verb, 1)[-1].strip()
                if target:
                    speak(open_application(target))
                    return

    if any(phrase in text for phrase in ["spam", "phishing", "scam"]):
        result = asyncio.run(check_and_clean_spam_messages(speak, confirm_action))
        speak(result)
        return

    if any(phrase in text for phrase in ["promotional", "business chat", "promo messages", "reminder chats", "junk chats"]):
        result = asyncio.run(check_and_clean_promotional_chats(speak, confirm_action))
        speak(result)
        return

    if any(phrase in text for phrase in ["class link", "schedule a class", "send class schedule", "send meet link", "discussion class"]):
        speak(send_class_schedule_now(speak, confirm_action))
        return

    if any(phrase in text for phrase in ["clear chat", "delete chat", "clear messages", "clear history"]):
        try:
            clean_text = text
            for prefix in ["clear chat with", "delete chat with", "clear history with", "clear messages from", "delete chat", "clear chat"]:
                if prefix in clean_text:
                    clean_text = clean_text.split(prefix, 1)[-1].strip()
                    break
            speak(clear_whatsapp_chat(clean_text, confirm_action))
            return
        except Exception as e:
            speak(f"Could not process clear chat request: {e}")
            return

    is_messaging_intent = any(keyword in text for keyword in ["send", "message", "text"]) or ("whatsapp" in text and "open" not in text)
    if is_messaging_intent and ("to" in text or "whatsapp" in text):
        try:
            clean_text = text.replace("on whatsapp", "").replace("in whatsapp", "").strip()
            for prefix in ["send a message to", "send message to", "send text to", "send to", "message to", "text to", "whatsapp"]:
                if clean_text.startswith(prefix):
                    clean_text = clean_text[len(prefix):].strip()
                    break

            if " saying " in clean_text:
                contact, message = clean_text.split(" saying ", 1)
            elif " that " in clean_text:
                contact, message = clean_text.split(" that ", 1)
            else:
                contact = clean_text
                message = ""

            speak(send_whatsapp_to_contact(contact.strip(), message.strip(), user_input, speak, confirm_action))
            return
        except Exception as e:
            speak(f"Could not process messaging request: {e}")
            return

    if any(word in text for word in ["close", "exit", "terminate", "quit"]):
        for verb in ["close", "exit", "terminate", "quit"]:
            if verb in text:
                target = text.split(verb, 1)[-1].strip()
                if target:
                    speak(close_application(target))
                    return

    if "play" in text and ("music" in text or "song" in text):
        song = text.replace("play", "").replace("music", "").replace("song", "").strip()
        speak(play_local_music(song))
        return

    # 3. General LLM Conversational Fallback
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are an intelligent desktop assistant. Answer questions or converse concisely and naturally."},
                {"role": "user", "content": user_input}
            ],
        )
        speak(response["message"]["content"])
    except Exception:
        speak("I am listening, but my local model encountered an issue processing that.")

def run_assistant():
    mode_status = "Online" if is_online() else "Offline"
    speak(f"Assistant ready in {mode_status} mode.")

    while True:
        user_input = listen_for_command()
        if not user_input:
            continue

        text_lower = user_input.lower().strip()
        if text_lower in ["stop", "exit", "quit", "goodbye"] or any(phrase in text_lower for phrase in ["stop assistant", "shut down"]):
            speak("Goodbye!")
            break

        process_command(user_input)

if __name__ == "__main__":
    run_assistant()