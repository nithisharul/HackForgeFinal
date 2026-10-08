"""
ClaimShield Nexus - Local LLM Engine (Llama 3.2)
Communicates with local Ollama runtime on port 11434.
"""

import os
import json
import urllib.request
import urllib.error

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_MODEL = "llama3.2"

def generate(prompt: str, system: str = "") -> dict:
    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json"
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        # Bypass Windows system proxy resolution which stalls on localhost
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        with opener.open(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            raw_text = result.get("response", "{}")
            return {
                "ok": True,
                "text": raw_text,
                "model": DEFAULT_MODEL
            }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "model": "template"
        }
