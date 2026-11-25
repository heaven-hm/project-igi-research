# Python MEF converter — implementation notes and verification

Added for [issue #6](https://github.com/heaven-hm/project-igi-research/issues/6),
which asked for the Python MEF converter from
[`IGI_MEF_CONV.7z`](https://www.mediafire.com/file/dgya95p5eqtcmbq/IGI_MEF_CONV.7z/file)
to be added to the research collection.

## What was verified

The archive was downloaded (377,715,229 bytes, SHA-256
`26c9bf085047ae1f6add5fdc27edba8a72a03800e2cebef39840da9559f1a3f9`) and its
Python tree inspected. The archive contains retail-derived MEF samples under
`Resource/IGI 1/Binary/{Rigid Models,Bone Models}/`. Those samples were used
**as local evidence only**; they are not committed to this repository and no
user-owned asset is required by the checked-in tests.

A clean-room, dependency-free vertical slice was implemented at
[`Tools/Python/MEF`](../../Tools/Python/MEF):

| File | Role |
|---|---|
| `ilff.py` | 20-byte outer `ILFF` header + 16-byte chunk headers; little-endian; validates declared size, align, links |
| `mef.py` | `HSEM` (156-byte header), `D3DR`, variable-length `DNER`, `XTRV` strides 32/40/40 for model types 0/1/3 |
| `obj.py` | OBJ vertices/UVs/normals/faces + JSON sidecar of per-vertex bone index/weight/local ID |
| `__main__.py` | CLI entry point `python3 -m Tools.Python.MEF <in.mef> <out.obj> [--sidecar bones.json]` |
| `tests/test_mef_converter.py` | Seven synthetic-fixture unit tests; no retail asset needed |

## Measured acceptance evidence

### Synthetic fixtures

```sh
python3 -m unittest discover -s Tools/Python/MEF/tests -v
```

Result: **7 tests, OK** (0 failures, 0 errors). Tests cover ILFF header and
chunk table, bad signature/size rejection, rigid vertex decoding, bone index
and weight retention, field-size validation, OBJ/sidecar output and the CLI.

### Retail-derived samples from the supplied archive

Each sample was parsed and the number of render vertices/faces produced by the
new reader was compared with the counts declared in its own `HSEM` header:

| Set | Files | Parsed successfully | Exact `HSEM` vertex+face count match |
|---|---:|---:|---:|
| `Resource/IGI 1/Binary/Rigid Models/*.mef` | 428 | 428 | 428 |
| `Resource/IGI 1/Binary/Bone Models/*.mef` | 126 | 126 | 126 |

Worked examples (SHA-256 of the sample, for reproducibility):

| Sample | Model type | HSEM faces / verts | Parsed faces / verts |
|---|---:|---:|---:|
| `1007_01_1.mef` (`db7ec8e2037a86d68a704bbdad4fec232fe8e943baf7fde279eecfa8ed9616fa`, 1,488 B) | 0 (rigid) | 8 / 10 | 8 / 10 |
| `000_01_5.mef` (`d717ba900a024239109695bee73a6c706259475e9c3b67859be5b630e64a80ac`, 13,264 B) | 1 (bone) | 91 / 305 | 91 / 305 |

Both files parse as `ILFF`/`OCEM`. The rigid sample's chunk order is
`HSEM, ATTA, XTVM, TROP, XVTP, CFTP, D3DR, DNER, XTRV, HSMC, XTVC, ECFC,
TAMC, HPSC, XTVC, ECFC, TAMC, HPSC`; the bone sample omits collision chunks.

### Layout corrections found while measuring

* `HSEM` is **156 bytes**, not 152: `float version; uint32 date[7]; uint32
  model_type; uint32 reserved[3]; float vectors[12]; uint32 counts[6]; float
  radius; uint16 counts[5]; uint8 reserved[22]`. The counts at offsets 96/100
  are `num_render_faces` / `num_render_verts`; magic-vertex and attachment
  counts are the `uint16`s at 124/126. This matches real files and the
  issue-#7 template's field names.
* `DNER`'s `num_face` field counts 16-bit face indices (2 bytes each), so a
  rigid/bone record is 28 + 2 × `num_face` bytes and a lightmap record is
  32 + 2 × `num_face` bytes, following the archive's `load_dner`.
* This slice groups consecutive index triples into triangles only after the
  `off_verts` adjustment; the original converter performs additional
  3ds Max-specific index corrections that are out of scope here.

## Not claimed

The slice does not produce the archive's 3ds Max `.mcs` scripts, texture
lookups, bone-relative world coordinates, collision geometry or portal data.
"Converts a MEF" here means: parse the documented render mesh and emit OBJ plus
bone-index metadata. No live-game or 3ds Max import result is asserted.
