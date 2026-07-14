"""基础统计分析与 AI 输入摘要。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _safe_number(value: Any) -> float | int | None:
    """把 numpy 数值转换成可 JSON 序列化的 Python 数值。"""
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), 4)
    return value


def calculate_numeric_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """计算数值字段的常见统计指标。"""
    records: list[dict] = []
    for column in df.select_dtypes(include="number").columns:
        series = df[column]
        records.append(
            {
                "字段名": column,
                "非空数量": int(series.notna().sum()),
                "缺失数量": int(series.isna().sum()),
                "均值": _safe_number(series.mean()),
                "中位数": _safe_number(series.median()),
                "最小值": _safe_number(series.min()),
                "最大值": _safe_number(series.max()),
                "总和": _safe_number(series.sum()),
                "标准差": _safe_number(series.std()),
                "25%分位数": _safe_number(series.quantile(0.25)),
                "75%分位数": _safe_number(series.quantile(0.75)),
            }
        )
    return pd.DataFrame(records)


def calculate_categorical_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """计算文本、分类和布尔字段概览。"""
    records: list[dict] = []
    numeric_columns = set(df.select_dtypes(include="number").columns)
    for column in df.columns:
        if column in numeric_columns or pd.api.types.is_datetime64_any_dtype(df[column]):
            continue
        series = df[column]
        value_counts = series.value_counts(dropna=True)
        top_value = value_counts.index[0] if not value_counts.empty else None
        top_count = int(value_counts.iloc[0]) if not value_counts.empty else 0
        records.append(
            {
                "字段名": column,
                "唯一值数量": int(series.nunique(dropna=True)),
                "缺失数量": int(series.isna().sum()),
                "最高频值": str(top_value) if top_value is not None else "",
                "最高频次数": top_count,
            }
        )
    return pd.DataFrame(records)


def calculate_statistics(df: pd.DataFrame) -> dict:
    return {
        "numeric": calculate_numeric_statistics(df),
        "categorical": calculate_categorical_statistics(df),
    }


def build_analysis_payload(df: pd.DataFrame, quality: dict, statistics: dict) -> dict:
    """构造发给大模型的精简聚合数据，不包含原始明细。"""
    numeric_records = statistics["numeric"].replace({np.nan: None}).to_dict(orient="records")
    categorical_records = statistics["categorical"].replace({np.nan: None}).to_dict(orient="records")

    missing_records = quality["missing"].head(20).to_dict(orient="records")
    outlier_records = quality["outliers"].head(20).rename(
        columns={"outlier_count": "异常值数量"}
    ).to_dict(orient="records")
    type_issue_records = quality["type_issues"].head(20).to_dict(orient="records")

    date_ranges = []
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            series = df[column].dropna()
            if not series.empty:
                date_ranges.append(
                    {
                        "字段名": column,
                        "最早日期": series.min().isoformat(),
                        "最晚日期": series.max().isoformat(),
                    }
                )

    return {
        "dataset": {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "column_names": [str(column) for column in df.columns],
            "numeric_columns": [str(column) for column in df.select_dtypes(include="number").columns],
            "date_columns": [
                str(column)
                for column in df.columns
                if pd.api.types.is_datetime64_any_dtype(df[column])
            ],
        },
        "quality": {
            "score": quality["score"],
            "duplicate_rows": quality["duplicate_count"],
            "missing": missing_records,
            "outliers": outlier_records,
            "type_issues": type_issue_records,
            "constant_columns": quality["constant_columns"],
        },
        "numeric_statistics": numeric_records[:30],
        "categorical_statistics": categorical_records[:30],
        "date_ranges": date_ranges,
    }

