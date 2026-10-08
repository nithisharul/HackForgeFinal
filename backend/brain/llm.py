import json
import os
import re
try:
    from google import genai
    from google.genai import types
except ImportError:  # google-genai is optional: without it everything runs in template mode
    genai = types = None
from backend.pipeline.common import ROOT

_loaded = False

def _env():
    global _loaded
    if _loaded:
        return
    _loaded = True
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def config():
    _env()
    key = os.getenv("GEMINI_API_KEY", os.getenv("LLM_API_KEY", "")) if genai else ""
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    return {"key": key, "model": model}

def available():
    return bool(config()["key"])

def status():
    c = config()
    return {"enabled": bool(c["key"]), "model": c["model"], "provider": "google-gemini"}

def chat(system, user, json_mode=False, max_tokens=4000):
    c = config()
    if not c["key"]: return None
    try:
        client = genai.Client(api_key=c["key"])
        sys_instruct = system
        if json_mode:
            sys_instruct += "\nIMPORTANT: You must return ONLY valid JSON without Markdown formatting blocks."
            
        response = client.models.generate_content(
            model=c["model"],
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.1,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" if json_mode else "text/plain"
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return None

def chat_json(system, user, max_tokens=4000):
    text = chat(system, user, json_mode=True, max_tokens=max_tokens)
    if not text: return None
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None
