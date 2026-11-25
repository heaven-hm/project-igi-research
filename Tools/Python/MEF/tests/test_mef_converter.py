"""Synthetic-fixture tests for the IGI 1 MEF converter vertical slice.

Run with: python3 -m unittest discover -s Tools/Python/MEF/tests -v
No retail MEF sample is required or checked in.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from Tools.Python.MEF.ilff import ILFFError, ILFFReader
from Tools.Python.MEF.mef import MODEL_BONE, MODEL_RIGID, from_bytes, parse_hsem, parse_xtrv
from Tools.Python.MEF.obj import export_obj, export_sidecar


def chunk(fourcc: bytes, payload: bytes) -> bytes:
    return fourcc + struct.pack("<3I", len(payload), 4, 0) + payload


def make_hsem(model_type: int) -> bytes:
    data = bytearray(156)
    struct.pack_into("<f", data, 0, 0.16)
    struct.pack_into("<7I", data, 4, 2026, 11, 26, 4, 12, 0, 0)
    struct.pack_into("<I", data, 32, model_type)
    struct.pack_into("<I", data, 96, 2)  # num render faces
    struct.pack_into("<I", data, 100, 3)  # num render verts
    struct.pack_into("<H", data, 124, 0)  # magic verts
    struct.pack_into("<H", data, 126, 0)  # attachments
    return bytes(data)


def make_d3dr(model_type: int) -> bytes:
    if model_type == MODEL_RIGID:
        return struct.pack("<4I8I", 4, 2, 1, 3, *([0] * 8))
    return struct.pack("<6I8I", 4, 2, 1, 0, 3, 3, *([0] * 8))


def make_xtrv(model_type: int) -> bytes:
    out = bytearray()
    for i in range(3):
        pos = (float(i), float(i + 1), float(i + 2))
        normal = (0.0, 0.0, 1.0)
        if model_type == MODEL_RIGID:
            out += struct.pack("<8f", *pos, *normal, i / 3, 1.0)
        else:
            out += struct.pack("<9f2H", *pos, *normal, i / 3, 1.0, 0.5, i, 7)
    return bytes(out)


def make_dner() -> bytes:
    # 28-byte rigid/bone header + six uint16 indices = two triangles.
    header = struct.pack("<3f6H", 1.0, 2.0, 3.0, 6, 0xFFFF, 0, 0, 3, 0)
    return header + b"\x00\x00\x00\x00" + struct.pack("<6H", 0, 1, 2, 1, 2, 3)


def make_mef(model_type: int) -> bytes:
    body = (
        chunk(b"HSEM", make_hsem(model_type))
        + chunk(b"D3DR", make_d3dr(model_type))
        + chunk(b"DNER", make_dner())
        + chunk(b"XTRV", make_xtrv(model_type))
    )
    return b"ILFF" + struct.pack("<3I4s", 20 + len(body), 4, 0, b"OCEM") + body


class ConverterTests(unittest.TestCase):
    def test_ilff_header_and_chunk_table(self):
        data = make_mef(MODEL_RIGID)
        reader = ILFFReader(data)
        self.assertEqual(reader.form, b"OCEM")
        self.assertEqual([c.fourcc for c in reader.chunks],
                         [b"HSEM", b"D3DR", b"DNER", b"XTRV"])
        self.assertEqual(len(reader.require(b"HSEM").data), 156)

    def test_ilff_rejects_bad_signature_and_bad_size(self):
        with self.assertRaises(ILFFError):
            ILFFReader(b"NOPE" + make_mef(MODEL_RIGID)[4:])
        bad = bytearray(make_mef(MODEL_RIGID))
        struct.pack_into("<I", bad, 4, 999)
        with self.assertRaises(ILFFError):
            ILFFReader(bytes(bad))

    def test_hsem_and_rigid_vertices(self):
        model = from_bytes(make_mef(MODEL_RIGID))
        self.assertEqual(model.header.model_type, MODEL_RIGID)
        self.assertEqual(model.header.date[:3], (2026, 11, 26))
        self.assertEqual(len(model.vertices), 3)
        self.assertEqual((model.vertices[1].x, model.vertices[1].y), (1.0, 2.0))
        self.assertAlmostEqual(model.vertices[1].u, 1 / 3)
        self.assertEqual(model.faces, [(0, 1, 2), (1, 2, 3)])

    def test_bone_vertices_keep_indices_and_weights(self):
        model = from_bytes(make_mef(MODEL_BONE))
        self.assertEqual(model.header.model_type, MODEL_BONE)
        self.assertEqual([v.bone_index for v in model.vertices], [7, 7, 7])
        self.assertEqual([v.local_vertex_id for v in model.vertices], [0, 1, 2])
        self.assertTrue(all(abs(v.weight - 0.5) < 1e-6 for v in model.vertices))

    def test_vertex_stride_validation(self):
        with self.assertRaises(ILFFError):
            parse_xtrv(b"\x00" * 33, MODEL_RIGID)
        with self.assertRaises(ILFFError):
            parse_hsem(b"\x00" * 155)

    def test_obj_and_sidecar_output(self):
        model = from_bytes(make_mef(MODEL_BONE))
        obj = export_obj(model, "rig")
        self.assertIn("o rig", obj)
        self.assertEqual(obj.count("\nv "), 3)
        self.assertEqual(obj.count("\nvt "), 3)
        self.assertEqual(obj.count("\nf "), 2)
        self.assertIn("f 1/1/1 2/2/2 3/3/3", obj)
        side = json.loads(export_sidecar(model))
        self.assertEqual(side["bone_indices"], [7, 7, 7])
        self.assertEqual(side["vertex_count"], 3)

    def test_cli_writes_both_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "sample.mef"
            obj_path = Path(tmp) / "sample.obj"
            side_path = Path(tmp) / "bones.json"
            src.write_bytes(make_mef(MODEL_BONE))
            proc = subprocess.run(
                [sys.executable, "-m", "Tools.Python.MEF", str(src), str(obj_path),
                 "--sidecar", str(side_path)],
                cwd=Path(__file__).resolve().parents[4],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("model_type=1 vertices=3 faces=2", proc.stdout)
            self.assertTrue(obj_path.exists())
            self.assertEqual(json.loads(side_path.read_text())["model_type"], 1)


if __name__ == "__main__":
    unittest.main()
