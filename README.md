# DSCI 510 Final Project
## Analyzing November Weather Patterns in Los Angeles

### Team Member
- Xinwei Wang (xwang663@usc.edu)

---

## What this project does

This project checks whether **November 2024** in Los Angeles had unusual precipitation compared to a historical November baseline.  
It uses daily weather data from NOAA (GHCND daily) and produces summary statistics, anomaly detection (z-scores), and plots.

---

## Project location (my setup)

My project folder is located at:

/Users/wangxinwei/Desktop/DSCI510 final project

All commands below assume you run them from the project root directory.

---

## Project structure

- data/raw/  
  Raw files downloaded from NOAA API
- data/processed/  
  Cleaned dataset (la_daily_cdo.csv)
- src/  
  Python scripts for data collection, cleaning, analysis, and visualization
- results/  
  analysis_summary.txt and figures/
- notebook/  
  Xinwei_Wang_DSCI510_Final_Project.ipynb

---

DSCI510 final project/
│
├── data/
│   ├── raw/                # Raw data downloaded from NOAA API
│   └── processed/          # Cleaned daily dataset
│
├── src/
│   ├── get_cdo_daily.py    # Data collection
│   ├── clean_data.py       # Data cleaning
│   ├── run_analysis.py     # Analysis code
│   └── visualize_results.py# Visualization code
│
├── results/
│   ├── figures/            # Output figures
│   └── analysis_summary.txt
│
├── notebook/
│   └── Xinwei_Wang_DSCI510_Final_Project.ipynb
│
├── requirements.txt
└── README.md

---

## 1. Create a virtual environment

This project was run using Anaconda (conda).  
You can either use your existing `base` environment (what I used), or create a separate conda environment.

### Option A (what I used): conda base
Activate base (usually already active if you see `(base)` in Terminal):

conda activate base

### Option B (recommended): create a new conda environment
conda create -n dsci510 python=3.12
conda activate dsci510

---

## 2.  Install required libraries

From the project root directory:

pip install -r requirements.txt

---

## 3.  Get the data (data collection)

This project uses the NOAA Climate Data Online (CDO) API.
You need a NOAA token stored as an environment variable.

Set the token (macOS / zsh):

export NOAA_TOKEN="YOUR_NOAA_TOKEN_HERE"

Then run the data collection script from the project root:

python src/get_cdo_daily.py

Output:
- Raw files saved into: data/raw/

---

## 4.  Clean the data

Run:

python src/clean_data.py

Output:
- Cleaned dataset saved into: data/processed/la_daily_cdo.csv

---

## 5.  Run the analysis

Run:

python src/run_analysis.py

Output:
- Summary results written to: results/analysis_summary.txt
- (If your script also writes CSV outputs, they will be in results/)

---

## 6.  Produce the visualizations

Run:

python src/visualize_results.py

Output:
- Figures saved into: results/figures/

---

## 7.  Jupyter notebook (presentation)

Open the notebook:

notebook/Xinwei_Wang_DSCI510_Final_Project.ipynb

The notebook is used to present results and display plots, using the processed dataset and generated figures.

---

## Notes

- The main data source is NOAA CDO (GHCND daily) for station GHCND:USW00023174 (Los Angeles International Airport).
- A weather.gov observations endpoint was tested earlier, but it did not return historical records for the station/time range, so the final analysis relies on NOAA CDO historical daily data.
- Run scripts in this order:
  1) get_cdo_daily.py
  2) clean_data.py
  3) run_analysis.py
  4) visualize_results.py