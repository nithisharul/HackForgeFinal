import hashlib


def create_hash(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()



def hash_log_entry(timestamp, case_id, user, action, previous_hash):
    data = "|".join([
        timestamp,
        case_id,
        user,
        action,
        previous_hash
    ])

    return create_hash(data)



def verify_entry(entry):
    expected_hash = hash_log_entry(
        entry["timestamp"],
        entry["case_id"],
        entry["user"],
        entry["action"],
        entry["previous_hash"]
    )

    return expected_hash == entry["current_hash"]


def verify_log_chain(entries):
    previous_hash = ""

    for index, entry in enumerate(entries):

        # Check that this entry points to the correct previous entry
        if entry["previous_hash"] != previous_hash:
            return {
                "valid": False,
                "broken_entry": index + 1,
                "reason": "Previous hash does not match"
            }

        # Check that this entry itself has not been changed
        if not verify_entry(entry):
            return {
                "valid": False,
                "broken_entry": index + 1,
                "reason": "Entry data has been changed"
            }

        # This entry's hash becomes the next entry's previous hash
        previous_hash = entry["current_hash"]

    return {
        "valid": True,
        "broken_entry": None,
        "reason": "Log chain is valid"
    }


import json
from pathlib import Path


LOG_FILE = Path(__file__).parent / "investigation_log.jsonl"


def append_log_entry(timestamp, case_id, user, action):
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        with LOG_FILE.open("r", encoding="utf-8") as file:
            last_line = file.readlines()[-1]
            last_entry = json.loads(last_line)
            previous_hash = last_entry["current_hash"]
    else:
        previous_hash = ""

    current_hash = hash_log_entry(
        timestamp,
        case_id,
        user,
        action,
        previous_hash
    )

    entry = {
        "timestamp": timestamp,
        "case_id": case_id,
        "user": user,
        "action": action,
        "previous_hash": previous_hash,
        "current_hash": current_hash
    }

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")

    return entry