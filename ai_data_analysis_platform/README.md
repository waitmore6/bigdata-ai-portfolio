# DataMind AI：智能数据分析平台

基于 Python 与 Streamlit 构建的数据分析工具。上传 CSV 或 Excel 后，系统可自动完成数据预览、质量检测、清洗、统计分析、ECharts 可视化和 AI 分析报告导出。

> 在线演示：部署完成后将在此补充访问链接。

## 核心功能

- 支持 CSV、XLSX、XLS 文件上传与前 20 行预览
- 检测缺失值、重复记录、IQR 异常值、字段类型问题和常量字段
- 支持去重、缺失值填充、日期标准化和文本去空格
- 自动生成均值、总和、极值、标准差、分位数与分类字段统计
- 根据字段类型生成趋势图、排行榜、饼图和分布图
- 支持 OpenAI、DeepSeek、通义千问，以及无需 Key 的本地规则分析
- 支持导出 Markdown 和 PDF 报告

## 快速开始

```powershell
cd ai_data_analysis_platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

启动后访问 `http://localhost:8501`。没有自己的数据时，可点击页面左侧的“加载演示数据”。

## AI API 配置（可选）

复制 `.env.example` 为 `.env`，按需填写：

```env
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
DASHSCOPE_API_KEY=
```

未配置 API Key 时，平台仍会使用本地规则生成分析报告。请勿提交 `.env` 文件。

## 测试

```powershell
python -m pytest -q
```

项目自带 `data/sample_sales.csv`，其中包含缺失值、重复记录和异常金额，便于验证完整分析流程。
