#!/usr/bin/env python3
"""Audit an IGI 1 .IFF chunk tree without loading engine assets.

The reader is a direct transcription of the layout measured in issue #1's
000.iff sample (SHA-256 0c704aba...). Chunk headers are big-endian; payload
scalars are little-endian. No game asset is required to run the self-tests.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

__all__ = ["IFFError", "Chunk", "audit", "walk"]


class IFFError(ValueError):
    """Raised when a chunk tree cannot be read consistently."""


class Chunk:
    __slots__ = ("offset", "fourcc", "size", "depth", "form_type")

    def __init__(self, offset: int, fourcc: str, size: int, depth: int, form_type: str | None):
        self.offset = offset
        self.fourcc = fourcc
        self.size = size
        self.depth = depth
        self.form_type = form_type

    def as_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "fourcc": self.fourcc,
            "size": self.size,
            "depth": self.depth,
            "form_type": self.form_type,
        }


def _u32(data: bytes, offset: int, endian: str = ">") -> int:
    if offset + 4 > len(data):
        raise IFFError(f"truncated 32-bit field at 0x{offset:X}")
    return struct.unpack_from(endian + "I", data, offset)[0]


def walk(data: bytes) -> list[Chunk]:
    """Return every chunk in file order, following FORM form-type payloads.

    A FORM child may declare an end beyond its parent's declared end (observed
    in the sample). We use a visited-offset set so such a child is not read
    again from the enclosing level.
    """
    chunks: list[Chunk] = []
    seen: set[int] = set()

    def visit(start: int, end: int, depth: int) -> int:
        offset = start
        while offset + 8 <= min(end, len(data)):
            if offset in seen:
                break
            seen.add(offset)
            fourcc = data[offset : offset + 4].decode("latin1")
            size = _u32(data, offset + 4)
            payload = offset + 8
            if payload + size > len(data):
                raise IFFError(
                    f"{fourcc} at 0x{offset:X} declares {size} bytes beyond EOF"
                )
            form_type = (
                data[payload : payload + 4].decode("latin1")
                if fourcc == "FORM" and size >= 4
                else None
            )
            chunks.append(Chunk(offset, fourcc, size, depth, form_type))
            if fourcc == "FORM":
                child_end = visit(payload + 4, payload + size, depth + 1)
                end = max(end, child_end)
                if child_end > offset:
                    # A FORM child may run past its parent's declared end.
                    # Skip to the child's real end instead of re-reading the
                    # bytes from the enclosing level.
                    offset = child_end
                    continue
            offset = payload + size
        return end

    visit(0, len(data), 0)
    return chunks


def audit(data: bytes) -> dict[str, Any]:
    """Compute reproducible chunk facts and check sample-derived invariants."""
    chunks = walk(data)
    by_cc: dict[str, list[Chunk]] = collections.defaultdict(list)
    for chunk in chunks:
        by_cc[chunk.fourcc].append(chunk)

    borh = by_cc.get("BORH", [])
    bord = by_cc.get("BORD", [])
    botd = by_cc.get("BOTD", [])
    boed = by_cc.get("BOED", [])
    boah = by_cc.get("BOAH", [])

    pairs = list(zip(borh, bord))
    size_mismatches = [
        {"offset": h.offset, "count": _u32(data, h.offset + 8, "<"), "size": d.size}
        for h, d in pairs
        if d.size != 52 * _u32(data, h.offset + 8, "<")
    ]

    facts: dict[str, Any] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "file_bytes": len(data),
        "chunk_counts": dict(sorted((k, len(v)) for k, v in by_cc.items())),
        "form_types": dict(
            sorted(collections.Counter(c.form_type for c in by_cc.get("FORM", [])).items())
        ),
        "borh_bord_pairs": len(pairs),
        "borh_bord_size_mismatches": len(size_mismatches),
        "bord_records": sum(c.size // 52 for c in bord),
        "botd_records": sum(c.size // 40 for c in botd),
        "botd_size_multiple_of_40": all(c.size % 40 == 0 for c in botd),
        "boed_records": sum(c.size // 24 for c in boed),
        "boed_size_multiple_of_24": all(c.size % 24 == 0 for c in boed),
        "boah_anims": len(boah),
        "boah_unique_ids": len(
            {_u32(data, c.offset + 16, "<") for c in boah}
        ),
        "checks": {
            "ends_at_eof": bool(chunks)
            and chunks[-1].offset + 8 + chunks[-1].size == len(data),
            "no_bord_size_mismatch": not size_mismatches,
            "no_unknown_fourcc": not (
                set(by_cc)
                - {
                    "FORM", "BOSH", "PLST", "TLST", "BALH", "BOAH", "BOTH",
                    "BOTD", "BORH", "BORD", "BOEH", "BOED",
                }
            ),
        },
        "mismatches": size_mismatches[:10],
    }
    facts["pass"] = all(facts["checks"].values())
    return facts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iff", type=Path, help="path to an IGI 1 .IFF file")
    parser.add_argument("--json", type=Path, help="write audit JSON here")
    args = parser.parse_args()

    data = args.iff.read_bytes()
    result = audit(data)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
