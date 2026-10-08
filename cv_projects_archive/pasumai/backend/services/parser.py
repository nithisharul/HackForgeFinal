import re
import json
import requests
from typing import Dict, Any

def parse_farmer_intent(text: str) -> Dict[str, Any]:
    if not text:
        text = "2.5 acres plowing in Guduvanchery"
    
    cleaned = text.strip()
    lower = cleaned.lower()

    # 1. Try local Ollama if active (quick 2s timeout)
    try:
        payload = {
            "model": "llama3.2",
            "prompt": (
                f"Extract structured agriculture demand JSON from this farmer query: '{cleaned}'. "
                "Keys: acres (float), task (string), crop (string), machinery_needed (string), "
                "seeds_and_inputs (string or null), irrigation_window (string or null). Return ONLY valid JSON."
            ),
            "stream": False,
            "format": "json"
        }
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=2.0)
        if res.status_code == 200:
            parsed = json.loads(res.json().get("response", "{}"))
            if parsed.get("acres") or parsed.get("task"):
                return {
                    "acres": float(parsed.get("acres", 2.5)),
                    "task": str(parsed.get("task", "Plowing & Land Prep")).title(),
                    "crop": str(parsed.get("crop", "Paddy")).title(),
                    "village": "Guduvanchery",
                    "machinery_needed": str(parsed.get("machinery_needed", "1x Sonalika 45HP Tractor")),
                    "seeds_and_inputs": parsed.get("seeds_and_inputs"),
                    "irrigation_window": parsed.get("irrigation_window"),
                    "engine": "Ollama (llama3.2)"
                }
    except Exception:
        pass

    # 2. Resilient Heuristic Edge Parser
    # Extract acres (looks for numbers near acre/ac/ekad or standalone)
    acre_match = re.search(r"(\d+(\.\d+)?)\s*(acre|acres|ac|ekad|ha|hectare)?", lower)
    detected_acres = 2.5
    if acre_match:
        try:
            val = float(acre_match.group(1))
            if 0.1 <= val <= 200:
                detected_acres = val
        except ValueError:
            detected_acres = 2.5

    # Tractor / Machinery detection
    machinery = "1x Sonalika 45HP Tractor + Implement"
    trac_match = re.search(r"(\d+)\s*(tractor|tractors)", lower)
    if trac_match:
        count = trac_match.group(1)
        machinery = f"{count}x Tractors (Cluster Fleet Dispatch)"
    elif "harvester" in lower or "combine" in lower:
        machinery = "1x Preet 987 Combine Harvester"
    elif "laser" in lower or "level" in lower:
        machinery = "1x 45HP Tractor + Laser Land Leveler (LLL)"
    elif "rotavator" in lower or "tiller" in lower:
        machinery = "1x 45HP Tractor + 7-Tyne Rotavator"

    # Task detection
    task = "Plowing & Land Prep"
    if any(k in lower for k in ["harvest", "reap", "cutting"]):
        task = "Harvesting"
    elif any(k in lower for k in ["sow", "seed", "planting", "drill"]):
        task = "Precision Sowing"
    elif any(k in lower for k in ["level", "laser"]):
        task = "Laser Land Leveling"
    elif any(k in lower for k in ["irrigat", "water", "pump"]):
        task = "Irrigation Dispatch"

    # Crop detection
    crop = "Paddy"
    crops_catalog = ["banana", "groundnut", "peanut", "wheat", "paddy", "rice", "sugarcane", "cotton", "maize", "corn", "tomato"]
    for c in crops_catalog:
        if c in lower:
            crop = c.title()
            break

    # Seeds / inputs detection
    inputs_pooled = None
    input_match = re.search(r"(\d+\s*(?:kg|bags?|liters?|quintals?))\s*([a-zA-Z\s]+)?", lower)
    if input_match:
        inputs_pooled = input_match.group(0).strip().title()
    elif "seed" in lower or "விதை" in lower:
        inputs_pooled = f"Certified {crop} Seeds (50 kg)"
    elif "urea" in lower or "fertilizer" in lower or "dap" in lower:
        inputs_pooled = "Nano-Urea + DAP Cluster Allocation"

    # Irrigation / time window
    irrigation_window = None
    time_match = re.search(r"(\d{1,2}\s*(?:am|pm)?\s*(?:to|-)\s*\d{1,2}\s*(?:am|pm))", lower)
    if time_match:
        irrigation_window = f"Solar Pump Slot: {time_match.group(1).upper()}"
    elif any(k in lower for k in ["solar", "pump", "irrigation", "water", "பாசனம்"]):
        irrigation_window = "Solar Pump Slot: 06:00 - 10:00"

    return {
        "acres": detected_acres,
        "task": task,
        "crop": crop,
        "village": "Guduvanchery",
        "machinery_needed": machinery,
        "seeds_and_inputs": inputs_pooled or f"Certified {crop} (BPT-5204) - 50 kg",
        "irrigation_window": irrigation_window or "Solar Pump Slot: 06:00 - 10:00",
        "engine": "Dynamic Edge Rule (Fallback)"
    }

parse_request = parse_farmer_intent