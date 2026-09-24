"""ANOMALY ANALYSIS - scikit-learn Isolation Forest over behavioural features.

An anomaly is an ANALYTICAL ANOMALY / INVESTIGATIVE LEAD. It is never evidence of
criminal activity and is always presented with its baseline and source evidence.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..database.postgres import relational

AGENT_NAME = "NETWORK_TEMPORAL_AGENT"

# Every finding carries the detector that produced it, so a response containing more
# than one detector is never ambiguous about which one fired.
DETECTOR_NAME = "isolation_forest_transaction_burst"


def _feature_frame(case_ids: Optional[list[str]] = None) -> pd.DataFrame:
    txns = relational.all("transactions")
    if case_ids:
        txns = [t for t in txns if t.get("case_id") in case_ids]
    if not txns:
        return pd.DataFrame()
    df = pd.DataFrame(txns)
    df["ts"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")
    df = df.dropna(subset=["ts"])
    if df.empty:
        return df
    df["hour_bucket"] = df["ts"].dt.floor("h")
    df["day"] = df["ts"].dt.date.astype(str)
    return df


def analyze(case_ids: Optional[list[str]] = None, contamination: float = 0.08) -> dict[str, Any]:
    df = _feature_frame(case_ids)
    if df.empty:
        return {
            "agent": AGENT_NAME, "sufficient": False, "anomalies": [], "observations": [],
            "detector": DETECTOR_NAME, "detector_kind": "classical_ml",
            "model": "IsolationForest (scikit-learn)",
            "message": "INSUFFICIENT EVIDENCE: no transactional records available in this scope "
                       "for behavioural baseline analysis.",
        }

    grouped = (
        df.groupby(["account_id", "hour_bucket"])
          .agg(txn_count=("txn_id", "count"),
               total_amount=("amount", "sum"),
               mean_amount=("amount", "mean"),
               distinct_counterparties=("counterparty", pd.Series.nunique),
               case_id=("case_id", "first"))
          .reset_index()
    )
    features = grouped[["txn_count", "total_amount", "mean_amount", "distinct_counterparties"]].to_numpy(float)

    if len(features) < 4:
        return {
            "agent": AGENT_NAME, "sufficient": False, "anomalies": [],
            "observations": grouped.assign(hour_bucket=grouped["hour_bucket"].astype(str)).to_dict("records"),
            "detector": DETECTOR_NAME, "detector_kind": "classical_ml",
            "model": "IsolationForest (scikit-learn)",
            "message": "INSUFFICIENT EVIDENCE: fewer than 4 behavioural observations - a reliable "
                       "baseline cannot be established.",
        }

    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
    labels = model.fit_predict(features)
    scores = model.decision_function(features)
    median_hourly = float(grouped["txn_count"].median()) or 1.0
    deviation = grouped["txn_count"] >= max(2.0 * median_hourly, median_hourly + 2)
    grouped["anomaly"] = (labels == -1) & deviation
    grouped["anomaly_score"] = np.round(-scores, 4)

    baseline_by_account = df.groupby(["account_id", "day"]).size().groupby("account_id").mean()

    anomalies: list[dict[str, Any]] = []
    for _, row in grouped[grouped["anomaly"]].sort_values("anomaly_score", ascending=False).iterrows():
        account = row["account_id"]
        window_txns = df[(df["account_id"] == account) & (df["hour_bucket"] == row["hour_bucket"])]
        anomalies.append({
            "detector": DETECTOR_NAME,
            "detector_kind": "classical_ml",
            "account_id": account,
            "case_id": row["case_id"],
            "window": str(row["hour_bucket"]),
            "observed": {
                "transactions_in_hour": int(row["txn_count"]),
                "total_amount": round(float(row["total_amount"]), 2),
                "distinct_counterparties": int(row["distinct_counterparties"]),
            },
            "baseline": {
                "mean_transactions_per_day": round(float(baseline_by_account.get(account, 0.0)), 2),
                "description": "Mean daily transaction volume for this account across available evidence.",
            },
            "anomaly_score": float(row["anomaly_score"]),
            "evidence_ids": sorted(set(window_txns["evidence_id"].tolist())),
            "label": "Analytical anomaly / investigative lead",
            "interpretation": "Behavioural anomaly detected relative to the account's own baseline. "
                              "An anomaly is not an indication of criminal activity and requires "
                              "corroboration and investigator review.",
        })

    observations = grouped.copy()
    observations["hour_bucket"] = observations["hour_bucket"].astype(str)

    return {
        "agent": AGENT_NAME,
        "sufficient": True,
        "detector": DETECTOR_NAME,
        "detector_kind": "classical_ml",
        "model": "IsolationForest (scikit-learn)",
        "parameters": {"n_estimators": 200, "contamination": contamination, "random_state": 42},
        "feature_space": ["txn_count", "total_amount", "mean_amount", "distinct_counterparties"],
        "observation_count": int(len(grouped)),
        "anomalies": anomalies,
        "observations": observations.to_dict("records"),
        "safety_note": "Anomaly ≠ guilt. Findings are analytical leads requiring corroboration.",
    }
