"""OBJ export plus a bone-index sidecar for the MEF vertical slice.

This is deliberately a *vertical slice*: it writes render vertices and the
face indices found in DNER. The original archive converter additionally
resolves bone-relative coordinates, material textures and 3ds Max scripts;
those steps are out of scope here and are not silently approximated.
"""

from __future__ import annotations

import json
from pathlib import Path

from .mef import MefModel

__all__ = ["export_obj", "export_sidecar"]


def _fmt(value: float) -> str:
    return f"{value:.6f}"


def export_obj(model: MefModel, name: str = "model") -> str:
    lines = [f"# IGI 1 MEF -> OBJ (vertical slice) model={name}",
             f"# model_type={model.header.model_type}",
             "o " + name]
    for v in model.vertices:
        lines.append(f"v {_fmt(v.x)} {_fmt(v.y)} {_fmt(v.z)}")
    for v in model.vertices:
        lines.append(f"vt {_fmt(v.u)} {_fmt(v.v)}")
    for v in model.vertices:
        lines.append(f"vn {_fmt(v.nx)} {_fmt(v.ny)} {_fmt(v.nz)}")
    lines.append("usemtl default")
    for a, b, c in model.faces:
        # OBJ indices are 1-based; MEF indices are 0-based.
        lines.append(f"f {a+1}/{a+1}/{a+1} {b+1}/{b+1}/{b+1} {c+1}/{c+1}/{c+1}")
    return "\n".join(lines) + "\n"


def export_sidecar(model: MefModel) -> str:
    """Per-vertex bone indices/weights (bone models) as JSON.

    IGI 1 stores bone hierarchy in the animation file, so this sidecar carries
    indices only; it does not invent bone names or world-space offsets.
    """
    payload = {
        "model_type": model.header.model_type,
        "vertex_count": len(model.vertices),
        "bone_indices": [v.bone_index for v in model.vertices],
        "bone_weights": [v.weight for v in model.vertices],
        "local_vertex_ids": [v.local_vertex_id for v in model.vertices],
    }
    return json.dumps(payload, indent=2) + "\n"


def write_outputs(model: MefModel, obj_path: Path, sidecar_path: Path | None = None,
                  name: str = "model") -> None:
    obj_path.write_text(export_obj(model, name), encoding="utf-8")
    if sidecar_path is not None:
        sidecar_path.write_text(export_sidecar(model), encoding="utf-8")
