# DataMind AI：AI 智能数据分析平台

一个适合大数据技术、数据分析、Python 全栈方向学生写进简历的完整项目。用户上传 CSV 或 Excel 后，系统自动完成数据读取、质量检测、可配置清洗、描述性统计、ECharts 可视化、AI 分析报告和 Markdown/PDF 导出。

项目默认带有本地规则分析，因此没有 API Key 也能完整演示；配置 Key 后可切换 OpenAI、DeepSeek 或通义千问。

## 1. 项目目录结构

```text
ai_data_analysis_platform/
├─ app.py                       # Streamlit 页面入口与交互流程
├─ core/
│  ├─ __init__.py
│  ├─ data_loader.py            # CSV / Excel 读取与编码兼容
│  ├─ data_quality.py           # 缺失、重复、异常、类型检测
│  ├─ data_cleaner.py           # 去重、填充、日期标准化
│  ├─ statistics.py             # 描述性统计与 AI 摘要
│  ├─ chart_builder.py          # 自动生成 ECharts 配置
│  ├─ ai_report.py              # 多模型调用与本地兜底
│  └─ report_exporter.py        # Markdown / PDF 导出
├─ assets/
│  └─ style.css                 # 页面视觉样式
├─ data/
│  └─ sample_sales.csv          # 含缺失、重复和异常值的演示数据
├─ tests/
│  └─ test_core.py              # 核心功能自动化测试
├─ .streamlit/
│  └─ config.toml               # Streamlit 主题与上传限制
├─ .env.example                 # API Key 配置模板
├─ .gitignore
├─ requirements.txt
├─ run.bat                      # Windows 一键运行
└─ README.md
```

## 2. 技术选型理由

| 技术 | 用途 | 选择理由 |
|---|---|---|
| Streamlit | Web 页面与交互 | 全 Python 开发，上传、表格、指标卡、下载组件齐全，适合学生快速做出可展示项目 |
| pandas / NumPy | 数据处理 | CSV/Excel 读取、缺失处理、统计分析和 IQR 异常检测成熟稳定 |
| Apache ECharts | 交互图表 | 图表效果专业，支持柱状图、折线图、饼图、缩放和排行榜 |
| OpenAI Python SDK | AI 调用 | OpenAI 使用 Responses API；DeepSeek、通义千问使用兼容接口，便于统一封装 |
| ReportLab | PDF 导出 | 纯 Python 生成 PDF，不要求浏览器或额外系统服务 |
| pytest | 自动化测试 | 证明项目不只是“能打开页面”，核心数据流程可验证 |

为什么不优先使用 Flask/Django：本项目重点是数据分析流程和作品展示，而不是复杂权限、订单或后台管理。Streamlit 能显著减少前端模板和接口代码，让学生把精力放在数据处理、产品逻辑和 AI 能力上。

## 3. 开发步骤

1. 设计数据处理流程：上传 → 读取 → 质量检测 → 清洗 → 统计 → 图表 → AI 报告 → 导出。
2. 封装 CSV/Excel 读取，兼容 UTF-8、GBK、GB18030 等常见编码。
3. 实现缺失值、重复值、IQR 异常值、疑似错误字段类型检测。
4. 实现可视化清洗配置，并用 Session State 保存当前工作数据。
5. 根据日期、数值和分类字段自动选择折线图、排行榜、饼图、柱状图或直方图。
6. 只向模型发送聚合统计，不默认发送原始数据。
7. 实现 OpenAI、DeepSeek、通义千问适配和本地兜底。
8. 生成 Markdown / PDF 报告，补充示例数据、测试和项目文档。

## 4. 核心功能

- 支持 `.csv`、`.xlsx`、`.xls`
- 数据前 20 行预览、字段类型、非空数、唯一值数
- 缺失值、重复行、IQR 异常值、类型问题、常量字段检测
- 去重、删除缺失行、均值/中位数/众数填充、日期标准化、文本去空格
- 均值、中位数、最大值、最小值、总和、标准差、四分位数
- 自动折线图、排行榜、饼图、分类柱状图、数值分布图
- OpenAI / DeepSeek / 通义千问 / 本地规则分析
- Markdown 和中文 PDF 报告下载
- 演示数据和自动化测试

