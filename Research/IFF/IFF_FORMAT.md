# IFF Format (`.iff`)

Skeletal animation / ILFF container format for IGI 1.

> **Extended measurements:** [`IFF_EXTENDED.md`](IFF_EXTENDED.md) documents `TLST`, `BORH`/`BORD`, `PLST`, `BOAH` and `BOED` from a byte-level audit of the sample supplied in [issue #1](https://github.com/heaven-hm/project-igi-research/issues/1), with an auditable tool and synthetic-fixture tests. It also supplies an extended 010 template at `Templates/IGI1/IGI1_IFF_extended.bt`.

**Note on Animations & Skeletons:**
All IFFs have a chunk `REIH` (bone hierarchy). The binary structure is exactly the same as in MEFs `REIH` chunk. However, `MANB` (bone names) are **not** present in IFFs. 

Because IFFs lack bone names, animation exporters must rely on hardcoded bone names based on the skeleton variation. There are two standard variations of skeletons:
* with 31 bones - for 3rd party animations
* with 47 bones - for 1st party animations

**Verification note:** the statements above are inherited community research. The single sample audited in `IFF_EXTENDED.md` (SHA-256 `0c704abab62d23cc4a088778e8e06958a9b2be3de4f41921b317bfb35151b051`) contains **33 bones**, no `MANB` chunk, and no literal `REIH` chunk — its hierarchy is in `PLST` (`parent` indices) and `TLST` (bone translations). The 31/47-bone variants remain unconfirmed by that sample.
