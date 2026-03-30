import os
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
from fredapi import Fred


API_KEY = os.getenv("FRED_API_KEY", "c8d84f3376ef9ce64612054e5f9754d0")

SERIES = {
    "PCEPILFE": "monthly",
    "FEDFUNDS": "monthly",
    "EXPINF1YR": "monthly",
    "UNRATE": "monthly",
    "GDPC1": "quarterly",
    "GDPPOT": "quarterly",
    "NROU": "quarterly",
}

OUT_DIR = Path("fred_data")
MONTHLY_FILE = "monthly.csv"
MONTHLY_Q_FILE = "monthly_q.csv"
QUARTERLY_FILE = "quarterly.csv"
COMBINED_Q_FILE = "combined_q.csv"
CALC_Q_FILE = "calc_q.csv"
REG_FILE = "rolling_reg.csv"


def download_series(api_key: str = API_KEY, out_dir: Path = OUT_DIR) -> None:
    """Download all required FRED series to short CSV filenames."""
    out_dir.mkdir(exist_ok=True)

    fred = Fred(api_key=api_key)

    for series_id in SERIES:
        print(f"Downloading {series_id}...")
        s = fred.get_series(series_id)

        df = pd.DataFrame({
            "date": pd.to_datetime(s.index),
            "value": s.values,
        }).dropna(subset=["value"])

        path = out_dir / f"{series_id}.csv"
        df.to_csv(path, index=False)
        print(f"Saved: {path}")


def make_monthly(out_dir: Path = OUT_DIR, output_file: str = MONTHLY_FILE) -> None:
    """Merge monthly series into one file."""
    pce = pd.read_csv(out_dir / "PCEPILFE.csv").rename(columns={"value": "pcepilfe"})
    fed = pd.read_csv(out_dir / "FEDFUNDS.csv").rename(columns={"value": "fedfunds"})
    expinf = pd.read_csv(out_dir / "EXPINF1YR.csv").rename(columns={"value": "expinf1yr"})
    unrate = pd.read_csv(out_dir / "UNRATE.csv").rename(columns={"value": "unrate"})

    df = pce.merge(fed, on="date", how="outer")
    df = df.merge(expinf, on="date", how="outer")
    df = df.merge(unrate, on="date", how="outer")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"{output_file} created successfully")


def monthly_to_quarterly(input_file: str = MONTHLY_FILE, output_file: str = MONTHLY_Q_FILE) -> None:
    """Convert monthly merged file to quarterly averages."""
    df = pd.read_csv(input_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    quarterly_df = df.resample("QS").mean().reset_index()
    quarterly_df.to_csv(output_file, index=False)

    print(f"{output_file} created successfully")


def make_quarterly(out_dir: Path = OUT_DIR, output_file: str = QUARTERLY_FILE) -> None:
    """Merge quarterly series into one file."""
    gdp = pd.read_csv(out_dir / "GDPC1.csv").rename(columns={"value": "gdpc1"})
    gdppot = pd.read_csv(out_dir / "GDPPOT.csv").rename(columns={"value": "gdppot"})
    nrou = pd.read_csv(out_dir / "NROU.csv").rename(columns={"value": "nrou"})

    df = gdp.merge(gdppot, on="date", how="outer")
    df = df.merge(nrou, on="date", how="outer")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"{output_file} created successfully")


def merge_quarterly(
    quarterly_file: str = QUARTERLY_FILE,
    monthly_q_file: str = MONTHLY_Q_FILE,
    output_file: str = COMBINED_Q_FILE,
) -> None:
    """Merge quarterly-only series with quarterly-averaged monthly series."""
    quarterly = pd.read_csv(quarterly_file)
    monthly_q = pd.read_csv(monthly_q_file)

    quarterly["date"] = pd.to_datetime(quarterly["date"])
    monthly_q["date"] = pd.to_datetime(monthly_q["date"])

    df = pd.merge(quarterly, monthly_q, on="date", how="outer")
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"{output_file} created successfully")


def add_calculated_fields(input_file: str = COMBINED_Q_FILE, output_file: str = CALC_Q_FILE) -> None:
    """Add assignment fields used for the regression."""
    df = pd.read_csv(input_file)

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["ffr"] = df["fedfunds"]
    df["ffr_lag1"] = df["fedfunds"].shift(1)
    df["unemployment_gap"] = df["unrate"] - df["nrou"]
    df["output_gap"] = 100 * ((df["gdpc1"] / df["gdppot"]) - 1)
    df["core_inflation"] = 100 * ((df["pcepilfe"] / df["pcepilfe"].shift(4)) - 1)
    df["expected_inflation_gap"] = df["expinf1yr"] - 2

    df.to_csv(output_file, index=False)
    print(f"{output_file} created successfully")


def rolling_regression(
    input_file: str = CALC_Q_FILE,
    output_file: str = REG_FILE,
    window: int = 40,
    start_date: str = "2014-04-01",
    end_date: str = "2024-07-01",
) -> None:
    """Run the 40-quarter rolling regression."""
    df = pd.read_csv(input_file)

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    needed = [
        "ffr",
        "ffr_lag1",
        "output_gap",
        "core_inflation",
        "expected_inflation_gap",
        "unemployment_gap",
    ]
    df = df.dropna(subset=needed).copy()

    results = []

    for i in range(window - 1, len(df)):
        window_df = df.iloc[i - window + 1 : i + 1].copy()

        y = window_df["ffr"]
        X = window_df[
            [
                "ffr_lag1",
                "output_gap",
                "core_inflation",
                "expected_inflation_gap",
                "unemployment_gap",
            ]
        ]

        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()

        result_date = df.iloc[i]["date"]

        results.append(
            {
                "date": result_date,
                "const": model.params.get("const"),
                "ffr_lag1": model.params.get("ffr_lag1"),
                "output_gap": model.params.get("output_gap"),
                "core_inflation": model.params.get("core_inflation"),
                "expected_inflation_gap": model.params.get("expected_inflation_gap"),
                "unemployment_gap": model.params.get("unemployment_gap"),
                "r_squared": model.rsquared,
            }
        )

    results_df = pd.DataFrame(results)
    results_df = results_df[
        (results_df["date"] >= start_date) & (results_df["date"] <= end_date)
    ].copy()

    results_df.to_csv(output_file, index=False)

    print(f"{output_file} created successfully")
    print(results_df.head())
    print(results_df.tail())


def main() -> None:
    download_series()
    make_monthly()
    monthly_to_quarterly()
    make_quarterly()
    merge_quarterly()
    add_calculated_fields()
    rolling_regression()
    print("\nPipeline finished.")
    print("Files created:")
    print(f"  {MONTHLY_FILE}")
    print(f"  {MONTHLY_Q_FILE}")
    print(f"  {QUARTERLY_FILE}")
    print(f"  {COMBINED_Q_FILE}")
    print(f"  {CALC_Q_FILE}")
    print(f"  {REG_FILE}")


if __name__ == "__main__":
    main()
