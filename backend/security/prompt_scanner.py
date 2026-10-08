"""Scan a pasted document before the LLM reads it.

This is one layer, not the whole defence. A keyword scanner can be reworded around. What limits the damage
is the design around it: a document can only add notes or propose a pattern, never change a verdict, a score
or a rule; the LLM is told the document is data; and a signed-in lead must approve the preview.

HIGH findings block the document. MEDIUM findings are shown to the approver, who decides.
"""
import re

PROVIDER = r"(?:provider\s+)?P\d{3}\b"
RULES = [
    ("instruction_override", "HIGH", r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all|system)\b[^.\n]{0,25}\b(instruction|prompt|rule|direction)s?\b"),
    ("role_hijack", "HIGH", r"\b(you are now|act as|pretend to be|new instructions?:|system prompt|developer mode|jailbreak)\b"),
    ("exonerate_provider", "HIGH", rf"\b(always|never|must|should)\b[^.\n]{{0,40}}\b(mark|treat|classify|flag|label|consider|clear)\b[^.\n]{{0,40}}{PROVIDER}"
                                   rf"|{PROVIDER}[^.\n]{{0,40}}\b(must|should|is to)\s+(always|never)\b"),
    ("verdict_tampering", "HIGH", r"\b(change|set|update|overwrite|delete|remove)\b[^.\n]{0,40}\b(verdict|confidence|score|audit log|precedent)s?\b"),
    ("output_control", "MEDIUM", r"\b(respond only with|output only|do not mention|do not tell|without telling|hide this)\b"),
    ("hidden_text", "MEDIUM", r"[​‌‍⁠﻿]|<!--.*?-->|<\s*(script|system|instructions?)\b"),
    ("named_provider", "MEDIUM", rf"{PROVIDER}[^.\n]{{0,60}}\b(safe|legitimate|cleared|trusted|exempt|do not (flag|investigate))\b"
                                 rf"|\b(safe|legitimate|cleared|trusted|exempt)\b[^.\n]{{0,60}}{PROVIDER}"),
]
MESSAGES = {
    "instruction_override": "tells the reader to ignore its instructions",
    "role_hijack": "tries to give the LLM a new role or instructions",
    "exonerate_provider": "instructs how a named provider must always be treated",
    "verdict_tampering": "asks for a verdict, score or log to be changed",
    "output_control": "tries to control or hide what the LLM says",
    "hidden_text": "contains hidden characters, comments or markup",
    "named_provider": "calls a specific provider safe or cleared; a bulletin should not decide a case",
}


def scan(title, text):
    body = f"{title}\n{text}"
    findings = []
    for rule, severity, pattern in RULES:
        m = re.search(pattern, body, re.I | re.S)
        if m:
            start, end = max(0, m.start() - 30), min(len(body), m.end() + 30)
            findings.append({"rule": rule, "severity": severity, "message": MESSAGES[rule],
                             "excerpt": " ".join(body[start:end].split())[:160]})
    blocked = any(f["severity"] == "HIGH" for f in findings)
    return {"verdict": "BLOCKED" if blocked else "SUSPICIOUS" if findings else "SAFE", "blocked": blocked, "findings": findings}
