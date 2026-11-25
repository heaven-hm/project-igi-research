# IGI 1 bone-model MEF notes (issue #7)

These notes accompany the bone-model changes to
[`Templates/IGI1/IGI1_MEF.bt`](../../Templates/IGI1/IGI1_MEF.bt) made for
[issue #7](https://github.com/heaven-hm/project-igi-research/issues/7).
They separate what was measured from what was inherited.

## 1. Provenance

| Source | Use | SHA-256 / identifier |
|---|---|---|
| Issue #7 attachment `IGI1_MEF_fullinfo.zip` → `IGI1_MEF.bt` | Community-proposed "full info" template: named `HSEM` fields, `DNER_0/DNER_3`, a 40-byte `XTRV` case with `w/vn/bn`, `XTVC.bn` | [`IGI1_MEF_fullinfo.zip`](https://github.com/user-attachments/files/28190689/IGI1_MEF_fullinfo.zip), template SHA-256 `6327a81009b2c1d8db0d6920d7fba11dbab3f80cadb1bd8b68fc3ebec377dd2c` |
| Archive linked in issue #6, `tools/dconv/plugins/mef/IGI1_mef_struct.py` | Authoritative field list for `HSEM`, `XTRV_0/1/3`, `XTVC`, `ECFC`, `DNER` | SHA-256 `dfa9e4bca97274b15241a68a9a8410050ced833ad70bbe4743d8116bac30b233`; archive SHA-256 `26c9bf085047ae1f6add5fdc27edba8a72a03800e2cebef39840da9559f1a3f9` |
| Repository `Templates/IGI2/IGI2_MEF.bt` | Layout of `REIH` / `MANB` recursive bone structs | this repo |
| Retail-derived samples inside the issue #6 archive, `Resource/IGI 1/Binary/Bone Models/*.mef` | Local verification of chunk sets, strides and bone indices | not committed; used only as evidence |

The attachment's template is **not** copied wholesale: it inlines its own
common includes, names a field `n_bone` without sample evidence, and has no
`REIH`/`MANB` cases. The repository template keeps its original includes and
`hsem.mt` switch contract.

## 2. Measured facts from 126 IGI 1 bone samples

| Observation | Result |
|---|---|
| `HSEM` payload size | 156 bytes in the parsed samples. Counts `num_r_faces` / `num_r_verts` at offsets 96/100; magic/attachment counts are `uint16` at 124/126 |
| Outer form | `ILFF` / `OCEM`, little-endian chunk headers |
| Common chunk set | `HSEM, ATTA, XTVM, TROP, XVTP, CFTP, D3DR, DNER` in 126/126 samples |
| `XTRV` present | 122/126 samples (4 samples in the archive end with a non-FourCC chunk and were not used for vertex statistics) |
| `XTRV` payload stride | 40 bytes in 122/122 bone samples with `XTRV` (no remainder) |
| Render counts | `HSEM.num_render_faces` / `num_render_verts` matched the independently parsed `DNER` face count and `XTRV` vertex count in 126/126 samples |
| Bone index field | `XTRV` bytes 36..37 (`bn`) spans many values; maximum per model ranges well beyond 48 (e.g. 176, 421, 486, 581), so a hardcoded 48/49-bone table is not universally applicable |
| `REIH` / `MANB` chunks | **not present** in any of the 126 samples. Bone names therefore cannot be read from the model file; they come from the animation side (see `Research/IFF/IFF_EXTENDED.md`) |
| Collision chunks | `HSMC` occurs 26 times; `XTVC/ECFC/TAMC/HPSC` occur 52 times — two collision layers in 26 samples |

Worked example: `000_01_5.mef` (13,264 bytes, SHA-256
`d717ba900a024239109695bee73a6c706259475e9c3b67859be5b630e64a80ac`) is
`model_type = 1`, has 305 render vertices and 91 render faces, both matching
`HSEM`, and declares no `REIH` or `MANB`.

## 3. Template changes and their status

| Change | Evidence status |
|---|---|
| Named `HSEM` counts via comments; kept original field names and 156-byte size | Measured against archive samples and `IGI1_mef_struct.py` |
| `XTRV` case 1 separated from case 3: `pos(3), normal(3), u, v, w, uint16 vn, uint16 bn` | Measured stride; `w/vn/bn` names inherited from the issue #7 attachment and archive struct, not independently proven semantic labels |
| `DNER` walked as variable-length records (`28 + 2*num_face`, or `32 + 2*num_face` for lightmaps) | Measured: all 554 rigid+bone samples matched `HSEM` counts with this walk |
| `XTVC` fourth field named `bn`; `ECFC` fields named `a,b,c,_mat` | Inherited from the issue #7 attachment; record sizes match archive structs |
| Optional `REIH` and `MANB` structs and root cases | Adapted from `IGI2/IGI2_MEF.bt`; **not observed in IGI 1 samples**. Provided only so such a file would not hit `Assert(false)` |
| `HSEM._f` labelled "bone-count candidate" | Explicitly tentative; the audited samples have zero there |

### Verification performed

* Structural check of `IGI1_MEF.bt`: braces `44/44`, parentheses `52/52`,
  brackets `25/25`; required tokens present (`case 1:`, `U2 bn;`, `REIH`,
  `MANB`, `DNER_0`, `DNER_3`).
* The equivalent layouts are exercised by the Python reader in
  [`Tools/Python/MEF`](../../Tools/Python/MEF), whose tests pass (7/7) and
  which matched `HSEM` counts on 428 rigid + 126 bone samples.
* **Not performed:** execution in 010 Editor (not available in this
  environment). No claim is made that the template was rendered or parsed by
  010 Editor; only the structural check above was run.

## 4. Practical consequence for bone models

For the audited IGI 1 bone models, a template must:
1. use the 40-byte `XTRV` case for `model_type == 1` (the old template read
   those bytes as a second UV set);
2. walk `DNER` records by their own `num_face` length rather than assuming
   `d3dr.mn` fixed-size records;
3. not require `REIH`/`MANB` to be present; bone names are resolved from the
   animation file, not the model.
