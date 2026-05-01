# backend/data_loader.py
# Handles all data loading, cleaning, and analytics computations.

import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.getenv("DATA_PATH", "retail_sales.csv")


def load_and_clean() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)

    # ── Date ──────────────────────────────────────────────────────────────────
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # ── Category & Region — normalise NaN-like strings ────────────────────────
    nan_vals = {"nan", "nan?", "null", "none", ""}
    for col in ["Category", "Region"]:
        col_str = df[col].astype(object).fillna("").astype(str).str.strip().str.lower()
        df[col] = df[col].astype(object)
        df.loc[col_str.isin(nan_vals), col] = np.nan

    # ── Numeric columns ───────────────────────────────────────────────────────
    for col in ["Sales", "Quantity", "Profit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Zero → NaN
    df.loc[df["Sales"] == 0, "Sales"] = np.nan
    df.loc[df["Quantity"] == 0, "Quantity"] = np.nan

    # ── Impute ────────────────────────────────────────────────────────────────
    df["Category"] = df["Category"].fillna(df["Category"].mode()[0])
    df["Region"]   = df["Region"].fillna(df["Region"].mode()[0])
    df["Sales"]    = df["Sales"].fillna(df["Sales"].median())
    df["Quantity"] = df["Quantity"].fillna(df["Quantity"].median())
    df["Profit"]   = df["Profit"].fillna(df["Profit"].median())

    # ── Derived columns ───────────────────────────────────────────────────────
    df["Month"]       = df["Date"].dt.month
    df["Month_Name"]  = df["Date"].dt.strftime("%b")
    df["Week"]        = df["Date"].dt.isocalendar().week.astype(int)
    df["DayOfWeek"]   = df["Date"].dt.day_name()
    df["Quarter"]     = df["Date"].dt.quarter.apply(lambda q: f"Q{q}")
    df["Profit_Margin"] = (df["Profit"] / df["Sales"] * 100).round(2)

    return df.dropna(subset=["Date"])


def build_summary(df: pd.DataFrame) -> str:
    """Build a rich text summary of the dataframe for the AI context."""
    cat   = df.groupby("Category").agg(Sales=("Sales","sum"), Profit=("Profit","sum"),
                                        Margin=("Profit_Margin","mean"), Txns=("Sales","count")).round(2)
    reg   = df.groupby("Region").agg(Sales=("Sales","sum"), Profit=("Profit","sum"),
                                      Txns=("Sales","count")).round(2)
    mon   = df.groupby("Month_Name")["Sales"].sum().round(2)
    dow   = df.groupby("DayOfWeek")["Sales"].mean().round(2)
    best  = df.groupby("Date")["Sales"].sum().idxmax()
    worst = df.groupby("Date")["Sales"].sum().idxmin()
    top5  = df.groupby(["Category","Region"])["Sales"].sum().nlargest(5).round(2)

    return f"""
You are an expert retail sales analyst. Answer questions ONLY from the data below.
Be concise, use specific numbers, format with $ and commas where relevant.

=== DATASET ===
Date range : {df['Date'].min().date()} → {df['Date'].max().date()}
Rows       : {len(df):,}
Categories : {', '.join(sorted(df['Category'].unique()))}
Regions    : {', '.join(sorted(df['Region'].unique()))}

=== KEY METRICS ===
Total Sales       : ${df['Sales'].sum():,.2f}
Total Profit      : ${df['Profit'].sum():,.2f}
Avg Profit Margin : {df['Profit_Margin'].mean():.1f}%
Total Units Sold  : {df['Quantity'].sum():,.0f}
Avg Order Value   : ${df['Sales'].mean():,.2f}
Best Sales Day    : {best.date()} (${df.groupby('Date')['Sales'].sum()[best]:,.2f})
Worst Sales Day   : {worst.date()} (${df.groupby('Date')['Sales'].sum()[worst]:,.2f})

=== BY CATEGORY ===
{cat.to_string()}

=== BY REGION ===
{reg.to_string()}

=== MONTHLY SALES ===
{mon.to_string()}

=== AVG SALES BY DAY OF WEEK ===
{dow.to_string()}

=== TOP 5 CATEGORY × REGION ===
{top5.to_string()}

=== MARGIN STATS ===
Min: {df['Profit_Margin'].min():.1f}%  Max: {df['Profit_Margin'].max():.1f}%  Std: {df['Profit_Margin'].std():.1f}%
"""
