# Reading the book's charts into data

The site redraws charts as SVG from a YAML data file (example: `figures/charts/p0063-1.yaml`). Two readers (A and B)
transcribe each chart **independently**; their files are compared value by value. **Accuracy is everything** — a value
you can't read must say so in `notes`, never be guessed silently.

## Input
The charts listed in `work/charts/batch.json` — per chart: `figure`, `unit`, `crop` (300 dpi image), `labels_en` (the
English wording of every label printed in the chart, already translated — use these words), `caption_en`.
Open each crop with the Read tool. Zoom into regions with Pillow (crop + resize 2–3×, save to your scratchpad, Read it).
The full page is `source/pages/NNNN/scan.jpg` if you need context.

## Output
`work/charts/read_<READER>.yaml` — a YAML list, one entry per chart, written as you go:

```yaml
- id: p0568-1
  type: grouped-bar            # grouped-bar | line
  title: {de: "A1- und A2A-Rezeptoraffinitäten von Coffein und Theophyllin", en: "A1 and A2A receptor affinities of caffeine and theophylline"}
  x_axis: {de: "Rezeptor", en: "Receptor"}          # axis title as printed; null if none
  y_axis: {de: "Ki [µM]", en: "Ki [µM]", min: 0, max: 50, ticks: [0, 10, 20, 30, 40, 50]}
  series:                                            # legend order as printed
    - {key: caf, de: "Coffein", en: "Caffeine"}
    - {key: theo, de: "Theophyllin", en: "Theophylline"}
  values_printed: true         # true: every value is printed on the chart and transcribed; false: measured
  categories:                  # grouped-bar: x categories in printed order, one value per series key
    - {de: "A1", en: "A1", caf: 12, theo: 8.5}
    - {de: "A2A", en: "A2A", caf: 2.4, theo: 25}
  notes: ""                    # anything uncertain, per value
```

For `type: line` use `x_axis` with `min`, `max`, `ticks` like `y_axis`, and instead of `categories`:
```yaml
  points:                      # per series key: [x, y] pairs in order, only where a marker/vertex is drawn
    training: [[1, 2], [2, 25], ...]
```

## Rules
1. **Printed values win.** When a number is printed on/above a bar, transcribe it exactly (keep decimals as printed,
   "0.7" not "0.70"). Assign each printed number to the right bar: check its horizontal position against the bars.
2. **Measured values** (nothing printed): measure from pixels — find the axis ticks' pixel rows, fit the scale (at
   least two ticks, check a third), then the bar top / marker centre. Correct for a tilted photo if the baseline is
   not level. Round to a sensible precision for the scale (state it in `notes`, e.g. "measured, ±2"). Set
   `values_printed: false`, and put the measurement method in `notes`.
3. A bar that is drawn but has no value and can't be measured → value `null` plus a note. A category with no bar for a
   series → `null`.
4. Axis `min`/`max`/`ticks` exactly as printed (a broken or non-zero axis, e.g. 36–40.5 °C, stays as printed).
5. Series keys: short ASCII (`rac`, `R`, `S`, `2C`, `3C`, `O`, `S_`, `nacl` …). German text exactly as printed in `de`;
   English from `labels_en` (fix only obvious OCR slips there, and say so).
6. Charts that turn out not to hold data (a schematic curve, an illustration) → one entry with `type: none` and a note
   why; don't invent values.

## Self-check (required)
Check your file parses (`scriptorium python -c "import yaml; yaml.safe_load(open('work/charts/read_<READER>.yaml'))"`),
that every category has a value (or null) for every series key, and re-read every chart once more against your numbers.

## Don'ts
- Don't read the other reader's file or `figures/charts/`. Edit nothing but your own file (scratch in your scratchpad).
- Don't look values up in the cited papers — this is what the book prints.

## Final reply
Short: charts done, which were measured (and precision), every uncertain value (chart, category, series, why).
