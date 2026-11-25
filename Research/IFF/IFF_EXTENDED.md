# IGI 1 `.IFF` — extended format notes (evidence-backed)

This document extends [`IFF_FORMAT.md`](IFF_FORMAT.md) in response to
[heaven-hm/project-igi-research#1](https://github.com/heaven-hm/project-igi-research/issues/1),
which asked for documentation of `TLST` and `BORH`, an answer on whether IFFs
contain bones, and more detail than Artiom Rotari's original short note.

**Scope:** one supplied sample was measured byte-by-byte. Statements below are
marked as *measured* when they come from that file and as *inherited* when they
come from earlier community research that this audit could not re-verify.
No claim is made about every retail animation or about the 31/47-bone variants.

---

## 1. Provenance

| Source | What it supplied | Identifier / SHA-256 |
|---|---|---|
| Issue #1 attachment `000.zip` → `000.iff` | The only binary sample audited here | [`000.zip`](https://github.com/user-attachments/files/18921477/000.zip), file SHA-256 `0c704abab62d23cc4a088778e8e06958a9b2be3de4f41921b317bfb35151b051`, 1,512,568 bytes |
| Issue #1 attachment `IGI1_IFF_binarytemplate.zip` → `IFF.bt` | Community template with named `BOSH/PLST/TLST/BOAH/BOTH/BOTD/BORH/BORD/BOED` payloads; starting point for `Templates/IGI1/IGI1_IFF_extended.bt` | [`IGI1_IFF_binarytemplate.zip`](https://github.com/user-attachments/files/24150793/IGI1_IFF_binarytemplate.zip), template SHA-256 `743d304706d96d9cd2058e792749cd63db1ccd8d797bb5faef34030697214405` |
| Repo baseline | Original `Research/IFF/IFF_FORMAT.md` and `Templates/IGI1/IGI1_IFF.bt` by Rotari Artiom (the latter treats all payloads as opaque `DFLT`) | this repository, `main` @ `9d11faf` |
| Issue #1 discussion | The maintainer explicitly rejected an unverified ChatGPT-generated layout ("you need to verify it from Game internal files first"); this audit follows that rule | issue #1 comments, 2024-12-01 |
| Research portal | Published summary describing IFF as a skeletal-animation container | `https://project-igi-research.vercel.app/igi1` (external, consulted for context only) |

The sample is **not** checked into this repository. The audit is reproducible
from `Tools/IFF/iff_chunk_audit.py` against any user-supplied file; the tests use
synthetic fixtures and need no game assets.

---

## 2. Measured chunk facts

Produced by:

```sh
python3 Tools/IFF/iff_chunk_audit.py /path/to/000.iff
python3 -m unittest discover -s Tools/IFF -p 'test_*.py'
```

Result for the sample above (all 11 tests/JSON checks pass):

| Chunk | Count | Payload size | Records | Notes |
|---|---:|---:|---:|---|
| `FORM` | 125 | varies | — | Types: 1 × `BOBJ` (outer), 1 × `BOBH` (skeleton), 1 × `BOAL` (animation list), 122 × `BOAN` (animation) |
| `BOSH` | 1 | 8 | 1 | `typeAnims = 0`, `numBones = 33` (little-endian) |
| `PLST` | 1 | 132 | 33 | Parent indices; first is `0xFFFFFFFF` (root), rest point to earlier bones |
| `TLST` | 1 | 396 | 33 | Three `float` per bone: rest translation in model units |
| `BALH` | 1 | 8 | 1 | `numAnims = 122`, `lastAnimID = 247` |
| `BOAH` | 122 | 12 | 122 | 122 distinct animation IDs (matches `BALH.numAnims`) |
| `BOTH` | 122 | 4 | 122 | Translation-key count for the animation |
| `BOTD` | 122 | multiples of 40 | 1,027 | 40 bytes per translation key; all sizes divisible by 40 |
| `BORH` | 4,026 | 4 | 4,026 | Rotation-key count for the following `BORD` |
| `BORD` | 4,026 | multiples of 52 | 26,535 | **`BORD.size == 52 × BORH.count` for 4,026/4,026 pairs** (0 mismatches) |
| `BOEH` | 122 | 4 | 122 | Event count |
| `BOED` | 122 | multiples of 24 | 73 | 24 bytes per event; all sizes divisible by 24 |

The file's last chunk ends exactly at EOF. No unrecognised FourCC appears.

### Endianness and nesting

* The outer and inner `FORM` headers are **big-endian**: the first header is
  `46 4f 52 4d 00 00 02 4c` (`FORM`, 588 bytes), while `BOSH.numBones` is
  little-endian (`21 00 00 00` = 33).
* A `FORM` payload starts with a 4-byte form type; sub-chunks follow.
* The `BOAL` `FORM` at offset `0x248` declares a payload size (1,508,564) whose
  end coincides with EOF and **runs past the enclosing `BOBJ` FORM's declared
  end** (`0x254`). A reader must seek by the child's own size; clamping to the
  parent loses the animation data or reads it twice. The auditor and the
  extended 010 template both implement this behaviour.

---

## 3. Chunk reference

Offsets are relative to the chunk payload. Confidence is explicit.

| FourCC | Size / record | Layout | Confidence |
|---|---|---|---|
| `FORM` | 4 + child chunks | Big-endian `size`; payload = form type (`BOBJ`, `BOBH`, `BOAL`, `BOAN`) + chunks | Measured |
| `BOSH` | 8 | `uint32 typeAnims`, `uint32 numBones` (LE) | Measured (`0, 33`) |
| `PLST` | 4 | `int32 parent[size/4]`; `-1` = root | Measured count and first value; parent semantics inferred from monotonic indices |
| `TLST` | 12 | `float px, py, pz` per bone | Measured count and plausible coordinates; "rest position" is an interpretation |
| `BALH` | 8 | `uint32 numAnims`, `uint32 lastAnimID` (LE) | Measured (`122, 247`); second field name is a label, not proven semantics |
| `BOAH` | 12 | word0 (`uint32`), `{uint16, uint16}`, uint32 ID (LE) | Bytes measured. Reading word0 as `float` gives integral values (13280.0, 11200.0, …); its unit is **unknown**. The high half of word1 is `0x8000` in some animations and 0 in others |
| `BOTH` | 4 | `uint32` translation-key count (LE) | Measured |
| `BOTD` | 40 | `float px, py, pz, time`, `float unknown[6]` | Size relation measured; first record is `(−310.28, 3.92, 3877.22, 0.0, 0, …, 0)`, so field meanings beyond the first four remain tentative |
| `BORH` | 4 | `uint32` rotation-key count (LE) | Measured via exact `BORD` size relation |
| `BORD` | 52 | 13 × `float`; first record `[-0.0403, -0.01669, -0.38232, 0.923, 0.0, -0.0403, -0.01669, -0.38232, 0.923, -0.0403, -0.01669, -0.38232, 0.923]` | Record size measured; the first four floats look like a quaternion (norm ≈ 1), but the repeated triples and trailing zero are **not** proven to be three keyframes |
| `BOEH` | 4 | `uint32` count (LE) | Measured |
| `BOED` | 24 | `int32 eventID`, `int32 boneID`, `float time`, `float px, py, pz` | Record size measured; field names inherited from the issue #1 template and not independently verified |

### What is **not** established

* No `MANB` (bone-name) chunk exists in the sample. This matches the baseline
  note that IFFs lack bone names, so exporters need names from elsewhere.
* The baseline note says "all IFFs have a `REIH` chunk". The audited sample has
  **no literal `REIH`**; the hierarchy is expressed by `PLST` and translations
  by `TLST`. Treat `REIH`-based statements as inherited, not verified here.
* The baseline 31-bone / 47-bone skeleton variants were not supplied. This
  sample has **33 bones** (`BOSH.numBones`, `PLST` entries and `TLST` records all
  agree), so the two-variant claim cannot be confirmed from this evidence.
* `BOAH` duration units, the extra `BOTD` floats and the `BORD` sub-structure
  require a second sample or engine-side evidence before they can be asserted.

---

## 4. Artifacts

* [`Templates/IGI1/IGI1_IFF_extended.bt`](../../Templates/IGI1/IGI1_IFF_extended.bt)
  — 010 Editor template implementing the table above; leaves uncertain fields
  with neutral names.
* [`Tools/IFF/iff_chunk_audit.py`](../../Tools/IFF/iff_chunk_audit.py) —
  reproducible chunk walk + invariant checks, emits JSON.
* [`Tools/IFF/test_iff_chunk_audit.py`](../../Tools/IFF/test_iff_chunk_audit.py)
  — six synthetic-fixture unit tests (no retail asset required).

### Answer to issue #1

Yes: an IFF carries bone-related data — parent indices (`PLST`), bone
translations (`TLST`) and per-bone rotation tracks (`BORH`/`BORD`) — but the
audited file carries **no bone names**, and no `REIH` chunk was observed. `TLST`
contains 33 twelve-byte records; `BORH` is a four-byte count whose value equals
the number of 52-byte records in the following `BORD` chunk.
