"""One small client for any OpenAI-compatible chat API (Groq, Gemini, OpenRouter, Ollama...).

Configure with environment variables or a .env file in the project root:
    LLM_API_KEY    the provider key (not needed for a local Ollama server)
    LLM_BASE_URL   default https://api.groq.com/openai/v1
    LLM_MODEL      default llama-3.3-70b-versatile
Every function returns None on any failure, so callers can fall back to templates.
"""
import json
import os
import re
import urllib.request

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
    key = os.getenv("LLM_API_KEY", "")
    base = os.getenv("LLM_BASE_URL", "") or ("https://api.groq.com/openai/v1" if key else "")
    return {"key": key, "base": base.rstrip("/"), "model": os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")}


def available():
    return bool(config()["base"])


def status():
    c = config()
    return {"enabled": bool(c["base"]), "model": c["model"] if c["base"] else None,
            "provider": c["base"].split("//")[-1].split("/")[0] if c["base"] else None}


def chat(system, user, json_mode=False, max_tokens=800):
    c = config()
    if not c["base"]:
        return None
    body = {"model": c["model"], "temperature": 0.2, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    attempts = [dict(body, response_format={"type": "json_object"}), body] if json_mode else [body]
    for payload in attempts:
        try:
            req = urllib.request.Request(
                c["base"] + "/chat/completions", data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {c['key'] or 'none'}",
                         "User-Agent": "claimshield-nexus/0.1"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return None


def chat_json(system, user, max_tokens=900):
    text = chat(system, user, json_mode=True, max_tokens=max_tokens)
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None
