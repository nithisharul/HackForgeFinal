"""Sign-in and token checks that guard every write.

    python -m unittest discover -s backend/tests -t .
"""
import base64
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from backend.app import auth

SECRET = "s" * 48
FAST = auth.hash_passcode("correct horse battery", iterations=1000)


def configured(users=f"Asha Rao:{FAST}", secret=SECRET):
    return mock.patch.dict(os.environ, {"AUTH_SECRET": secret, "INVESTIGATORS": users})


class Passcodes(unittest.TestCase):
    def test_right_and_wrong_passcodes(self):
        self.assertTrue(auth.check_passcode("correct horse battery", FAST))
        self.assertFalse(auth.check_passcode("correct horse batterY", FAST))

    def test_malformed_stored_hash_never_matches(self):
        for stored in ("", "plain-text", "md5$1$aa$bb", "pbkdf2_sha256$x$zz$yy"):
            self.assertFalse(auth.check_passcode("anything", stored))

    def test_hash_is_salted(self):
        self.assertNotEqual(auth.hash_passcode("same passcode", iterations=1000), auth.hash_passcode("same passcode", iterations=1000))


class Sessions(unittest.TestCase):
    def setUp(self):
        auth._failures.clear()

    def login(self, name="Asha Rao", passcode="correct horse battery"):
        return auth.login(name, passcode)

    def test_login_gives_a_token_for_the_registered_name(self):
        with configured():
            s = self.login(name="  asha   RAO ")
            self.assertEqual(s["investigator"], "Asha Rao")
            self.assertEqual(auth.require_investigator(f"Bearer {s['token']}"), "Asha Rao")

    def test_wrong_passcode_and_unknown_name_are_refused_alike(self):
        with configured():
            for name, code in (("Asha Rao", "wrong passcode!"), ("Nobody Here", "correct horse battery")):
                with self.assertRaises(HTTPException) as e:
                    self.login(name, code)
                self.assertEqual((e.exception.status_code, e.exception.detail), (401, "Unknown investigator or wrong passcode"))

    def test_missing_or_non_bearer_header_is_refused(self):
        with configured():
            token = self.login()["token"]
            for header in ("", token, f"Basic {token}", "Bearer ", "Bearer not.a.token"):
                with self.assertRaises(HTTPException) as e:
                    auth.require_investigator(header)
                self.assertEqual(e.exception.status_code, 401)

    def test_tampered_token_is_refused(self):
        with configured():
            body, mac = self.login()["token"].split(".")
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            payload["sub"] = "Someone Else"
            forged = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
            self.assertIsNone(auth.verify(f"{forged}.{mac}"))

    def test_token_signed_with_another_key_is_refused(self):
        with configured(secret="a" * 48):
            token = self.login()["token"]
        with configured(secret="b" * 48):
            self.assertIsNone(auth.verify(token))

    def test_expired_token_is_refused(self):
        with configured():
            token = self.login()["token"]
            with mock.patch.object(auth.time, "time", return_value=time.time() + auth.SESSION_SECONDS + 1):
                self.assertIsNone(auth.verify(token))

    def test_token_of_a_removed_investigator_is_refused(self):
        with configured():
            token = self.login()["token"]
        with configured(users=f"Other Person:{FAST}"):
            self.assertIsNone(auth.verify(token))

    def test_repeated_failures_lock_the_name_then_release_it(self):
        with configured():
            for _ in range(auth.MAX_FAILURES):
                with self.assertRaises(HTTPException):
                    self.login(passcode="wrong passcode!")
            with self.assertRaises(HTTPException) as e:
                self.login()  # right passcode, but locked
            self.assertEqual(e.exception.status_code, 429)
            with mock.patch.object(auth.time, "time", return_value=time.time() + auth.LOCKOUT_SECONDS + 1):
                self.assertEqual(self.login()["investigator"], "Asha Rao")

    def test_writes_are_refused_when_nothing_is_configured(self):
        for env in ({"AUTH_SECRET": "", "INVESTIGATORS": f"Asha Rao:{FAST}"}, {"AUTH_SECRET": SECRET, "INVESTIGATORS": ""},
                    {"AUTH_SECRET": "short", "INVESTIGATORS": f"Asha Rao:{FAST}"}):
            with mock.patch.dict(os.environ, env):
                for call in (lambda: auth.require_investigator("Bearer x.y"), lambda: self.login()):
                    with self.assertRaises(HTTPException) as e:
                        call()
                    self.assertEqual(e.exception.status_code, 503)


class EnvFile(unittest.TestCase):
    def test_add_creates_secret_once_and_updates_without_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("LLM_MODEL=gemma3:4b\n", encoding="utf-8")
            auth.add_investigator("Asha Rao", "first passcode 123", env)
            first = dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines())
            auth.add_investigator("asha  rao", "second passcode 456", env)
            auth.add_investigator("Vikram Shah", "third passcode 789", env)
            second = dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines())
            self.assertEqual(second["LLM_MODEL"], "gemma3:4b")
            self.assertEqual(first["AUTH_SECRET"], second["AUTH_SECRET"])
            self.assertGreaterEqual(len(second["AUTH_SECRET"]), 32)
            users = dict(e.rpartition(":")[::2] for e in second["INVESTIGATORS"].split(";"))
            self.assertEqual(sorted(users), ["Vikram Shah", "asha rao"])
            self.assertTrue(auth.check_passcode("second passcode 456", users["asha rao"]))
            self.assertNotIn("passcode", env.read_text(encoding="utf-8"))

    def test_short_passcodes_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                auth.add_investigator("Asha Rao", "short", Path(d) / ".env")


if __name__ == "__main__":
    unittest.main()
