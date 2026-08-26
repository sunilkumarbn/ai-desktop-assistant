# 🎙️ AI Voice & Desktop Automation Assistant

An intelligent, voice-driven desktop assistant built in Python. The system combines instant rule-based keyword matching with local LLM-powered intent classification (via Ollama) to automate everyday desktop tasks, execute messaging workflows, manage local media playback, and perform AI-assisted security scans.

---

## ✨ Features

* **Hybrid Intent Recognition Engine:** Utilizes instant regex pattern matching for high-speed local actions, falling back to a local LLM (Ollama) for complex natural language understanding.
* **Fuzzy Contact Resolution:** Integrated `rapidfuzz` string matching to dynamically resolve spoken contact variations to correct targets.
* **Automated WhatsApp Dispatches:** Direct desktop automation via PyAutoGUI, Pywinctl/PyGetWindow, and Pyperclip with active window state verification.
* **Asynchronous Chat Audits:** Concurrent LLM analysis using `asyncio` and `ollama.AsyncClient` for rapid spam and phishing detection.
* **Structured UI Guard:** Context-managed execution (`UIStateGuard`) to automatically release held keys and clear clipboard data upon exit or errors.
* **Interactive Voice Confirmation Loop:** Safety confirmation pipeline using Speech-to-Text (STT) and Text-to-Speech (TTS) before performing sensitive tasks.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **AI / NLP:** Ollama (Local LLM), RapidFuzz, SpeechRecognition, PyTTSx3
* **GUI Automation & System:** PyAutoGUI, PyGetWindow, Pyperclip, Subprocess, Asyncio

---

## 📁 Project Structure

```text
├── actions.py           # Core execution functions, WhatsApp automation, async chat scans
├── ai_handler.py       # Intent parsing logic and local LLM context prompt handling
├── calendar_service.py # Google Meet / Calendar link extraction logic
├── config.py           # Configuration parameters and environment variable loading
├── main.py             # Main event loop, STT input listening, and command router
├── .env.example        # Environment variable template
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation