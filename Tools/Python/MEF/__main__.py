"""CLI: python3 -m Tools.Python.MEF input.mef output.obj [--sidecar bones.json]"""

from __future__ import annotations

import argparse
from pathlib import Path

from .ilff import ILFFError
from .mef import from_bytes
from .obj import write_outputs


def main() -> int:
    p = argparse.ArgumentParser(description="Convert an IGI 1 MEF to OBJ (vertical slice)")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sidecar", type=Path, help="write per-vertex bone data JSON")
    args = p.parse_args()

    try:
        model = from_bytes(args.input.read_bytes())
    except ILFFError as exc:
        p.error(str(exc))
    write_outputs(
        model,
        args.output,
        args.sidecar,
        name=args.input.stem,
    )
    print(
        f"model_type={model.header.model_type} vertices={len(model.vertices)} "
        f"faces={len(model.faces)} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
