"""AI 智能数据分析平台 - Streamlit 入口文件。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_echarts import st_echarts

from core.ai_report import AI_PROVIDERS, generate_ai_report, generate_local_report
from core.chart_builder import build_auto_charts
from core.data_cleaner import clean_dataframe, infer_date_candidates
from core.data_loader import DataLoadError, load_dataframe
from core.data_quality import analyze_data_quality
from core.report_exporter import build_markdown_report, markdown_to_pdf
from core.statistics import build_analysis_payload, calculate_statistics


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="DataMind AI · 智能数据分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    """加载项目自定义样式。"""
    css_path = BASE_DIR / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_state() -> None:
    """初始化页面会话状态。"""
    defaults = {
        "original_df": None,
        "working_df": None,
        "file_name": "",
        "source_key": "",
        "ai_report": "",
        "cleaning_log": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_dataset(df: pd.DataFrame, file_name: str, source_key: str) -> None:
    """把新数据集写入会话状态，并清除旧分析结果。"""
    st.session_state.original_df = df.copy()
    st.session_state.working_df = df.copy()
    st.session_state.file_name = file_name
    st.session_state.source_key = source_key
    st.session_state.ai_report = ""
    st.session_state.cleaning_log = []


def load_uploaded_file(uploaded_file) -> None:
    """读取用户上传的数据文件。"""
    file_bytes = uploaded_file.getvalue()
    digest = hashlib.md5(file_bytes, usedforsecurity=False).hexdigest()
    source_key = f"{uploaded_file.name}:{digest}"
    if source_key == st.session_state.source_key:
        return

    df = load_dataframe(file_bytes, uploaded_file.name)
    set_dataset(df, uploaded_file.name, source_key)


def load_sample_data() -> None:
    """加载项目自带的演示数据。"""
    sample_path = BASE_DIR / "data" / "sample_sales.csv"
    file_bytes = sample_path.read_bytes()
    df = load_dataframe(file_bytes, sample_path.name)
    set_dataset(df, sample_path.name, "built-in-sample")


def reset_dataset() -> None:
    """恢复最初上传的数据。"""
    if st.session_state.original_df is not None:
        st.session_state.working_df = st.session_state.original_df.copy()
        st.session_state.ai_report = ""
        st.session_state.cleaning_log = ["已恢复为原始数据"]


def render_empty_state() -> None:
    """未加载数据时展示产品介绍。"""
    st.markdown(
        """
        <div class="hero-card">
            <div class="eyebrow">AI-POWERED ANALYTICS</div>
            <h1>让一份表格，自动变成一份分析报告</h1>
            <p>上传 CSV 或 Excel，平台会完成数据体检、清洗、统计、图表推荐和 AI 结论生成。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    features = [
        ("01", "数据体检", "缺失、重复、异常和类型问题"),
        ("02", "智能清洗", "常用清洗策略可视化配置"),
        ("03", "自动图表", "按字段类型生成 ECharts 图表"),
        ("04", "AI 报告", "支持 OpenAI、DeepSeek、通义千问"),
    ]
    for col, (number, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                    <span>{number}</span>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.info("请在左侧上传文件，或点击“加载演示数据”直接体验完整流程。")


def dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """避免超长文本影响页面展示。"""
    display_df = df.copy()
    for column in display_df.select_dtypes(include=["object", "string"]).columns:
        display_df[column] = display_df[column].astype("string").str.slice(0, 100)
    return display_df


def render_sidebar() -> dict:
    """渲染文件上传和 AI 配置区域。"""
    with st.sidebar:
        st.markdown("## DataMind AI")
        st.caption("从数据文件到分析结论的一站式平台")
        st.markdown("---")

        uploaded_file = st.file_uploader(
            "上传 Excel 或 CSV",
            type=["csv", "xlsx", "xls"],
            help="建议单文件不超过 200 MB。",
        )
        if uploaded_file is not None:
            try:
                load_uploaded_file(uploaded_file)
            except DataLoadError as exc:
                st.error(str(exc))

        sample_col, reset_col = st.columns(2)
        if sample_col.button("加载演示数据", width="stretch"):
            load_sample_data()
            st.rerun()
        if reset_col.button(
            "恢复原数据",
            width="stretch",
            disabled=st.session_state.original_df is None,
        ):
            reset_dataset()
            st.rerun()

        st.markdown("---")
        st.markdown("### AI 报告配置")
        provider = st.selectbox("模型服务", list(AI_PROVIDERS.keys()))
        provider_info = AI_PROVIDERS[provider]

        default_key = os.getenv(provider_info["env_key"], "") if provider != "本地规则分析" else ""
        api_key = st.text_input(
            "API Key",
            value=default_key,
            type="password",
            disabled=provider == "本地规则分析",
            help=f"也可以在 .env 中配置 {provider_info['env_key']}。",
        )
        model = st.text_input(
            "模型名称",
            value=provider_info["default_model"],
            disabled=provider == "本地规则分析",
        )
        st.caption("未配置 Key 时仍可使用本地规则生成报告。")

        if st.session_state.working_df is not None:
            st.markdown("---")
            st.markdown("### 当前数据")
            st.caption(st.session_state.file_name)
            st.write(
                f"{len(st.session_state.working_df):,} 行 × "
                f"{len(st.session_state.working_df.columns):,} 列"
            )

    return {"provider": provider, "api_key": api_key, "model": model}


def render_overview(df: pd.DataFrame, quality: dict) -> None:
    """渲染页面顶部关键指标。"""
    st.markdown(
        f"""
        <div class="page-title">
            <div>
                <div class="eyebrow">DATA WORKSPACE</div>
                <h1>{st.session_state.file_name}</h1>
                <p>当前展示的是清洗后的工作数据，可随时恢复原文件。</p>
            </div>
            <div class="status-pill">● 分析就绪</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    missing_total = int(df.isna().sum().sum())
    duplicate_total = int(df.duplicated().sum())
    outlier_total = int(quality["outliers"]["outlier_count"].sum()) if not quality["outliers"].empty else 0
    numeric_total = len(df.select_dtypes(include="number").columns)

    cols = st.columns(5)
    metrics = [
        ("数据行数", f"{len(df):,}", "records"),
        ("字段数量", f"{len(df.columns):,}", "columns"),
        ("数值字段", f"{numeric_total:,}", "numeric"),
        ("缺失单元格", f"{missing_total:,}", "missing"),
        ("异常值提示", f"{outlier_total:,}", "IQR"),
    ]
    for col, (label, value, hint) in zip(cols, metrics):
        with col:
            st.metric(label, value, hint)

    if duplicate_total:
        st.warning(f"当前数据包含 {duplicate_total} 条重复记录，建议在“数据清洗”中处理。")


def render_preview_tab(df: pd.DataFrame) -> None:
    st.subheader("数据预览")
    st.caption("默认展示前 20 行；表格支持排序、搜索和全屏查看。")
    st.dataframe(dataframe_for_display(df.head(20)), width="stretch", hide_index=True)

    st.subheader("字段信息")
    field_info = pd.DataFrame(
        {
            "字段名": df.columns,
            "数据类型": [str(dtype) for dtype in df.dtypes],
            "非空数量": [int(df[col].notna().sum()) for col in df.columns],
            "缺失数量": [int(df[col].isna().sum()) for col in df.columns],
            "唯一值数量": [int(df[col].nunique(dropna=True)) for col in df.columns],
        }
    )
    st.dataframe(field_info, width="stretch", hide_index=True)


def render_quality_tab(df: pd.DataFrame, quality: dict) -> None:
    st.subheader("数据质量评分")
    score_cols = st.columns([1, 1, 1, 2])
    score_cols[0].metric("综合评分", f"{quality['score']}/100")
    score_cols[1].metric("重复行", quality["duplicate_count"])
    score_cols[2].metric("空字段", quality["empty_column_count"])
    score_cols[3].progress(quality["score"] / 100)

    st.markdown("#### 缺失值检测")
    missing = quality["missing"]
    if missing.empty:
        st.success("没有检测到缺失值。")
    else:
        st.dataframe(missing, width="stretch", hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 异常值检测（IQR）")
        if quality["outliers"].empty:
            st.success("数值字段中未发现明显异常值。")
        else:
            st.dataframe(
                quality["outliers"].rename(columns={"outlier_count": "异常值数量"}),
                width="stretch",
                hide_index=True,
            )
    with col2:
        st.markdown("#### 字段类型问题")
        if quality["type_issues"].empty:
            st.success("没有发现明显的字段类型问题。")
        else:
            st.dataframe(quality["type_issues"], width="stretch", hide_index=True)

    if quality["constant_columns"]:
        st.info("单一值字段：" + "、".join(quality["constant_columns"]))


def render_cleaning_tab(df: pd.DataFrame) -> None:
    st.subheader("数据清洗")
    st.caption("清洗操作默认基于原始数据重新执行，避免多次点击造成不可逆修改。")
    date_candidates = infer_date_candidates(st.session_state.original_df)

    with st.form("cleaning_form"):
        col1, col2 = st.columns(2)
        with col1:
            remove_duplicates = st.checkbox("删除重复行", value=True)
            trim_text = st.checkbox("清除文本首尾空格", value=True)
        with col2:
            missing_strategy = st.selectbox(
                "缺失值处理",
                [
                    "保持不变",
                    "删除含缺失值的行",
                    "数值中位数 + 文本众数填充",
                    "数值均值 + 文本众数填充",
                ],
            )
            date_columns = st.multiselect(
                "标准化日期字段",
                options=list(st.session_state.original_df.columns),
                default=date_candidates,
                help="成功转换的日期将统一为 pandas datetime 类型。",
            )
        submitted = st.form_submit_button("执行数据清洗", type="primary", width="stretch")

    if submitted:
        cleaned_df, cleaning_log = clean_dataframe(
            st.session_state.original_df,
            remove_duplicates=remove_duplicates,
            missing_strategy=missing_strategy,
            date_columns=date_columns,
            trim_text=trim_text,
        )
        st.session_state.working_df = cleaned_df
        st.session_state.cleaning_log = cleaning_log
        st.session_state.ai_report = ""
        st.success("清洗完成，统计和图表已基于新数据刷新。")
        st.rerun()

    if st.session_state.cleaning_log:
        st.markdown("#### 最近一次清洗记录")
        for item in st.session_state.cleaning_log:
            st.write(f"- {item}")

    original_rows = len(st.session_state.original_df)
    current_rows = len(df)
    st.markdown("#### 清洗前后对比")
    compare_cols = st.columns(3)
    compare_cols[0].metric("原始行数", original_rows)
    compare_cols[1].metric("当前行数", current_rows, current_rows - original_rows)
    compare_cols[2].metric("当前缺失值", int(df.isna().sum().sum()))


def render_statistics_tab(statistics: dict) -> None:
    st.subheader("数值字段统计")
    numeric = statistics["numeric"]
    if numeric.empty:
        st.info("当前数据没有可统计的数值字段。")
    else:
        st.dataframe(numeric, width="stretch", hide_index=True)

    st.subheader("分类字段概览")
    categorical = statistics["categorical"]
    if categorical.empty:
        st.info("当前数据没有分类字段。")
    else:
        st.dataframe(categorical, width="stretch", hide_index=True)


def render_charts_tab(df: pd.DataFrame) -> None:
    st.subheader("自动可视化")
    st.caption("系统会根据日期、数值和分类字段的组合自动推荐图表。")
    chart_specs = build_auto_charts(df)
    if not chart_specs:
        st.info("当前字段组合暂时无法生成有意义的图表。")
        return

    for index in range(0, len(chart_specs), 2):
        columns = st.columns(2)
        for offset, col in enumerate(columns):
            chart_index = index + offset
            if chart_index >= len(chart_specs):
                break
            chart = chart_specs[chart_index]
            with col:
                st.markdown(f"#### {chart['title']}")
                st_echarts(
                    options=chart["options"],
                    height=chart.get("height", "390px"),
                    key=f"chart-{chart_index}-{len(df)}",
                )


def render_report_tab(df: pd.DataFrame, quality: dict, statistics: dict, ai_config: dict) -> None:
    st.subheader("AI 分析报告")
    st.caption("仅把数据概况和聚合统计发送给模型，不发送原始明细行。")

    if st.button("生成 / 重新生成分析报告", type="primary"):
        payload = build_analysis_payload(df, quality, statistics)
        with st.spinner("正在整理数据证据并生成报告..."):
            if ai_config["provider"] == "本地规则分析":
                report = generate_local_report(payload)
            else:
                report = generate_ai_report(
                    payload=payload,
                    provider=ai_config["provider"],
                    api_key=ai_config["api_key"],
                    model=ai_config["model"],
                )
            st.session_state.ai_report = report

    if not st.session_state.ai_report:
        payload = build_analysis_payload(df, quality, statistics)
        st.session_state.ai_report = generate_local_report(payload)

    st.markdown(st.session_state.ai_report)

    markdown_report = build_markdown_report(
        file_name=st.session_state.file_name,
        df=df,
        quality=quality,
        statistics=statistics,
        ai_report=st.session_state.ai_report,
        cleaning_log=st.session_state.cleaning_log,
    )

    export_col1, export_col2 = st.columns(2)
    export_col1.download_button(
        "下载 Markdown 报告",
        data=markdown_report,
        file_name="data_analysis_report.md",
        mime="text/markdown",
        width="stretch",
    )
    try:
        pdf_bytes = markdown_to_pdf(markdown_report)
        export_col2.download_button(
            "下载 PDF 报告",
            data=pdf_bytes,
            file_name="data_analysis_report.pdf",
            mime="application/pdf",
            width="stretch",
        )
    except Exception as exc:  # PDF 是附加能力，失败时不影响主流程
        export_col2.error(f"PDF 生成失败：{exc}")


def main() -> None:
    load_css()
    init_state()
    ai_config = render_sidebar()

    if st.session_state.working_df is None:
        render_empty_state()
        return

    df = st.session_state.working_df
    quality = analyze_data_quality(df)
    statistics = calculate_statistics(df)
    render_overview(df, quality)

    tabs = st.tabs(
        [
            "数据预览",
            "质量检测",
            "数据清洗",
            "统计分析",
            "自动图表",
            "AI 报告",
        ]
    )
    with tabs[0]:
        render_preview_tab(df)
    with tabs[1]:
        render_quality_tab(df, quality)
    with tabs[2]:
        render_cleaning_tab(df)
    with tabs[3]:
        render_statistics_tab(statistics)
    with tabs[4]:
        render_charts_tab(df)
    with tabs[5]:
        render_report_tab(df, quality, statistics, ai_config)


if __name__ == "__main__":
    main()