## 5. 如何运行

### 方式 A：Windows 一键启动

双击项目目录中的 `run.bat`。首次运行会创建虚拟环境并安装依赖。

### 方式 B：命令行启动

```powershell
cd ai_data_analysis_platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

浏览器通常会自动打开：

```text
http://localhost:8501
```

如果暂时没有自己的数据，点击左侧“加载演示数据”即可体验。

### API Key 配置

复制 `.env.example` 为 `.env`，按需填写：

```env
OPENAI_API_KEY=你的_OpenAI_Key
DEEPSEEK_API_KEY=你的_DeepSeek_Key
DASHSCOPE_API_KEY=你的_阿里云百炼_Key
```

不要把 `.env` 上传到 GitHub。页面侧边栏也可以临时输入 Key，输入值只用于当前应用会话。

模型名称可以直接在页面修改，避免云厂商更新模型后必须改代码。

### 运行测试

```powershell
python -m pytest -q
```

## 6. 功能截图占位

建议运行后截取以下页面，并放到 `docs/screenshots/`：

```text
docs/screenshots/
├─ 01-home.png          # 首页与上传区域
├─ 02-quality.png       # 数据质量检测
├─ 03-cleaning.png      # 数据清洗配置
├─ 04-charts.png        # 自动图表
└─ 05-ai-report.png     # AI 分析报告与导出
```

然后在 README 中加入：

```markdown
![首页](docs/screenshots/01-home.png)
![自动图表](docs/screenshots/04-charts.png)
```

## 7. 简历描述写法

### 简洁版

**DataMind AI 智能数据分析平台｜Python、Streamlit、pandas、ECharts、大模型 API**

- 独立开发支持 CSV/Excel 上传的数据分析平台，实现数据预览、缺失/重复/IQR 异常检测、可配置清洗和描述性统计。
- 根据字段类型自动生成趋势图、排行榜、饼图和分布图，并支持 Markdown/PDF 分析报告导出。
- 封装 OpenAI、DeepSeek、通义千问多模型调用，仅传输聚合统计并提供本地规则兜底，提升隐私性与演示稳定性。
- 使用模块化目录和 pytest 编写核心流程测试，增强代码可维护性和二次开发能力。

### 面试介绍思路

可以重点讲三个设计：

1. 为什么只发送聚合数据给大模型：降低隐私风险、减少 Token 成本、减少模型对原始明细的误读。
2. 为什么使用 IQR 检测异常值：不要求数据服从正态分布，比固定阈值更通用，但检测结果只是提示，不应自动删除。
3. 为什么有本地兜底：API 欠费、网络异常或 Key 未配置时，项目仍能完成现场演示。

## 8. 后续可扩展功能

- 多工作表选择、批量文件合并和大文件分块读取
- 自定义字段类型、清洗规则模板、撤销/重做
- 相关性热力图、回归分析、聚类、时间序列预测
- 用户用自然语言提问，系统自动生成 pandas / SQL 分析步骤
- 接入 MySQL、Hive、ClickHouse、Spark、Hadoop HDFS
- 用户登录、历史项目、报告版本管理
- Celery / Redis 异步任务，处理超大文件
- FastAPI 前后端分离和 Vue/React 专业后台
- Docker、GitHub Actions、Streamlit Community Cloud 部署
- 敏感字段识别、脱敏、权限控制和操作审计

## 9. 项目说明

- 数据质量评分是为了方便展示的启发式分数，不是行业标准。
- IQR 异常值检测用于提示人工复核，不会自动删除数据。
- AI 结论用于辅助探索，不应替代业务专家判断。
- 演示数据中的金额异常、缺失评分和重复记录是故意保留的，便于展示检测能力。

