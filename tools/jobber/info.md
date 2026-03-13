# Information of Applicant 

## Personal info

My name: Dimitrios Mylonas
Timezone:  UTC+2
Availability: Open to remote or relocation
Date of Birth: 1999
Languages
- English: Proficient
- Greek: Native
- German: Basic, A2
Tech stack summary: Python, C/C++, JavaScript/TypeScript, Git, Linux, Windows, Docker, SQL, FastAPI, CI/CD, XGBoost, scikil-learn, numpy, pandas, Seaboarn

## Education

### University of Macedonia - Bachelor
- Location: Greece
- Start Date: 2017
- Business administration
- Dropped out in 2020

### The 42 Network
- Location: Wolfsburg, Germany
- Start Date: 2021
- Stayed there and completed the base curriculum in 2022.
- Projects in systems programming, algorithms, and problem-solving, C and C++.
	- Notable: Built a functional Unix-like shell supporting command parsing, pipes, redirection, environment variables, and process control.
- Applied low-level OS concepts (system calls, signals, file descriptors) and ensured full memory safety through manual management.

### University of Colorado Boulder - Masters
- Master of Science in Data Science
- Enrolled: February 2024; Graduated: August 2025

## Experience

### Google Summer of Code, 2025 — Learning Equality (Educational OSS)
- Led Windows app engineering work across UI, server, and installer components.
- Upgraded legacy IE web view to Edge WebView2 to fix UI hangs/crashes.
- Split UI and server into separate processes for stability.
- Built InnoSetup-based installer + automated build/signing in GitHub Actions.
- Added system tray controls and legacy data migration for upgrades.
- Key PRs: [170](https://github.com/learningequality/kolibri-app/pull/170), [171](https://github.com/learningequality/kolibri-app/pull/171), [182](https://github.com/learningequality/kolibri-app/pull/182), [183](https://github.com/learningequality/kolibri-app/pull/183), [186](https://github.com/learningequality/kolibri-app/pull/186), [188](https://github.com/learningequality/kolibri-app/pull/188)
 - Tech: Python, Windows, WebView2, InnoSetup, GitHub Actions

### Google Summer of Code, 2023 — SugarLabs (Educational OSS)
- Shipped multiple game/activity updates across Python and SugarLabs stack.
- Ported activities to Python 3, fixed crashes, input handling, and UI issues.
- Notable work:
  - Flappy: merge + gameplay polish + collision masking. [PR 18](https://github.com/sugarlabs/flappy/pull/18)
  - 2Cars: Python 3 port + refactor + UI fixes. [PR 14](https://github.com/sugarlabs/2-cars-activity/pull/14)
  - Browse: homepage UI + PDF open fix. [PR 124](https://github.com/sugarlabs/browse-activity/pull/124), [PR 128](https://github.com/sugarlabs/browse-activity/pull/128)
  - Lemonade: regression fixes + help console fixes. [PR 20](https://github.com/sugarlabs/Lemonade/pull/20), [PR 22](https://github.com/sugarlabs/Lemonade/pull/22)
  - Cell Game: flake8 + UI fixes. [PR 12](https://github.com/sugarlabs/cellgame/pull/12)
 - Tech: Python, GTK/Sugar stack


## Projects (outside of GSoC)

Flagship / systems
- [42-minishell](https://github.com/Dimi20cen/42-minishell) — Unix-like shell implementing parsing, pipes, redirection, env expansion, built-ins, and signal handling. Tech: C, POSIX syscalls, readline.
- [42-cub3d](https://github.com/Dimi20cen/42-cub3d) — Ray-casting 3D maze game with texture mapping and map parsing. Tech: C, miniLibX.
- Pathogen_spread_simulation — Agent-based epidemic simulation with adjustable parameters and real-time visualization. Tech: Processing (Java mode).

ML / data
- CEBRA_EEG_pipeline — EEG data classification with classic ML baselines and a GNN extension. Tech: Python, Jupyter, scikit-learn, PyTorch Geometric.
- MSDS_5511-Movie_Review_Sentiment_Analysis — IMDb sentiment analysis using a CNN baseline and DistilBERT fine-tuning. Results: DistilBERT 91.4% acc (F1 0.91), CNN 88.6% acc. Tech: Python, Jupyter, transformers.
- MSDS-5510-2008-crisis — Anomaly detection for market stress in 2007–2009 with Isolation Forest and time-series feature engineering. Tech: Python (pandas, numpy, scikit-learn, matplotlib).
- MSDS-Wine_Quality — Wine quality prediction (score 3–8) with regression + classification, EDA, and model tuning. Best: RF regressor RMSE ~0.59, RF classifier ~0.89 acc. Tech: Jupyter/Python, scikit-learn.
- MSDS-F1_Visualisation — Tableau visualization of F1 Constructors’ Championship dominance (1999–2023) using stacked area charts and team-color encoding. Tech: Tableau.

Other
- HQ — Personal controller/tools suite for automation and utilities. Tech: Python, JavaScript.