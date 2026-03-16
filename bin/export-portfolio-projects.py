#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controller.projects_registry import export_projects  # noqa: E402


def main() -> int:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    result = export_projects(destination)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
