"""可配置的数据清洗模块。"""

from __future__ import annotations

import warnings

import pandas as pd


def infer_date_candidates(df: pd.DataFrame) -> list[str]:
    """推断适合转换为日期的字段，供界面默认勾选。"""
    candidates: list[str] = []
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            candidates.append(column)
            continue
        if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
            continue
        series = df[column].dropna().astype(str).head(300)
        if series.empty:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed_ratio = pd.to_datetime(series, errors="coerce", format="mixed").notna().mean()
        name_hint = any(word in str(column).lower() for word in ["date", "time", "日期", "时间", "年月", "day"])
        if parsed_ratio >= 0.8 and (name_hint or parsed_ratio >= 0.95):
            candidates.append(column)
    return candidates


def _fill_categorical(series: pd.Series) -> pd.Series:
    """使用众数填充文本/分类字段；无众数时使用“未知”。"""
    mode = series.mode(dropna=True)
    fill_value = mode.iloc[0] if not mode.empty else "未知"
    return series.fillna(fill_value)


def clean_dataframe(
    df: pd.DataFrame,
    *,
    remove_duplicates: bool,
    missing_strategy: str,
    date_columns: list[str],
    trim_text: bool,
) -> tuple[pd.DataFrame, list[str]]:
    """执行清洗并返回新 DataFrame 和操作日志。"""
    cleaned = df.copy()
    log: list[str] = []

    if trim_text:
        text_columns = cleaned.select_dtypes(include=["object", "string"]).columns
        for column in text_columns:
            cleaned[column] = cleaned[column].map(lambda value: value.strip() if isinstance(value, str) else value)
        log.append(f"已清除 {len(text_columns)} 个文本字段的首尾空格")

    if remove_duplicates:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        log.append(f"已删除 {before - len(cleaned)} 条重复记录")

    if missing_strategy == "删除含缺失值的行":
        before = len(cleaned)
        cleaned = cleaned.dropna().reset_index(drop=True)
        log.append(f"已删除 {before - len(cleaned)} 条含缺失值的记录")
    elif missing_strategy in {"数值中位数 + 文本众数填充", "数值均值 + 文本众数填充"}:
        numeric_columns = cleaned.select_dtypes(include="number").columns
        other_columns = cleaned.columns.difference(numeric_columns)
        for column in numeric_columns:
            if cleaned[column].isna().any():
                if missing_strategy.startswith("数值中位数"):
                    fill_value = cleaned[column].median()
                else:
                    fill_value = cleaned[column].mean()
                cleaned[column] = cleaned[column].fillna(fill_value)
        for column in other_columns:
            if cleaned[column].isna().any():
                cleaned[column] = _fill_categorical(cleaned[column])
        log.append(f"已使用“{missing_strategy}”处理缺失值")
    else:
        log.append("未修改缺失值")

    converted_dates = 0
    for column in date_columns:
        if column not in cleaned.columns:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(cleaned[column], errors="coerce", format="mixed")
        success_count = int(parsed.notna().sum())
        original_non_null = int(cleaned[column].notna().sum())
        if original_non_null == 0 or success_count / original_non_null >= 0.8:
            cleaned[column] = parsed
            converted_dates += 1
    log.append(f"已标准化 {converted_dates} 个日期字段")

    return cleaned, log

