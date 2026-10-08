"""One small client for any OpenAI-compatible chat API (Groq, Gemini, OpenRouter, Ollama...).

Configure with environment variables or a .env file in the project root:
    LLM_API_KEY    the provider key (not needed for a local Ollama server)
    LLM_BASE_URL   default https://api.groq.com/openai/v1
    LLM_MODEL      default llama-3.3-70b-versatile
Every function returns None on any failure, so callers can fall back to templates.

The clinical audit uses its own local model (see clinical_config), so the Second Brain provider and the
clinical model can differ:
    CLINICAL_LLM_BASE_URL  default http://127.0.0.1:11434 (a local Ollama server)
    CLINICAL_LLM_MODEL     default llama3.2
    CLINICAL_LLM_TIMEOUT   seconds, default 60
    CLINICAL_LLM_ENABLED   set to 0 to turn the model off; the deterministic checks still run
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

from backend.pipeline.common import ROOT

_loaded = False
_STATUS = {}  # clinical model status, cached briefly so an offline server is not probed on every request
STATUS_SECONDS = 15


def _env():
    global _loaded
    if _loaded:
        return
    _loaded = True
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def config():
    _env()
    key = os.getenv("LLM_API_KEY", "")
    base = os.getenv("LLM_BASE_URL", "") or ("https://api.groq.com/openai/v1" if key else "")
    return {"key": key, "base": base.rstrip("/"), "model": os.getenv("LLM_MODEL", "gemma3:4b")}


def _local(url):
    return urllib.parse.urlsplit(url).hostname in ("127.0.0.1", "localhost", "::1")


def _open(req, timeout):
    """Local servers are reached directly: a system proxy would otherwise stall requests to localhost."""
    if _local(req.full_url):
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


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
            with _open(req, 90) as r:
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


# ------------------------------------------------------------ clinical model ---
def clinical_config():
    _env()
    try:
        timeout = max(1.0, float(os.getenv("CLINICAL_LLM_TIMEOUT", "60")))
    except ValueError:
        timeout = 60.0
    return {"base": os.getenv("CLINICAL_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            "model": os.getenv("CLINICAL_LLM_MODEL", "llama3.2"), "timeout": timeout,
            "enabled": os.getenv("CLINICAL_LLM_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")}


def clinical_status(timeout=2):
    """Whether the local clinical model can answer: server reachable and model pulled. Never downloads anything."""
    c = clinical_config()
    key = (c["base"], c["model"], c["enabled"])
    hit = _STATUS.get(key)
    if hit and time.monotonic() - hit[0] < STATUS_SECONDS:
        return hit[1]
    _STATUS[key] = (time.monotonic(), _probe(c, timeout))
    return _STATUS[key][1]


def _probe(c, timeout):
    out = {"enabled": c["enabled"], "model": c["model"], "provider": urllib.parse.urlsplit(c["base"]).netloc,
           "reachable": False, "model_available": False}
    if not c["enabled"]:
        return out | {"reason": "Turned off with CLINICAL_LLM_ENABLED=0"}
    try:
        with _open(urllib.request.Request(c["base"] + "/api/tags"), timeout) as r:
            names = {m.get("name", "") for m in json.loads(r.read()).get("models", [])}
    except Exception as e:
        return out | {"reason": f"Ollama is not reachable at {out['provider']} ({type(e).__name__})"}
    found = c["model"] in names or f"{c['model']}:latest" in names
    return out | {"reachable": True, "model_available": found,
                  **({} if found else {"reason": f"Model {c['model']} is not pulled; run: ollama pull {c['model']}"})}


def clinical_json(system, user, max_tokens=600):
    """Ask the local clinical model for one JSON object. Returns (dict, None) or (None, reason)."""
    c = clinical_config()
    if not c["enabled"]:
        return None, "Clinical model turned off (CLINICAL_LLM_ENABLED=0)"
    payload = {"model": c["model"], "stream": False, "format": "json",
               "options": {"temperature": 0, "num_predict": max_tokens},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(c["base"] + "/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "claimshield-nexus/0.1"})
    try:
        with _open(req, c["timeout"]) as r:
            text = json.loads(r.read()).get("message", {}).get("content", "")
    except TimeoutError:
        return None, f"The clinical model did not answer within {c['timeout']:.0f} s"
    except Exception as e:
        return None, f"The clinical model is unavailable ({type(e).__name__})"
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        out = json.loads(m.group(0)) if m else None
    except ValueError:
        out = None
    return (out, None) if isinstance(out, dict) else (None, "The clinical model returned malformed JSON")
