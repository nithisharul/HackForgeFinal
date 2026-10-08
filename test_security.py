from backend.security.log_integrity import (
    hash_log_entry,
    verify_entry,
    verify_log_chain
)


# -----------------------------
# ENTRY 1
# -----------------------------

entry1 = {
    "timestamp": "10:00",
    "case_id": "P274",
    "user": "investigator_01",
    "action": "Created",
    "previous_hash": ""
}

entry1["current_hash"] = hash_log_entry(
    entry1["timestamp"],
    entry1["case_id"],
    entry1["user"],
    entry1["action"],
    entry1["previous_hash"]
)


# -----------------------------
# ENTRY 2
# -----------------------------

entry2 = {
    "timestamp": "10:15",
    "case_id": "P274",
    "user": "investigator_01",
    "action": "Reviewed",
    "previous_hash": entry1["current_hash"]
}

entry2["current_hash"] = hash_log_entry(
    entry2["timestamp"],
    entry2["case_id"],
    entry2["user"],
    entry2["action"],
    entry2["previous_hash"]
)


# -----------------------------
# ENTRY 3
# -----------------------------

entry3 = {
    "timestamp": "10:30",
    "case_id": "P274",
    "user": "investigator_01",
    "action": "Escalated",
    "previous_hash": entry2["current_hash"]
}

entry3["current_hash"] = hash_log_entry(
    entry3["timestamp"],
    entry3["case_id"],
    entry3["user"],
    entry3["action"],
    entry3["previous_hash"]
)


# -----------------------------
# SHOW THE CHAIN
# -----------------------------

print("ENTRY 1")
print(entry1)

print("\nENTRY 2")
print(entry2)

print("\nENTRY 3")
print(entry3)


# -----------------------------
# VERIFY
# -----------------------------

print("\nVERIFICATION")

print("Entry 1:", verify_entry(entry1))
print("Entry 2:", verify_entry(entry2))
print("Entry 3:", verify_entry(entry3))



print("\n--- SIMULATING TAMPERING ---")

entry2["action"] = "Cleared"

print("Entry 1:", verify_entry(entry1))
print("Entry 2:", verify_entry(entry2))
print("Entry 3:", verify_entry(entry3))



print("\n--- WHOLE CHAIN VERIFICATION ---")

result = verify_log_chain([
    entry1,
    entry2,
    entry3
])

print(result)



from backend.security.log_integrity import append_log_entry

print("\n--- REAL LOG TEST ---")

new_entry = append_log_entry(
    "11:00",
    "P274",
    "investigator_01",
    "Verdict: confirmed"
)

print(new_entry)


second_entry = append_log_entry(
    "11:05",
    "P274",
    "investigator_01",
    "Case reviewed"
)

print(second_entry)