# Navidya – JNVST (Navodaya) Class 6 Bilingual Mock Tests (हिन्दी / English)

Free **bilingual (Hindi default + live `हिन्दी / English` toggle)** mock tests for the Jawahar Navodaya Vidyalaya Selection Test (Class VI), built from **real previous-year papers** (see the table below for exactly which parts are real).
Booklet-style pages, OMR answer sheet, countdown timer with a bell every 30 minutes, rough-work pad, instant section-wise result, and bilingual answer review with explanations.

Pure static site (HTML + CSS + ES5 JS, no build step, no server, no external libraries) – works on GitHub Pages and on any phone/tablet/desktop browser.

## Go live on GitHub Pages

1. Merge this branch into `main`.
2. Repo → **Settings → Pages → Build and deployment → Source: “Deploy from a branch” → Branch: `main` / `(root)` → Save.**
3. After about a minute the site is live at `https://<username>.github.io/Navidya/`.

## Papers

| Paper | Exam date | Booklet (EN / HI) | Status |
|---|---|---|---|
| JNVST 2026 | 13 Dec 2025 | IB266D ENGL / IB266D HIND – E | **Full paper, all real (EN + HI)**: 80 Q with the booklet's own figures, authentic Hindi & English Section II + III, official NVS key |
| JNVST 2025 | 18 Jan 2025 | SS256J ENGL / SS256J HIND – D | 80 Q: Authentic English & Hindi Section II + III from the real paper; Section I = generated practice figures |
| JNVST 2024 | 20 Jan 2024 | VS246J ENGL / VS246J HIND – J | 80 Q: Section II (EN + Hindi translation, Q41–42 figures redrawn by `tools/draw2024.py`); Section III = real English passages + JNVST-pattern Hindi practice passages (`@langgen`); Section I = generated practice figures |
| JNVST 2023 | 29 Apr 2023 | NJ623 ENGL / NJ623 HIND – J | 80 Q: Authentic English & Hindi Section II + III from the real paper; Section I = generated practice figures |
| JNVST 2022 | 30 Apr 2022 | AP ENGL / AP HIND – G | 80 Q: Section II (EN + Hindi translation); Section III = real English passages + JNVST-pattern Hindi practice passages (`@langgen`); Section I = generated practice figures |
| JNVST 2021 | 11 Aug 2021 | APST21 ENGL / APST21 HIND – W | 80 Q: Authentic English & Hindi Section II + III from the real paper; Section I = generated practice figures |

Every mock is a full 80-question, 100-mark, 2-hour paper.

**About Section I (Mental Ability, Q1–40) of 2021–2025.** That section is entirely figure-based and no usable scan of those booklets was
available, so its 40 questions per paper are **new practice questions drawn as SVG by `tools/matgen.py`** on the real 10-part pattern
(odd one out, figure matching, pattern completion, series, analogy, figure completion, mirror image, paper folding, cut-out pieces, embedded figure).
They are **not** the figures of the original booklets, and the site says so on the paper card, on the cover page and at the top of Section I.
The generator checks every question (the four options are pairwise different, the keyed option follows from the rule) and writes bilingual
Devanagari Hindi (`notes`) and English (`notes_en`) explanations shown in the answer review. To replace them with the real figures later,
cut the scans with `tools/crop.py` into `papers/<year>/qNN.png`, add `@key1` (keys are in `tools/KEYS.md`) and delete `tools/gen/<year>.json`.

**About Section III (Language, Q61–80) Hindi mode in 2022 & 2024.** Where verified Hindi booklet passages were not available online,
`tools/src/2022.txt` and `tools/src/2024.txt` provide original JNVST-pattern Hindi comprehension passages (`@langgen 1`, `@key_hi61`), clearly
disclosed on the cover page and Section III header, and scored against `paper.key_hi`.

See `papers/` for the data and `tools/` for how it is produced.

## Adding / completing a paper

* Text questions live in `tools/src/<year>.txt` (`[ARITH]`/`[LANG]` for English and `[ARITH_HI]`/`[LANG_HI]` for Hindi, one line per question: `41. question | A | B | C | D`, fractions as `{3/4}`, passages start with `#P`).
* Mental Ability figures are either cut out of a scanned booklet with `tools/crop.py` (see `tools/crop2026.py`) into `papers/<year>/qNN.png`
  with `@key1 <40 letters>` in the `.txt`, or generated with `python3 tools/matgen.py <year>` (writes `papers/<year>/qNN*.svg` and `tools/gen/<year>.json`).
* Run `python3 tools/build.py` – it regenerates `papers/<year>/paper.js` and `papers/index.js` with bilingual metadata, sections, keys, and review notes.

Requires Python 3 with `pillow`, `numpy` and (for PDF scans) `pymupdf`.

## Notes

* Question papers are © Navodaya Vidyalaya Samiti. This site is an unofficial free practice tool.
* The real papers above follow the old pattern (Mental Ability 40 + Arithmetic 20 + Language 20). JNVST 2027 (28 Nov 2026) uses a new pattern with an EVS section; see `research/NOTES.md`.
