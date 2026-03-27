# XJTLU Marks Rank Estimator

A lightweight Streamlit web app to estimate ranking from MTH007 and MTH013 scores.

## Features

- Input two course scores and estimate rank instantly.
- Uses a normal-distribution-based combined model.
- Fixed correlation coefficient: rho = 0.75.
- Plot labels are in English to avoid cloud font issues.
- Visual deployment error help page in Streamlit pages.
- Semi-automatic Cloud log diagnosis with prioritized repair checklist.
- One-click version/changelog generation via Release Center.
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

- Base population: 3009.
- Means and estimated std are derived from grouped score tables.
- Ranking is computed from upper-tail probability of combined score distribution.

## Smoke Test

Use score 93 / 93 with rho 0.75:

- Expected rank around #240.
