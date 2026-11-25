"""Minimal ILFF container reader used by the MEF converter vertical slice.

Layout (all little-endian) is taken from the supplied IGI_MEF_CONV archive:
`tools/dconv/plugins/mef/reader_ilff.py` and `tools/dconv/utils/ilff.py`.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = ["Chunk", "ILFFError", "ILFFReader"]


class ILFFError(ValueError):
    """Raised for malformed ILFF headers or chunk tables."""


@dataclass(frozen=True)
class Chunk:
    fourcc: bytes
    data: bytes
    offset: int
    datasize: int
    align: int
    chunksize: int


class ILFFReader:
    def __init__(self, data: bytes):
        if len(data) < 20:
            raise ILFFError("ILFF file shorter than the 20-byte outer header")
        sig, declared_size, align, skip, form = struct.unpack_from("<4s3I4s", data, 0)
        if sig != b"ILFF":
            raise ILFFError(f"expected ILFF signature, got {sig!r}")
        if declared_size != len(data):
            raise ILFFError(
                f"ILFF size field {declared_size} does not match file size {len(data)}"
            )
        if align != 4 or skip != 0:
            raise ILFFError(f"unsupported ILFF align/skip: {align}/{skip}")
        self.form = form
        self.chunks: list[Chunk] = []
        offset = 20
        while offset < len(data):
            if offset + 16 > len(data):
                raise ILFFError(f"truncated chunk header at 0x{offset:X}")
            fourcc, size, chunk_align, chunk_size = struct.unpack_from(
                "<4s3I", data, offset
            )
            start = offset + 16
            end = start + size
            if end > len(data):
                raise ILFFError(
                    f"{fourcc!r} at 0x{offset:X} declares {size} bytes beyond EOF"
                )
            self.chunks.append(
                Chunk(fourcc, data[start:end], offset, size, chunk_align, chunk_size)
            )
            # The 4th header field is the byte distance to the next chunk when
            # nonzero; otherwise payload size is used (archive reader_ilff.py).
            offset = offset + chunk_size if chunk_size > 16 else end
            if chunk_size > 16 and offset > len(data):
                raise ILFFError(f"chunk link at 0x{offset:X} runs past EOF")

    def first(self, fourcc: bytes) -> Chunk | None:
        return next((c for c in self.chunks if c.fourcc == fourcc), None)

    def all(self, fourcc: bytes) -> list[Chunk]:
        return [c for c in self.chunks if c.fourcc == fourcc]

    def require(self, fourcc: bytes) -> Chunk:
        chunk = self.first(fourcc)
        if chunk is None:
            raise ILFFError(f"missing required chunk {fourcc!r}")
        return chunk
