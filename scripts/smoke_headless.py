#!/usr/bin/env python3
"""Minimal headless smoke test for Bulky.

- Verifies GI imports work.
- Uses FileObject to rename a temp file without launching the UI.
- Prints JSON with status and timings.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure repo paths are importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "usr" / "lib" / "bulky"))

start = time.time()
result = {
    "ok": False,
    "steps": [],
    "tmpdir": None,
    "old_name": None,
    "new_name": None,
    "elapsed_ms": None,
}

try:
    import gi  # noqa: F401
    from bulky import FileObject  # type: ignore

    result["steps"].append("imports_ok")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result["tmpdir"] = str(tmp_path)

        old = tmp_path / "smoke_original.txt"
        new = "smoke_renamed.txt"
        old.write_text("bulky smoke test", encoding="utf-8")
        result["old_name"] = old.name
        result["new_name"] = new

        fo = FileObject(str(old), scale=1)
        if not fo.is_valid:
            raise RuntimeError("FileObject invalid")

        fo.rename(new)
        renamed_path = old.parent / new
        if not renamed_path.exists():
            raise RuntimeError("Rename did not persist")

        result["steps"].append("rename_ok")
        result["ok"] = True

except Exception as exc:  # noqa: BLE001
    result["error"] = str(exc)

finally:
    result["elapsed_ms"] = round((time.time() - start) * 1000, 2)
    print(json.dumps(result))
