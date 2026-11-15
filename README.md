# Navidya – JNVST (Navodaya) Class 6 Mock Tests

Free mock tests for the Jawahar Navodaya Vidyalaya Selection Test (Class VI), built from **real previous-year papers**.
Booklet-style pages, OMR answer sheet, countdown timer with a bell every 30 minutes, instant section-wise result and answer review.

Pure static site (HTML + CSS + JS, no build step, no server, no external libraries) – works on GitHub Pages and on any phone/tablet/desktop browser.

## Go live on GitHub Pages

1. Merge this branch into `main`.
2. Repo → **Settings → Pages → Build and deployment → Source: “Deploy from a branch” → Branch: `main` / `(root)` → Save.**
3. After about a minute the site is live at `https://<username>.github.io/Navidya/`.

## Papers

| Paper | Exam date | Booklet | Status |
|---|---|---|---|
| JNVST 2026 | 13 Dec 2025 | IB266D ENGL – E | **Full paper**: 80 Q with real figures, official NVS key |
| JNVST 2025 | 18 Jan 2025 | SS256J ENGL – D | Section II + III (39 Q; Q53 left out). Mental Ability figures not added yet |
| JNVST 2024 | 20 Jan 2024 | VS246J ENGL – J | Section II + III (38 Q; figure-based Q41, Q42 left out). Mental Ability figures not added yet |
| JNVST 2023 | 29 Apr 2023 | NJ623 ENGL – J | Section II + III (40 Q). Mental Ability figures not added yet |
| JNVST 2022 | 30 Apr 2022 | AP ENGL – G | Section II + III (40 Q). Mental Ability figures not added yet |
| JNVST 2021 | 11 Aug 2021 | APST21 ENGL – W | Section II + III (40 Q). Mental Ability figures not added yet |

The Mental Ability section (Q1–40) is entirely figure-based, so it needs a scan of each booklet. Only the Dec 2025 booklet scan was available;
for 2021–2025 drop the paper PDFs into the repo and cut the figures with `tools/crop.py` (answer keys for those sets are already in `tools/KEYS.md`).

See `papers/` for the data and `tools/` for how it is produced.

## Adding / completing a paper

* Text questions live in `tools/src/<year>.txt` (one line per question: `41. question | A | B | C | D`, fractions as `{3/4}`, passages start with `#P`).
* Mental Ability figures are cut out of a scanned booklet with `tools/crop.py` (see `tools/crop2026.py` for a worked example) into `papers/<year>/qNN.png`.
* Add `@key1 <40 letters>` to the `.txt`, then run `python3 tools/build.py` – it regenerates `papers/<year>/paper.js` and `papers/index.js`.

Requires Python 3 with `pillow`, `numpy` and (for PDF scans) `pymupdf`.

## Notes

* Question papers are © Navodaya Vidyalaya Samiti. This site is an unofficial free practice tool.
* The real papers above follow the old pattern (Mental Ability 40 + Arithmetic 20 + Language 20). JNVST 2027 (28 Nov 2026) uses a new pattern with an EVS section; see `research/NOTES.md`.
