"""
ClaimShield Nexus - Local LLM Engine (Llama 3.2)
Provides both chat() and generate() interfaces for Ollama with Windows localhost proxy bypass.
"""

import os
import json
import urllib.request
import urllib.error

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def _send_request(endpoint: str, payload: dict, timeout: int = 60) -> dict:
    url = f"{OLLAMA_HOST}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    # Bypass Windows system proxy resolution which stalls on localhost
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def chat(messages, model: str = DEFAULT_MODEL, **kwargs) -> str:
    """
    Chat completion interface expected by backend/brain/brief.py.
    Accepts list of messages [{'role': '...', 'content': '...'}] or a single prompt string.
    Returns the assistant content string.
    """
    if isinstance(messages, str):
        msgs = [{"role": "user", "content": messages}]
    else:
        msgs = messages

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": msgs,
        "stream": False
    }
    
    try:
        res = _send_request("/api/chat", payload)
        return res.get("message", {}).get("content", "")
    except Exception as e:
        # Fallback to /api/generate if /api/chat is unavailable
        try:
            prompt_str = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in msgs])
            gen_res = _send_request("/api/generate", {"model": model or DEFAULT_MODEL, "prompt": prompt_str, "stream": False})
            return gen_res.get("response", "")
        except Exception:
            raise e

def generate(prompt: str, system: str = "") -> dict:
    """
    Structured generation interface with JSON formatting support.
    """
    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json"
    }
    try:
        res = _send_request("/api/generate", payload)
        return {
            "ok": True,
            "text": res.get("response", "{}"),
            "model": DEFAULT_MODEL
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "model": "template"
        }
