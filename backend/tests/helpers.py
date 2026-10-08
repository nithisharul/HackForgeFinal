"""Shared fixtures for API tests that must never touch the real Second Brain or .env."""
import dataclasses
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from backend import region
from backend.app import auth
from backend.brain import llm

SECRET = "t" * 48
INVESTIGATOR = "Test Investigator"
PASSCODE = "correct horse battery"


def isolated_wiki(test):
    """Point both regions' knowledge folders at a throwaway copy for the duration of one test."""
    tmp = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    shutil.copytree(region.ROOT / "knowledge", tmp / "knowledge")  # same layout, so repo-relative paths still resolve
    regions = {code: dataclasses.replace(r, know=tmp / r.know.relative_to(region.ROOT)) for code, r in region.REGIONS.items()}
    for patcher in (mock.patch.dict(region.REGIONS, regions), mock.patch.object(region, "ROOT", tmp)):
        patcher.start()
        test.addCleanup(patcher.stop)
    return regions


def signed_in(test):
    """Configure one known investigator (overriding .env) and return a bearer header for them."""
    llm._env()  # load .env first, so the patch below wins and is fully undone afterwards
    patcher = mock.patch.dict(os.environ, {"AUTH_SECRET": SECRET,
                                           "INVESTIGATORS": f"{INVESTIGATOR}:{auth.hash_passcode(PASSCODE, iterations=1000)}"})
    patcher.start()
    test.addCleanup(patcher.stop)
    return {"Authorization": f"Bearer {auth.login(INVESTIGATOR, PASSCODE)['token']}"}
