"""MEF payload decoding for the converter vertical slice.

Structures mirror `IGI1_mef_struct.py` from the supplied IGI_MEF_CONV archive
and `Templates/IGI1/IGI1_MEF.bt` in this repository. Only the fields needed for
a first OBJ export are exposed; unknown fields stay in `raw` where possible.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .ilff import ILFFError, ILFFReader

__all__ = [
    "MODEL_RIGID", "MODEL_BONE", "MODEL_LIGHTMAP",
    "HSEM", "Vertex", "Mesh", "parse_hsem", "parse_xtrv", "parse_dner",
    "parse_d3dr", "MefModel", "from_bytes",
]

MODEL_RIGID = 0
MODEL_BONE = 1
MODEL_LIGHTMAP = 3

# byte layout: <f 7I 3I 12f 6I 2f 5H 22B  (see IGI1_mef_struct.py)
_HSEM = struct.Struct("<f7I4I12f6If5H22B")
_XTRV0 = struct.Struct("<8f")
_XTRV1 = struct.Struct("<9f2H")
_XTRV3 = struct.Struct("<10f")
_D3DR0 = struct.Struct("<4I8I")
_D3DR1 = struct.Struct("<6I8I")
_D3DR3 = struct.Struct("<7I7I")


@dataclass(frozen=True)
class HSEM:
    version: float
    date: tuple[int, ...]
    model_type: int
    num_render_faces: int
    num_render_verts: int
    num_magic_verts: int
    num_attachments: int

    @property
    def vertex_stride(self) -> int:
        return {MODEL_RIGID: 32, MODEL_BONE: 40, MODEL_LIGHTMAP: 40}[self.model_type]


@dataclass(frozen=True)
class Vertex:
    x: float
    y: float
    z: float
    nx: float = 0.0
    ny: float = 0.0
    nz: float = 0.0
    u: float = 0.0
    v: float = 0.0
    u1: float = 0.0
    v1: float = 0.0
    weight: float = 0.0
    local_vertex_id: int = 0
    bone_index: int = 0


@dataclass(frozen=True)
class Mesh:
    faces: list[tuple[int, int, int]]
    vertices: list[Vertex]


def parse_hsem(data: bytes) -> HSEM:
    if len(data) < _HSEM.size:
        raise ILFFError(f"HSEM needs {_HSEM.size} bytes, got {len(data)}")
    v = _HSEM.unpack_from(data)
    return HSEM(
        version=v[0],
        date=tuple(v[1:8]),
        model_type=v[8],
        num_render_faces=v[24],
        num_render_verts=v[25],
        num_magic_verts=v[31],
        num_attachments=v[32],
    )


def parse_d3dr(data: bytes, model_type: int) -> dict[str, object]:
    fmt = {MODEL_RIGID: _D3DR0, MODEL_BONE: _D3DR1, MODEL_LIGHTMAP: _D3DR3}.get(model_type)
    if fmt is None:
        raise ILFFError(f"unknown model type {model_type}")
    if len(data) < fmt.size:
        raise ILFFError(f"D3DR type {model_type} needs {fmt.size} bytes, got {len(data)}")
    values = fmt.unpack_from(data)
    if model_type == MODEL_LIGHTMAP:
        return {"num_face": values[2], "num_mesh": values[3], "num_vert": values[4]}
    return {"num_face": values[1], "num_mesh": values[2], "num_vert": values[5]}


def parse_xtrv(data: bytes, model_type: int) -> list[Vertex]:
    stride = HSEM(0.0, (), model_type, 0, 0, 0, 0).vertex_stride
    if len(data) % stride:
        raise ILFFError(f"XTRV payload {len(data)} not divisible by {stride}")
    out: list[Vertex] = []
    for offset in range(0, len(data), stride):
        raw = data[offset : offset + stride]
        if model_type == MODEL_RIGID:
            v = _XTRV0.unpack(raw)
            out.append(Vertex(*v[:8]))
        elif model_type == MODEL_LIGHTMAP:
            v = _XTRV3.unpack(raw)
            out.append(Vertex(*v[:8], u1=v[8], v1=v[9]))
        else:
            v = _XTRV1.unpack(raw)
            out.append(
                Vertex(
                    v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7],
                    weight=v[8], local_vertex_id=v[9], bone_index=v[10],
                )
            )
    return out


def parse_dner(data: bytes, model_type: int) -> list[dict[str, object]]:
    """Read the variable-length DNER material/mesh records.

    Header is 28 bytes for rigid/bone models and 32 bytes for lightmap models,
    followed by `num_face` uint16 face indices (archive `load_dner`).
    """
    header_size = 32 if model_type == MODEL_LIGHTMAP else 28
    records: list[dict[str, object]] = []
    offset = 0
    while offset + header_size <= len(data):
        if model_type == MODEL_LIGHTMAP:
            px, py, pz, nface, nextoffs, td, lmap, offverts, nverts, opacity, _ = (
                struct.unpack_from("<3f8H", data, offset)
            )
            flags = data[offset + 28 : offset + 32]
        else:
            px, py, pz, nface, nextoffs, td, offverts, nverts, opacity = (
                struct.unpack_from("<3f6H", data, offset)
            )
            flags = data[offset + 24 : offset + 28]
        face_end = offset + header_size + 2 * nface
        if face_end > len(data):
            raise ILFFError("DNER face list runs past chunk end")
        faces = list(
            struct.unpack_from("<" + "H" * nface, data, offset + header_size)
        ) if nface else []
        records.append(
            {
                "position": (px, py, pz),
                "num_face": nface,
                "next_offset": nextoffs,
                "texture_id": td,
                "vertex_offset": offverts,
                "num_vertex": nverts,
                "opacity": opacity,
                "flags": flags,
                "faces": faces,
            }
        )
        offset = face_end
        if nextoffs == 0xFFFF:
            break
    return records


@dataclass(frozen=True)
class MefModel:
    header: HSEM
    d3dr: dict[str, object]
    vertices: list[Vertex]
    dner: list[dict[str, object]]

    @property
    def faces(self) -> list[tuple[int, int, int]]:
        tris: list[tuple[int, int, int]] = []
        for record in self.dner:
            faces = record["faces"]
            offset = int(record["vertex_offset"])
            for i in range(0, len(faces) - 2, 3):
                tris.append(
                    tuple(int(faces[i + j]) + offset for j in range(3))  # type: ignore[arg-type]
                )
        return tris


def from_bytes(data: bytes) -> MefModel:
    reader = ILFFReader(data)
    if reader.form != b"OCEM":
        raise ILFFError(f"expected OCEM MEF form, got {reader.form!r}")
    header = parse_hsem(reader.require(b"HSEM").data)
    d3dr = parse_d3dr(reader.require(b"D3DR").data, header.model_type)
    vertices = parse_xtrv(reader.require(b"XTRV").data, header.model_type)
    dner = parse_dner(reader.require(b"DNER").data, header.model_type)
    return MefModel(header=header, d3dr=d3dr, vertices=vertices, dner=dner)
