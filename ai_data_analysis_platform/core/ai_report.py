"""大模型分析报告模块，支持本地兜底和多个 OpenAI 兼容服务。"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


AI_PROVIDERS = {
    "本地规则分析": {
        "env_key": "",
        "default_model": "无需模型",
        "base_url": "",
    },
    "OpenAI": {
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-5.5",
        "base_url": "https://api.openai.com/v1",
    },
    "DeepSeek": {
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
    },
    "通义千问": {
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
}


SYSTEM_PROMPT = """
你是一名谨慎、专业的数据分析师。请根据用户提供的聚合统计信息生成中文分析报告。

规则：
1. 只能使用输入中明确提供的数据，不得编造业务背景、原因、同比、目标或预测。
2. 明确区分“数据事实”“可能解释”“建议验证”，不要把猜测写成结论。
3. 优先指出数据质量风险、重要数值范围、异常情况和可执行建议。
4. 如果数据不足以支持趋势或因果判断，要直接说明。
5. 使用 Markdown，输出 4 个小节：核心发现、数据质量、业务解读、下一步建议。
6. 报告控制在 500~900 个中文字符。
""".strip()


def _format_number(value: Any) -> str:
    if value is None:
        return "无"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def generate_local_report(payload: dict) -> str:
    """不依赖 API 的规则报告，确保项目离线也能完整演示。"""
    dataset = payload["dataset"]
    quality = payload["quality"]
    numeric = payload.get("numeric_statistics", [])
    categorical = payload.get("categorical_statistics", [])

    findings: list[str] = [
        f"当前数据集包含 **{dataset['rows']:,} 行、{dataset['columns']:,} 列**，"
        f"其中数值字段 {len(dataset['numeric_columns'])} 个。"
    ]

    if numeric:
        # 使用均值绝对值最大的字段作为一个客观、可复现的重点字段。
        valid_numeric = [item for item in numeric if isinstance(item.get("均值"), (int, float))]
        if valid_numeric:
            focus = max(valid_numeric, key=lambda item: abs(item["均值"]))
            findings.append(
                f"数值字段 **{focus['字段名']}** 的均值为 {_format_number(focus['均值'])}，"
                f"范围为 {_format_number(focus['最小值'])} 至 {_format_number(focus['最大值'])}，"
                f"总和为 {_format_number(focus['总和'])}。"
            )

    if categorical:
        useful_categories = [
            item
            for item in categorical
            if item.get("唯一值数量", 0) <= max(20, dataset["rows"] * 0.5)
            and not any(word in str(item.get("字段名", "")).lower() for word in ["date", "time", "日期", "时间"])
        ]
        focus = min(
            useful_categories or categorical,
            key=lambda item: item.get("唯一值数量", dataset["rows"] + 1),
        )
        findings.append(
            f"分类字段 **{focus['字段名']}** 包含 {focus['唯一值数量']} 个非空类别，"
            f"最高频值是“{focus['最高频值']}”，出现 {focus['最高频次数']} 次。"
        )

    quality_items: list[str] = [f"综合质量评分为 **{quality['score']}/100**。"]
    if quality["duplicate_rows"]:
        quality_items.append(f"检测到 {quality['duplicate_rows']} 条重复记录。")
    if quality["missing"]:
        top_missing = quality["missing"][0]
        quality_items.append(
            f"缺失最明显的字段是 **{top_missing['字段名']}**，"
            f"缺失 {top_missing['缺失数量']} 个（{top_missing['缺失比例']}%）。"
        )
    if quality["outliers"]:
        outlier = quality["outliers"][0]
        quality_items.append(
            f"字段 **{outlier['字段名']}** 按 IQR 规则发现 {outlier['异常值数量']} 个异常值提示。"
        )
    if len(quality_items) == 1:
        quality_items.append("未检测到明显的缺失、重复或 IQR 异常问题。")

    limitations = (
        "这些结果来自描述性统计，只能说明当前文件中的分布与质量情况；"
        "在缺少业务目标、时间对照和外部基准时，不应直接推断因果关系。"
    )
    suggestions = [
        "先确认缺失值和异常值是否来自录入错误、口径差异或真实极端情况。",
        "结合具体业务目标选择核心指标，并增加时间、地区或产品等维度进行分组比较。",
        "保存清洗规则和指标口径，后续可扩展为定时更新的数据看板。",
    ]

    return "\n".join(
        [
            "### 核心发现",
            *[f"- {item}" for item in findings],
            "",
            "### 数据质量",
            *[f"- {item}" for item in quality_items],
            "",
            "### 业务解读",
            limitations,
            "",
            "### 下一步建议",
            *[f"{index + 1}. {item}" for index, item in enumerate(suggestions)],
        ]
    )


def generate_ai_report(payload: dict, provider: str, api_key: str, model: str) -> str:
    """调用所选模型；失败时返回带错误说明的本地报告。"""
    if provider not in AI_PROVIDERS or provider == "本地规则分析":
        return generate_local_report(payload)
    if not api_key.strip():
        return (
            "> 未提供 API Key，已自动使用本地规则分析。\n\n"
            + generate_local_report(payload)
        )

    provider_info = AI_PROVIDERS[provider]
    client = OpenAI(
        api_key=api_key.strip(),
        base_url=provider_info["base_url"],
        timeout=60.0,
        max_retries=1,
    )
    user_prompt = (
        "下面是经过程序计算的数据聚合摘要。请严格依据这些数据写报告：\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    try:
        if provider == "OpenAI":
            response = client.responses.create(
                model=model.strip() or provider_info["default_model"],
                instructions=SYSTEM_PROMPT,
                input=user_prompt,
            )
            return response.output_text.strip()

        response = client.chat.completions.create(
            model=model.strip() or provider_info["default_model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("模型返回了空内容")
        return content.strip()
    except Exception as exc:
        return (
            f"> {provider} 调用失败：{exc}\n\n"
            "> 已自动切换为本地规则分析，页面其他功能不受影响。\n\n"
            + generate_local_report(payload)
        )

