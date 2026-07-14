"""Markdown 与 PDF 报告导出模块。"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import re

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _dataframe_to_markdown(df: pd.DataFrame, empty_text: str = "无") -> str:
    if df.empty:
        return empty_text
    return df.to_markdown(index=False)


def build_markdown_report(
    *,
    file_name: str,
    df: pd.DataFrame,
    quality: dict,
    statistics: dict,
    ai_report: str,
    cleaning_log: list[str],
) -> str:
    """拼装一份可直接保存到 GitHub 或作品集的 Markdown 报告。"""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    outliers = quality["outliers"].rename(columns={"outlier_count": "异常值数量"})
    cleaning_text = "\n".join(f"- {item}" for item in cleaning_log) or "- 未执行额外清洗"

    return f"""# AI 智能数据分析报告

## 1. 数据概况

- 文件名称：`{file_name}`
- 生成时间：{generated_at}
- 数据规模：{len(df):,} 行 × {len(df.columns):,} 列
- 数据质量评分：{quality['score']}/100
- 重复记录：{quality['duplicate_count']} 条

## 2. 数据清洗记录

{cleaning_text}

## 3. 缺失值检测

{_dataframe_to_markdown(quality['missing'])}

## 4. 异常值检测

{_dataframe_to_markdown(outliers)}

## 5. 数值字段统计

{_dataframe_to_markdown(statistics['numeric'])}

## 6. 分类字段统计

{_dataframe_to_markdown(statistics['categorical'])}

## 7. AI 分析结论

{ai_report}

---

> 本报告由 DataMind AI 根据当前文件的聚合统计自动生成。自动结论用于辅助探索，重要决策仍需结合业务口径和人工复核。
"""


def _clean_markdown(text: str) -> str:
    """把少量 Markdown 标记转换为 ReportLab Paragraph 可读文本。"""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"^\s*[-*]\s+", "• ", text)
    text = re.sub(r"^\s*\d+\.\s+", "• ", text)
    return text


def markdown_to_pdf(markdown_text: str) -> bytes:
    """使用 ReportLab 内置中文 CID 字体生成 PDF 字节。"""
    buffer = BytesIO()
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:
        font_name = "Helvetica"

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=20,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#24253d"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=20,
        textColor=colors.HexColor("#5b45d6"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=16,
        textColor=colors.HexColor("#333647"),
        wordWrap="CJK",
    )

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="AI 智能数据分析报告",
    )
    story = []
    table_lines: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table_lines
        if not table_lines:
            return
        max_columns = max(len(row) for row in table_lines)
        normalized = [row + [""] * (max_columns - len(row)) for row in table_lines]
        table = Table(normalized, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ece9ff")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#3f318e")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8d9e6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8fc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([table, Spacer(1, 8)])
        table_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                continue
            table_lines.append(cells)
            continue

        flush_table()
        if not line or line == "---":
            story.append(Spacer(1, 5))
        elif line.startswith("# "):
            story.append(Paragraph(_clean_markdown(line[2:]), title_style))
        elif line.startswith("## "):
            story.append(Paragraph(_clean_markdown(line[3:]), heading_style))
        elif line.startswith("### "):
            story.append(Paragraph(_clean_markdown(line[4:]), heading_style))
        elif line.startswith("> "):
            story.append(Paragraph(_clean_markdown(line[2:]), body_style))
        else:
            story.append(Paragraph(_clean_markdown(line), body_style))
            story.append(Spacer(1, 2))
    flush_table()

    document.build(story)
    return buffer.getvalue()

