"""One small client for any OpenAI-compatible chat API (Groq, Gemini, OpenRouter, Ollama...).

Configure with environment variables or a .env file in the project root:
    LLM_API_KEY    the provider key (not needed for a local Ollama server)
    LLM_BASE_URL   e.g. http://localhost:11434/v1 for Ollama; https://api.groq.com/openai/v1 when only a key is set
    LLM_MODEL      default gemma4:e4b-it-qat
    LLM_REASONING_EFFORT  "none" (default for a local Ollama server) turns a thinking model's hidden reasoning off.
                   The text written here is short and factual: thinking only adds delay, and on a tight token
                   budget it can use every token before any answer is written. Set e.g. "low" to allow some.
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
    for path in dict.fromkeys([ROOT / ".env", env_file()]):
        if path.exists():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def env_file():
    """Where generated settings (the signing key) are written: ENV_FILE if set, else the project .env.
    A read-only container points ENV_FILE into its data volume, so the key survives restarts."""
    from pathlib import Path
    return Path(os.getenv("ENV_FILE") or ROOT / ".env")


def config():
    _env()
    key = os.getenv("LLM_API_KEY", "")
    base = os.getenv("LLM_BASE_URL", "") or ("https://api.groq.com/openai/v1" if key else "")
    base = base.rstrip("/")
    effort = os.getenv("LLM_REASONING_EFFORT", "none" if ":11434" in base else "")
    return {"key": key, "base": base, "model": os.getenv("LLM_MODEL", "gemma4:e4b-it-qat"), "effort": effort}


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
    if c["effort"]:
        body["reasoning_effort"] = c["effort"]
    plain = {k: v for k, v in body.items() if k != "reasoning_effort"}  # for a provider that rejects the parameter
    attempts = ([dict(body, response_format={"type": "json_object"})] if json_mode else []) + [body] + ([plain] if c["effort"] else [])
    for payload in attempts:
        try:
            req = urllib.request.Request(
                c["base"] + "/chat/completions", data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {c['key'] or 'none'}",
                         "User-Agent": "claimshield-nexus/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM ERROR] {e}")
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
