# backend/main.py
# FastAPI backend — handles sessions, analytics, and Gemini AI chat.

import os
import uuid
import requests as http_requests
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Load env before anything else ─────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# ── Import data layer ──────────────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.data_loader import load_and_clean, build_summary

# ── Load data once at startup ──────────────────────────────────────────────────
DF = load_and_clean()
DATA_SUMMARY = build_summary(DF)

# ── In-memory session store  {session_id: [{"role": ..., "parts": [...]}]} ────
SESSIONS: dict[str, list] = {}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="Retail Sales AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int

class KPIResponse(BaseModel):
    total_sales: float
    total_profit: float
    total_quantity: float
    avg_margin: float
    total_transactions: int
    avg_order_value: float

class CategoryStats(BaseModel):
    category: str
    total_sales: float
    total_profit: float
    avg_margin: float
    transactions: int

class RegionStats(BaseModel):
    region: str
    total_sales: float
    total_profit: float
    transactions: int

class MonthlySales(BaseModel):
    month: str
    sales: float
    profit: float

class DailySales(BaseModel):
    date: str
    sales: float
    profit: float
    transactions: int

class WeeklySales(BaseModel):
    week: int
    sales: float
    profit: float
    transactions: int

class DayOfWeekSales(BaseModel):
    day: str
    sales: float
    profit: float
    avg_sales: float
    transactions: int

class QuarterlySales(BaseModel):
    quarter: str
    sales: float
    profit: float
    transactions: int
    avg_margin: float

class HeatmapCell(BaseModel):
    category: str
    region: str
    sales: float
    profit: float
    transactions: int

class DeepDiveItem(BaseModel):
    category: str
    region: str
    month: str
    sales: float
    profit: float
    transactions: int

class DataQuality(BaseModel):
    total_rows: int
    complete_rows: int
    missing_dates: int
    missing_categories: int
    missing_regions: int
    missing_sales: int
    missing_profit: int
    missing_quantity: int
    duplicate_rows: int
    sales_min: float
    sales_max: float
    sales_mean: float
    profit_min: float
    profit_max: float
    date_min: str
    date_max: str
    categories: List[str]
    regions: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: apply optional date/category/region filters to DF
