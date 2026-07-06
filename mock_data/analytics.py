import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def compute_growth_rate(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / values[0] * 100


def summarize_dataset(df: pd.DataFrame) -> dict:
    return {
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_counts": df.isnull().sum().to_dict(),
        "numeric_summary": df.describe().to_dict() if not df.empty else {},
    }


class SalesAnalyzer:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.df = None

    def load(self) -> None:
        self.df = pd.read_csv(self.data_path, parse_dates=["date"])

    def top_products(self, n: int = 5) -> pd.DataFrame:
        return self.df.groupby("product")["total"].sum().nlargest(n).reset_index()
