# XJTLU Marks Rank Estimator

A lightweight Streamlit web app to estimate ranking from MTH007 and MTH013 scores.

## Features

- Input two course scores and estimate rank instantly.
- Integer-only inputs for scores and total population.
- Default initial inputs: `0`, `0`, `3006`.
- Uses a discrete distribution model built from grouped frequency tables.
- Ranking rule is competition rank (same score, same rank; next rank skips).
- Model path: A+B (percentile lookup first, then linear interpolation inside segments).
- Second calibration enabled: high-score tail inflation to reduce top-end rank collapse.
- Fixed correlation coefficient: rho = 0.75.
- Quantized scoring model: `quantized_score = score / 100`, so input 100 gives 1.
- Plot labels are in English to avoid cloud font issues.
- Visual deployment error help page in Streamlit pages.
- Semi-automatic Cloud log diagnosis with prioritized repair checklist.
- Cloud log file upload (.txt/.log) and confidence scoring.
- One-click export for diagnosis report.
- One-click version/changelog generation via Release Center.
- One-click deploy pipeline (preflight + add/commit/push) via Release Center.
- Lightweight runtime analytics (in-memory, no database).

## Local Run

1. Install dependencies:

```bash
python -m pip install -r GradeEstimate/requirements.txt
```

2. Start app:

```bash
python -m streamlit run GradeEstimate/app.py
```

Optional preflight check before deploy:

```bash
python GradeEstimate/preflight_check.py
```

One-click release assets:

```bash
python GradeEstimate/release_tools.py
```

One-click deploy (CLI):

```bash
python GradeEstimate/deploy_tools.py --remote xjtlu-marks --branch master
```

Tip: for the first deployment, bind repository in Streamlit Community Cloud manually once; afterwards, each push triggers auto-redeploy.

3. Open browser:

- http://localhost:8501

## Streamlit Community Cloud Deploy

1. Push project to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app and select repository `xxxyz1949/xjtlu-marks`.
4. Set main file path to:

- `GradeEstimate/app.py`

5. Click Deploy.

After app starts, open the Streamlit page named `Cloud Checklist` in the left page list and tick items one by one.

## Model Notes

- Base population is fixed at 3006 in the current UI.
- Maximum score is treated as 100 for quantization.
- Joint average-score distribution is constructed from grouped frequencies of MTH007 and MTH013.
- Main ranking path is data-driven discrete lookup (A) with optional segment interpolation (B).
- Secondary calibration adjusts high-score tail for better separation near 98-100.
- Competition rank is computed by strict higher-score ratio: `rank = floor(total * P(score > x)) + 1`.
- Hard constraint: `100/100 -> rank #1`.

## Smoke Test

Suggested checks:

- `100/100` should always return `#1`.
- Same input score pair should return exactly the same rank across runs.
- High-score inputs like `98/100` should be more stable than Gaussian-tail behavior.
