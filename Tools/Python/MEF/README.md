# IGI 1 MEF converter — Python vertical slice

A small, dependency-free Python reader/export path for IGI 1 `.MEF` models,
added for [issue #6](https://github.com/heaven-hm/project-igi-research/issues/6).
It is a research tool: it reads ILFF chunks, decodes `HSEM`, `D3DR`, `DNER` and
`XTRV`, and writes OBJ plus an optional JSON sidecar with per-vertex bone
indices/weights.

## Usage

```sh
python3 -m Tools.Python.MEF input.mef output.obj --sidecar bones.json
```

Run from the repository root; no third-party packages are required.

```sh
python3 -m unittest discover -s Tools/Python/MEF/tests -v
```

## Provenance

* The issue links [`IGI_MEF_CONV.7z`](https://www.mediafire.com/file/dgya95p5eqtcmbq/IGI_MEF_CONV.7z/file).
  The downloaded archive is 377,715,229 bytes, SHA-256
  `26c9bf085047ae1f6add5fdc27edba8a72a03800e2cebef39840da9559f1a3f9`.
  It contains a large dconv tool tree plus retail-derived assets. **Neither the
  archive nor any game asset is checked in here.**
* Layouts were read from these files in the archive (not copied verbatim):
  * `tools/dconv/plugins/mef/IGI1_mef_struct.py`, SHA-256
    `dfa9e4bca97274b15241a68a9a8410050ced833ad70bbe4743d8116bac30b233`
  * `tools/dconv/plugins/mef/reader_ilff.py`, SHA-256
    `de28a267ed74d0ce33aed3bb4573f0b92c8bb4c419a0fd81556a8fa8c3f33a6e`
  * `tools/dconv/plugins/mef/IGI1_mef_type_bone.py`, SHA-256
    `ebbe1e4e65694c41131dbf2aa9793726416157b1f06e68a419af257215a10175`
  * `tools/dconv/plugins/mef/IGI1_mefc_type_bone.py`, SHA-256
    `89423178252e3771a668995a20bc6f32571d5d0a748e966525d5641bfa39991b`
* Repository sources: `Templates/IGI1/IGI1_MEF.bt` and
  `Research/MEF/MEF_REFERENCE.md`.
* The archive has no explicit license file for its Python tree; this is an
  independent, minimal implementation of documented field layouts, not a
  redistribution of that code.

## Scope and limits

This is intentionally a **vertical slice**, not the full archive converter:
* Supports `model_type` 0 (rigid), 1 (bone) and 3 (lightmap) vertex strides.
* Reads render mesh faces from `DNER` and applies its `off_verts` index offset.
* Does **not** resolve bone-relative positions, material textures, 3ds Max
  scripts, collision meshes or portals. Bone names live in animations, so the
  sidecar carries indices only and invents no names.
* Uncertain fields are not renamed or interpreted beyond what the sources
  establish; see `Research/MEF/MEF_PYTHON_CONVERTER.md`.
