"""核心模块测试，不依赖浏览器和真实大模型 API。"""

from pathlib import Path

import pandas as pd

from core.chart_builder import build_auto_charts
from core.data_cleaner import clean_dataframe, infer_date_candidates
from core.data_loader import load_dataframe
from core.data_quality import analyze_data_quality
from core.report_exporter import build_markdown_report, markdown_to_pdf
from core.statistics import build_analysis_payload, calculate_statistics
from core.ai_report import generate_local_report


BASE_DIR = Path(__file__).resolve().parents[1]


def load_sample() -> pd.DataFrame:
    path = BASE_DIR / "data" / "sample_sales.csv"
    return load_dataframe(path.read_bytes(), path.name)


def test_load_and_quality_analysis() -> None:
    df = load_sample()
    quality = analyze_data_quality(df)
    assert df.shape == (30, 10)
    assert quality["duplicate_count"] == 1
    assert not quality["missing"].empty
    assert not quality["outliers"].empty
    assert 0 <= quality["score"] <= 100


def test_cleaning_and_date_conversion() -> None:
    df = load_sample()
    candidates = infer_date_candidates(df)
    assert "订单日期" in candidates

    cleaned, log = clean_dataframe(
        df,
        remove_duplicates=True,
        missing_strategy="数值中位数 + 文本众数填充",
        date_columns=["订单日期"],
        trim_text=True,
    )
    assert len(cleaned) == 29
    assert cleaned.isna().sum().sum() == 0
    assert pd.api.types.is_datetime64_any_dtype(cleaned["订单日期"])
    assert log


def test_statistics_charts_and_reports() -> None:
    df = load_sample()
    cleaned, log = clean_dataframe(
        df,
        remove_duplicates=True,
        missing_strategy="数值中位数 + 文本众数填充",
        date_columns=["订单日期"],
        trim_text=True,
    )
    quality = analyze_data_quality(cleaned)
    statistics = calculate_statistics(cleaned)
    charts = build_auto_charts(cleaned)
    payload = build_analysis_payload(cleaned, quality, statistics)
    ai_report = generate_local_report(payload)

    assert not statistics["numeric"].empty
    assert len(charts) >= 3
    assert "时间趋势" in charts[0]["title"]
    assert "核心发现" in ai_report

    markdown = build_markdown_report(
        file_name="sample_sales.csv",
        df=cleaned,
        quality=quality,
        statistics=statistics,
        ai_report=ai_report,
        cleaning_log=log,
    )
    pdf = markdown_to_pdf(markdown)
    assert markdown.startswith("# AI 智能数据分析报告")
    assert pdf.startswith(b"%PDF")

