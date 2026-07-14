"""根据字段类型自动构建 ECharts 配置。"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from core.data_cleaner import infer_date_candidates


COLORS = ["#7057ff", "#2dd4bf", "#ffb454", "#ff6b8a", "#5ca8ff", "#a78bfa", "#34d399", "#f97316"]


def _python_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), 4)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _base_options(title: str) -> dict:
    return {
        "color": COLORS,
        "animationDuration": 650,
        "tooltip": {"trigger": "axis", "backgroundColor": "rgba(20, 24, 40, .94)"},
        "grid": {"left": "3%", "right": "4%", "bottom": "4%", "containLabel": True},
        "textStyle": {"fontFamily": "Inter, Microsoft YaHei, sans-serif"},
        "aria": {"enabled": True, "description": title},
    }


def _histogram_chart(df: pd.DataFrame, column: str) -> dict | None:
    series = df[column].dropna()
    if len(series) < 2 or series.nunique() < 2:
        return None
    bin_count = min(15, max(5, int(math.sqrt(len(series)))))
    counts, edges = np.histogram(series, bins=bin_count)
    labels = [f"{edges[index]:.2f} ~ {edges[index + 1]:.2f}" for index in range(len(edges) - 1)]
    options = _base_options(f"{column} 分布")
    options.update(
        {
            "xAxis": {"type": "category", "data": labels, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value", "name": "记录数"},
            "series": [
                {
                    "name": "记录数",
                    "type": "bar",
                    "data": counts.astype(int).tolist(),
                    "itemStyle": {"borderRadius": [5, 5, 0, 0]},
                }
            ],
        }
    )
    return {"title": f"{column} · 分布情况", "options": options}


def _category_count_chart(df: pd.DataFrame, column: str) -> dict | None:
    counts = df[column].fillna("缺失").astype(str).value_counts().head(10)
    if counts.empty:
        return None
    options = _base_options(f"{column} 类别数量")
    options.update(
        {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "value", "name": "记录数"},
            "yAxis": {"type": "category", "data": counts.index[::-1].tolist()},
            "series": [
                {
                    "name": "记录数",
                    "type": "bar",
                    "data": counts.values[::-1].astype(int).tolist(),
                    "itemStyle": {"borderRadius": [0, 6, 6, 0]},
                    "label": {"show": True, "position": "right"},
                }
            ],
        }
    )
    return {"title": f"{column} · Top 10 类别", "options": options}


def _pie_chart(df: pd.DataFrame, column: str) -> dict | None:
    counts = df[column].fillna("缺失").astype(str).value_counts()
    if counts.empty or len(counts) < 2 or len(counts) > 8:
        return None
    options = _base_options(f"{column} 占比")
    options.update(
        {
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"bottom": 0, "type": "scroll"},
            "series": [
                {
                    "name": column,
                    "type": "pie",
                    "radius": ["42%", "68%"],
                    "center": ["50%", "45%"],
                    "avoidLabelOverlap": True,
                    "data": [
                        {"name": str(name), "value": int(value)}
                        for name, value in counts.items()
                    ],
                    "label": {"formatter": "{b}\n{d}%"},
                }
            ],
        }
    )
    return {"title": f"{column} · 构成占比", "options": options}


def _ranking_chart(df: pd.DataFrame, category: str, value: str) -> dict | None:
    grouped = (
        df[[category, value]]
        .dropna()
        .groupby(category, as_index=False)[value]
        .sum()
        .sort_values(value, ascending=False)
        .head(10)
    )
    if grouped.empty or len(grouped) < 2:
        return None
    grouped = grouped.iloc[::-1]
    options = _base_options(f"{category} 按 {value} 排名")
    options.update(
        {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "value", "name": value},
            "yAxis": {"type": "category", "data": grouped[category].astype(str).tolist()},
            "series": [
                {
                    "name": value,
                    "type": "bar",
                    "data": [_python_value(value_) for value_ in grouped[value]],
                    "itemStyle": {"borderRadius": [0, 6, 6, 0]},
                    "label": {"show": True, "position": "right"},
                }
            ],
        }
    )
    return {"title": f"{category} · {value} 排行榜", "options": options}


def _time_series_chart(df: pd.DataFrame, date_column: str, value_column: str) -> dict | None:
    subset = df[[date_column, value_column]].dropna().copy()
    if subset.empty:
        return None
    subset["_date"] = pd.to_datetime(subset[date_column]).dt.date
    grouped = subset.groupby("_date", as_index=False)[value_column].sum().sort_values("_date")
    if len(grouped) < 2:
        return None
    if len(grouped) > 200:
        grouped = grouped.iloc[:: max(len(grouped) // 200, 1)].head(200)

    options = _base_options(f"{value_column} 时间趋势")
    options.update(
        {
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [str(value) for value in grouped["_date"]],
                "boundaryGap": False,
            },
            "yAxis": {"type": "value", "name": value_column, "scale": True},
            "dataZoom": [{"type": "inside"}, {"type": "slider", "height": 18}],
            "series": [
                {
                    "name": value_column,
                    "type": "line",
                    "smooth": True,
                    "showSymbol": len(grouped) <= 40,
                    "data": [_python_value(value) for value in grouped[value_column]],
                    "areaStyle": {"opacity": 0.12},
                    "lineStyle": {"width": 3},
                }
            ],
        }
    )
    return {"title": f"{value_column} · 时间趋势", "options": options, "height": "420px"}


def build_auto_charts(df: pd.DataFrame, max_charts: int = 6) -> list[dict]:
    """按优先级生成折线、排行榜、饼图、柱状图和分布图。"""
    working_df = df.copy()
    # 图表推荐独立识别日期型文本，用户不必先执行清洗才能看到趋势图。
    for column in infer_date_candidates(working_df):
        if not pd.api.types.is_datetime64_any_dtype(working_df[column]):
            working_df[column] = pd.to_datetime(working_df[column], errors="coerce", format="mixed")

    charts: list[dict] = []
    numeric_columns = list(working_df.select_dtypes(include="number").columns)
    date_columns = [
        column
        for column in working_df.columns
        if pd.api.types.is_datetime64_any_dtype(working_df[column])
    ]
    categorical_columns = [
        column
        for column in working_df.columns
        if column not in numeric_columns
        and column not in date_columns
        and 1 < working_df[column].nunique(dropna=True) <= 50
    ]

    if date_columns and numeric_columns:
        chart = _time_series_chart(working_df, date_columns[0], numeric_columns[0])
        if chart:
            charts.append(chart)

    if categorical_columns and numeric_columns:
        chart = _ranking_chart(working_df, categorical_columns[0], numeric_columns[0])
        if chart:
            charts.append(chart)

    for column in categorical_columns[:3]:
        if len(charts) >= max_charts:
            break
        pie = _pie_chart(working_df, column)
        chart = pie or _category_count_chart(working_df, column)
        if chart:
            charts.append(chart)

    for column in numeric_columns[:3]:
        if len(charts) >= max_charts:
            break
        chart = _histogram_chart(working_df, column)
        if chart:
            charts.append(chart)

    return charts[:max_charts]