# ─────────────────────────────────────────────────────────────────────────────
def filtered_df(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[str] = None,
    regions: Optional[str] = None,
):
    df = DF.copy()
    if date_from:
        df = df[df["Date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["Date"] <= pd.Timestamp(date_to)]
    if categories:
        cat_list = [c.strip() for c in categories.split(",") if c.strip()]
        if cat_list:
            df = df[df["Category"].isin(cat_list)]
    if regions:
        reg_list = [r.strip() for r in regions.split(",") if r.strip()]
        if reg_list:
            df = df[df["Region"].isin(reg_list)]
    return df

import pandas as pd  # needed for Timestamp in filtered_df


# ─────────────────────────────────────────────────────────────────────────────
# Session endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/session/new", response_model=SessionInfo)
def new_session():
    sid = str(uuid.uuid4())
    SESSIONS[sid] = []
    return SessionInfo(session_id=sid, created_at=datetime.utcnow().isoformat(), message_count=0)

@app.get("/session/{session_id}", response_model=SessionInfo)
def get_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(session_id=session_id, created_at="N/A", message_count=len(SESSIONS[session_id]))

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    SESSIONS[session_id] = []
    return {"message": "Session cleared", "session_id": session_id}

@app.get("/sessions")
def list_sessions():
    return [{"session_id": sid, "message_count": len(hist)} for sid, hist in SESSIONS.items()]


# ─────────────────────────────────────────────────────────────────────────────
# Chat endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")
    if req.session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found. Call /session/new first.")

    SESSIONS[req.session_id].append({"role": "user", "parts": [req.message]})
    contents = [
        {"role": msg["role"], "parts": [{"text": msg["parts"][0]}]}
        for msg in SESSIONS[req.session_id]
    ]
    payload = {
        "system_instruction": {"parts": [{"text": DATA_SUMMARY}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
    }
    resp = http_requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=30)
    if resp.status_code != 200:
        err = resp.json().get("error", {}).get("message", "Unknown Gemini error")
        raise HTTPException(status_code=resp.status_code, detail=err)

    reply_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    SESSIONS[req.session_id].append({"role": "model", "parts": [reply_text]})
    history = [ChatMessage(role=m["role"], text=m["parts"][0]) for m in SESSIONS[req.session_id]]
    return ChatResponse(session_id=req.session_id, reply=reply_text, history=history)


# ─────────────────────────────────────────────────────────────────────────────
# Core analytics endpoints (original)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/kpis", response_model=KPIResponse)
def get_kpis(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        return KPIResponse(
            total_sales=round(float(df["Sales"].sum()), 2),
            total_profit=round(float(df["Profit"].sum()), 2),
            total_quantity=round(float(df["Quantity"].sum()), 2),
            avg_margin=round(float(df["Profit_Margin"].mean()), 2),
            total_transactions=int(len(df)),
            avg_order_value=round(float(df["Sales"].mean()), 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"kpis error: {str(e)}")


@app.get("/analytics/categories", response_model=List[CategoryStats])
def get_categories(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, None, regions)
        grp = (
            df.groupby("Category")
            .agg(
                total_sales=("Sales", "sum"),
                total_profit=("Profit", "sum"),
                avg_margin=("Profit_Margin", "mean"),
                transactions=("Sales", "count"),
            )
            .reset_index().round(2)
        )
        grp.columns = ["category", "total_sales", "total_profit", "avg_margin", "transactions"]
        return [
            CategoryStats(
                category=str(r["category"]),
                total_sales=float(r["total_sales"]),
                total_profit=float(r["total_profit"]),
                avg_margin=float(r["avg_margin"]),
                transactions=int(r["transactions"]),
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"categories error: {str(e)}")


@app.get("/analytics/regions", response_model=List[RegionStats])
def get_regions(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, None)
        grp = (
            df.groupby("Region")
            .agg(total_sales=("Sales", "sum"), total_profit=("Profit", "sum"), transactions=("Sales", "count"))
            .reset_index().round(2)
        )
        grp.columns = ["region", "total_sales", "total_profit", "transactions"]
        return [
            RegionStats(region=str(r["region"]), total_sales=float(r["total_sales"]),
                        total_profit=float(r["total_profit"]), transactions=int(r["transactions"]))
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"regions error: {str(e)}")


@app.get("/analytics/monthly", response_model=List[MonthlySales])
def get_monthly(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        grp = (
            df.groupby(["Month", "Month_Name"])
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"))
            .reset_index().sort_values("Month").round(2)
        )
        return [
            MonthlySales(month=str(r["Month_Name"]), sales=float(r["sales"]), profit=float(r["profit"]))
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"monthly error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Daily trend endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/daily", response_model=List[DailySales])
def get_daily(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        grp = (
            df.groupby("Date")
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), transactions=("Sales", "count"))
            .reset_index().sort_values("Date").round(2)
        )
        return [
            DailySales(
                date=r["Date"].strftime("%Y-%m-%d"),
                sales=float(r["sales"]),
                profit=float(r["profit"]),
                transactions=int(r["transactions"]),
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"daily error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Weekly trend endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/weekly", response_model=List[WeeklySales])
def get_weekly(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        grp = (
            df.groupby("Week")
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), transactions=("Sales", "count"))
            .reset_index().sort_values("Week").round(2)
        )
        return [
            WeeklySales(week=int(r["Week"]), sales=float(r["sales"]),
                        profit=float(r["profit"]), transactions=int(r["transactions"]))
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"weekly error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Day-of-week performance
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/dayofweek", response_model=List[DayOfWeekSales])
def get_dayofweek(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        grp = (
            df.groupby("DayOfWeek")
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"),
                 avg_sales=("Sales", "mean"), transactions=("Sales", "count"))
            .reindex(day_order).reset_index().round(2)
        )
        return [
            DayOfWeekSales(
                day=str(r["DayOfWeek"]),
                sales=float(r["sales"]) if pd.notna(r["sales"]) else 0.0,
                profit=float(r["profit"]) if pd.notna(r["profit"]) else 0.0,
                avg_sales=float(r["avg_sales"]) if pd.notna(r["avg_sales"]) else 0.0,
                transactions=int(r["transactions"]) if pd.notna(r["transactions"]) else 0,
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"dayofweek error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Quarterly performance
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/quarterly", response_model=List[QuarterlySales])
def get_quarterly(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        grp = (
            df.groupby("Quarter")
            .agg(
                sales=("Sales", "sum"),
                profit=("Profit", "sum"),
                transactions=("Sales", "count"),
                avg_margin=("Profit_Margin", "mean"),
            )
            .reset_index().sort_values("Quarter").round(2)
        )
        return [
            QuarterlySales(
                quarter=str(r["Quarter"]),
                sales=float(r["sales"]),
                profit=float(r["profit"]),
                transactions=int(r["transactions"]),
                avg_margin=float(r["avg_margin"]),
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"quarterly error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Category × Region heatmap
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/heatmap", response_model=List[HeatmapCell])
def get_heatmap(
    metric: str = Query("sales", description="sales | profit | transactions"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to)
        grp = (
            df.groupby(["Category", "Region"])
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), transactions=("Sales", "count"))
            .reset_index().round(2)
        )
        return [
            HeatmapCell(
                category=str(r["Category"]),
                region=str(r["Region"]),
                sales=float(r["sales"]),
                profit=float(r["profit"]),
                transactions=int(r["transactions"]),
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"heatmap error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Deep-dive (category + region + month breakdown)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/deepdive", response_model=List[DeepDiveItem])
def get_deepdive(
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    try:
        df = filtered_df(date_from, date_to, category, region)
        grp = (
            df.groupby(["Category", "Region", "Month_Name", "Month"])
            .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), transactions=("Sales", "count"))
            .reset_index().sort_values(["Category", "Region", "Month"]).round(2)
        )
        return [
            DeepDiveItem(
                category=str(r["Category"]),
                region=str(r["Region"]),
                month=str(r["Month_Name"]),
                sales=float(r["sales"]),
                profit=float(r["profit"]),
                transactions=int(r["transactions"]),
            )
            for _, r in grp.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"deepdive error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Data quality / profiling report
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/quality", response_model=DataQuality)
def get_quality():
    try:
        raw_df = DF.copy()
        return DataQuality(
            total_rows=int(len(raw_df)),
            complete_rows=int(raw_df.dropna().shape[0]),
            missing_dates=int(raw_df["Date"].isna().sum()),
            missing_categories=int(raw_df["Category"].isna().sum()),
            missing_regions=int(raw_df["Region"].isna().sum()),
            missing_sales=int(raw_df["Sales"].isna().sum()),
            missing_profit=int(raw_df["Profit"].isna().sum()),
            missing_quantity=int(raw_df["Quantity"].isna().sum()),
            duplicate_rows=int(raw_df.duplicated().sum()),
            sales_min=round(float(raw_df["Sales"].min()), 2),
            sales_max=round(float(raw_df["Sales"].max()), 2),
            sales_mean=round(float(raw_df["Sales"].mean()), 2),
            profit_min=round(float(raw_df["Profit"].min()), 2),
            profit_max=round(float(raw_df["Profit"].max()), 2),
            date_min=str(raw_df["Date"].min().date()),
            date_max=str(raw_df["Date"].max().date()),
            categories=sorted(raw_df["Category"].dropna().unique().tolist()),
            regions=sorted(raw_df["Region"].dropna().unique().tolist()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"quality error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Raw data + health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/analytics/raw")
def get_raw(
    limit: int = 100,
    offset: int = 0,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    regions: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
):
    try:
        df = filtered_df(date_from, date_to, categories, regions)
        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=(sort_dir == "asc"))
        slice_ = df.iloc[offset: offset + limit].copy()
        slice_["Date"] = slice_["Date"].dt.strftime("%Y-%m-%d")
        return {
            "total": int(len(df)),
            "offset": int(offset),
            "limit": int(limit),
            "data": slice_.astype(object).where(slice_.notna(), None).to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"raw data error: {str(e)}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rows_loaded": len(DF),
        "categories": sorted(DF["Category"].unique().tolist()),
        "regions": sorted(DF["Region"].unique().tolist()),
        "date_min": str(DF["Date"].min().date()),
        "date_max": str(DF["Date"].max().date()),
    }
