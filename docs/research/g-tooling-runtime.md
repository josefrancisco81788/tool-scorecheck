# G. Tooling and runtime

## Findings

### ReportLab is the PDF library to try

Claim: WeasyPrint's Windows instructions require Pango and its dependencies, and name MSYS2 as the easy path (`pacman -S mingw-w64-ucrt-x86_64-pango`). That is a second install beside `pip`, and it breaks a one-command run on a laptop that does not already have those libraries. ReportLab ships wheels. fpdf2 is pure Python with Pillow, defusedxml, and fontTools. Quarto needs a TeX install. The `typst` wheel can embed a compiler, and it is a second typesetting language.

Evidence: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows, https://pypi.org/project/reportlab/, https://pypi.org/project/fpdf2/, accessed 2026-10-24. Quote: "The easiest way to install these libraries is to use MSYS2."

Confidence: `verified`.

ScoreCheck: try ReportLab for the validation pack (tables plus Matplotlib images). If table layout fails a check, try fpdf2 before any HTML-to-PDF tool. Do not add WeasyPrint.

### 50,000 households fits the ten-minute command; 200,000 with monthly refits does not

Claim: 200,000 households × 24 months is 4,800,000 household-month rows. At about 2.5 adults and more than one SIM, a naive SIM-month frame is on the order of 19 million rows and will push a 16 GB laptop into swap if it is a float64 pandas frame. A full outcomes loop that refits two or three boosters every month is on the order of 36 to 72 fits and, on a laptop CPU, is likely to run past ten minutes before charts and the public file. 50,000 households, quarterly refits (six points on the curve), float32, and SHAP on a 10,000-row sample lands in a few minutes.

Evidence: the row counts are arithmetic. The wall-clock bands are engineering estimates from typical LightGBM histogram timings, not a benchmark on this machine. Confidence: row counts `verified`. Minutes `likely`. The first implementation run replaces the estimate with a measured elapsed time in the README.

The ten-minute command also cannot aggregate Home Credit's bureau-balance table (about 27 million rows) and still finish. That aggregation belongs to the full command. See [c-public-dataset.md](c-public-dataset.md).

## Recommendations

- Default scale: 50,000 households, 24 months, quarterly refit, UCI 350 as the public file.
- Full scale: 200,000 households and the Home Credit aggregate.
- The README, the command's first lines of output, and the validation-pack header all state the scale that was run, the seed, and the sentence that 50,000 is the default and 200,000 is the full run. There is no UI yet. The design doc reserves that header so a later screen shows the same sentence.
- Generate household aggregates in numpy. Do not materialise a SIM-month pandas frame for the whole panel.
