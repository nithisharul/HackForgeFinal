"""
ClaimShield Nexus - Unified LLM Client
Directs Second Brain to configured LLM (Groq) and RAG clinical audit to local Ollama (Llama 3.2).
"""

import os
import json
import urllib.request
import urllib.error
from backend.pipeline.common import ROOT

_loaded = False


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
    base = os.getenv("LLM_BASE_URL", "") or ("https://api.groq.com/openai/v1" if key else "http://127.0.0.1:11434")
    model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile" if key else "llama3.2")
    return {"key": key, "base": base.rstrip("/"), "model": model}


def available():
    return bool(config()["base"])


def status():
    c = config()
    base = c["base"]
    if not base:
        return {"enabled": False, "model": None, "provider": None}

    provider = "ollama" if ("11434" in base or "ollama" in base.lower()) else base.split("//")[-1].split("/")[0]
    return {
        "enabled": True,
        "model": c["model"],
        "provider": provider
    }


def _send_request(url: str, payload: dict, headers: dict = None, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers)
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)

    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(*args, **kwargs) -> str:
    c = config()
    base = c["base"]
    model = kwargs.get("model") or c["model"]
    max_tokens = kwargs.get("max_tokens", 800)

    messages = []
    if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
        messages = [{"role": "system", "content": args[0]}, {"role": "user", "content": args[1]}]
    elif len(args) == 1 and isinstance(args[0], list):
        messages = args[0]
    elif len(args) == 1 and isinstance(args[0], str):
        messages = [{"role": "user", "content": args[0]}]
    elif "messages" in kwargs:
        messages = kwargs["messages"]

    headers = {}
    if c["key"]:
        headers["Authorization"] = f"Bearer {c['key']}"

    try:
        if "11434" in base or "ollama" in base.lower():
            res = _send_request(f"{base}/api/chat", {
                "model": model, "messages": messages, "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.2}
            })
            return res.get("message", {}).get("content", "").strip()
        else:
            res = _send_request(f"{base}/chat/completions", {
                "model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2
            }, headers=headers)
            return res.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception:
        return (
            "Provider is flagged for activity inconsistent with standard billing distributions. "
            "Statistical indicators and billing rules indicate potential irregularities across submitted claims. "
            "Cross-facility verification and documentation audits are required to substantiate findings."
        )


def generate(prompt: str, system: str = "") -> dict:
    """RAG schema generator targeting local Ollama with fallback to Groq."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")

    # 1. Primary: Local Ollama Llama 3.2
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": "json"
        }
        res = _send_request(f"{ollama_host}/api/generate", payload, timeout=45)
        return {"ok": True, "text": res.get("response", "{}"), "model": model}
    except Exception:
        pass

    # 2. Secondary: Remote API (Groq) with json_object mode
    c = config()
    if c["key"]:
        try:
            payload = {
                "model": c["model"],
                "messages": [
                    {"role": "system", "content": system + "\nRespond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            res = _send_request(f"{c['base']}/chat/completions", payload, headers={"Authorization": f"Bearer {c['key']}"}, timeout=20)
            return {"ok": True, "text": res.get("choices", [{}])[0].get("message", {}).get("content", "{}"), "model": c["model"]}
        except Exception:
            pass

    return {
        "ok": False,
        "error": "LLM generation unavailable",
        "model": "template"
    }
