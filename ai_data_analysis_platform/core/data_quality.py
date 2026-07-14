"""数据质量检测：缺失、重复、异常、字段类型问题。"""

from __future__ import annotations

import warnings

import pandas as pd


def detect_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """返回存在缺失值的字段统计。"""
    missing_count = df.isna().sum()
    result = pd.DataFrame(
        {
            "字段名": missing_count.index,
            "缺失数量": missing_count.values.astype(int),
            "缺失比例": (missing_count.values / max(len(df), 1) * 100).round(2),
        }
    )
    result = result[result["缺失数量"] > 0].sort_values("缺失数量", ascending=False)
    return result.reset_index(drop=True)


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """使用四分位距 IQR 方法检测数值异常值。"""
    records: list[dict] = []
    for column in df.select_dtypes(include="number").columns:
        series = df[column].dropna()
        if len(series) < 4 or series.nunique() < 2:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_mask = (series < lower) | (series > upper)
        count = int(outlier_mask.sum())
        if count:
            records.append(
                {
                    "字段名": column,
                    "异常值数量": count,
                    "异常比例": round(count / len(series) * 100, 2),
                    "合理下界": round(float(lower), 4),
                    "合理上界": round(float(upper), 4),
                    "异常最小值": round(float(series[outlier_mask].min()), 4),
                    "异常最大值": round(float(series[outlier_mask].max()), 4),
                }
            )
    return pd.DataFrame(records)


def detect_type_issues(df: pd.DataFrame) -> pd.DataFrame:
    """识别“看起来像数字/日期但被读成文本”的字段。"""
    records: list[dict] = []
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        series = df[column].dropna().astype(str).str.strip()
        if series.empty:
            continue

        sample = series.head(500)
        numeric_ratio = pd.to_numeric(sample.str.replace(",", "", regex=False), errors="coerce").notna().mean()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            date_ratio = pd.to_datetime(sample, errors="coerce", format="mixed").notna().mean()

        if numeric_ratio >= 0.8:
            records.append(
                {
                    "字段名": column,
                    "问题类型": "数字被识别为文本",
                    "疑似比例": round(float(numeric_ratio) * 100, 2),
                    "建议": "清除千分位符号后转为数值类型",
                }
            )
        elif date_ratio >= 0.8:
            records.append(
                {
                    "字段名": column,
                    "问题类型": "日期被识别为文本",
                    "疑似比例": round(float(date_ratio) * 100, 2),
                    "建议": "在数据清洗中选择该字段进行日期标准化",
                }
            )
    return pd.DataFrame(records)


def calculate_quality_score(
    df: pd.DataFrame,
    missing_count: int,
    duplicate_count: int,
    outlier_count: int,
    type_issue_count: int,
) -> int:
    """计算一个便于展示的数据质量分，结果不是行业标准评分。"""
    cell_count = max(df.shape[0] * max(df.shape[1], 1), 1)
    row_count = max(len(df), 1)
    missing_penalty = min(missing_count / cell_count * 100, 35)
    duplicate_penalty = min(duplicate_count / row_count * 100, 25)
    outlier_penalty = min(outlier_count / cell_count * 100, 20)
    type_penalty = min(type_issue_count * 5, 20)
    return max(0, round(100 - missing_penalty - duplicate_penalty - outlier_penalty - type_penalty))


def analyze_data_quality(df: pd.DataFrame) -> dict:
    """汇总全部数据质量检测结果。"""
    missing = detect_missing_values(df)
    outliers = detect_outliers(df)
    type_issues = detect_type_issues(df)
    duplicate_count = int(df.duplicated().sum())
    missing_count = int(df.isna().sum().sum())
    outlier_count = int(outliers["异常值数量"].sum()) if not outliers.empty else 0
    empty_columns = [column for column in df.columns if df[column].isna().all()]
    constant_columns = [column for column in df.columns if df[column].nunique(dropna=True) <= 1]

    score = calculate_quality_score(
        df,
        missing_count=missing_count,
        duplicate_count=duplicate_count,
        outlier_count=outlier_count,
        type_issue_count=len(type_issues),
    )
    # 同时提供中文列名和内部统一列名，便于界面与报告分别使用。
    outliers_internal = outliers.rename(columns={"异常值数量": "outlier_count"})
    return {
        "score": score,
        "missing": missing,
        "outliers": outliers_internal,
        "type_issues": type_issues,
        "duplicate_count": duplicate_count,
        "empty_column_count": len(empty_columns),
        "empty_columns": empty_columns,
        "constant_columns": constant_columns,
    }

