"""Synthetic-fixture tests for the IFF chunk auditor.

Run with: python3 -m unittest discover -s Tools/IFF -p 'test_*.py'
No retail IFF sample is required or checked in.
"""

from __future__ import annotations

import struct
import unittest

from iff_chunk_audit import IFFError, audit, walk


def be_chunk(fourcc: bytes, payload: bytes) -> bytes:
    return fourcc + struct.pack(">I", len(payload)) + payload


def form(form_type: bytes, body: bytes) -> bytes:
    return be_chunk(b"FORM", form_type + body)


def le32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def build_sample(num_bones: int = 33, rotation_keys: int = 2, overrun: bool = True) -> bytes:
    bosh = le32(0) + le32(num_bones)
    plst = b"".join(le32(0xFFFFFFFF if i == 0 else i - 1) for i in range(num_bones))
    tlst = struct.pack("<" + "f" * (3 * num_bones), *range(3 * num_bones))

    skeleton = form(b"BOBH", be_chunk(b"BOSH", bosh) + be_chunk(b"PLST", plst)
                    + be_chunk(b"TLST", tlst))

    boah = le32(0x464F8000) + le32(0) + le32(123)
    botd = struct.pack("<10f", 1.0, 2.0, 3.0, 0.0, *([0.0] * 6))
    bod = struct.pack("<13f", *([0.5] * 13)) * rotation_keys
    anim = form(
        b"BOAN",
        be_chunk(b"BOAH", boah)
        + be_chunk(b"BOTH", le32(1))
        + be_chunk(b"BOTD", botd)
        + be_chunk(b"BORH", le32(rotation_keys))
        + be_chunk(b"BORD", bod)
        + be_chunk(b"BOEH", le32(0))
        + be_chunk(b"BOED", b""),
    )

    animations = form(b"BOAL", be_chunk(b"BALH", le32(1) + le32(123)) + anim)

    # The real sample's first FORM declares a size shorter than the BOAL FORM
    # it contains. Reproduce that quirk so the reader's de-duplication is
    # exercised; with overrun=False both FORMs are independent top-level chunks.
    if overrun:
        declared = 8 + len(skeleton) + 16  # parent ends 8 bytes into the BOAL FORM
        return b"FORM" + struct.pack(">I", declared) + b"BOBJ" + skeleton + animations
    return form(b"BOBJ", skeleton + animations)


class AuditorTests(unittest.TestCase):
    def test_chunk_headers_are_big_endian_payloads_little_endian(self):
        data = build_sample()
        chunks = walk(data)
        bosh = next(c for c in chunks if c.fourcc == "BOSH")
        self.assertEqual(
            struct.unpack_from("<II", data, bosh.offset + 8), (0, 33)
        )
        self.assertNotEqual(
            struct.unpack_from(">II", data, bosh.offset + 8), (0, 33)
        )

    def test_chunk_walk_is_unique_even_when_form_child_overruns_parent(self):
        data = build_sample(overrun=True)
        counts = {c.fourcc: sum(1 for x in walk(data) if x.fourcc == c.fourcc)
                  for c in walk(data)}
        self.assertEqual(counts["FORM"], 4)  # outer, BOBJ, BOAL, BOAN
        self.assertEqual(counts["BORH"], 1)
        self.assertEqual(counts["BORD"], 1)
        self.assertEqual(counts["BOAH"], 1)

    def test_bord_count_matches_borh_size_relation(self):
        for keys in (1, 2, 7):
            result = audit(build_sample(rotation_keys=keys))
            self.assertTrue(result["pass"], result)
            self.assertEqual(result["borh_bord_size_mismatches"], 0)
            self.assertEqual(result["bord_records"], keys)

    def test_row_sizes_and_anim_counts(self):
        result = audit(build_sample(num_bones=33))
        self.assertEqual(result["chunk_counts"]["PLST"], 1)
        self.assertEqual(result["chunk_counts"]["TLST"], 1)
        self.assertEqual(result["botd_records"], 1)
        self.assertEqual(result["boed_records"], 0)
        self.assertEqual(result["boah_anims"], 1)
        self.assertEqual(result["boah_unique_ids"], 1)

    def test_borh_count_disagreement_is_reported(self):
        data = bytearray(build_sample())
        borh = next(c for c in walk(bytes(data)) if c.fourcc == "BORH")
        struct.pack_into("<I", data, borh.offset + 8, 3)  # BORD still has 2
        result = audit(bytes(data))
        self.assertFalse(result["pass"])
        self.assertEqual(result["borh_bord_size_mismatches"], 1)
        self.assertEqual(result["checks"]["no_bord_size_mismatch"], False)

    def test_truncated_chunk_raises(self):
        with self.assertRaises(IFFError):
            walk(b"FORM" + struct.pack(">I", 999) + b"BOBJ")


if __name__ == "__main__":
    unittest.main()
