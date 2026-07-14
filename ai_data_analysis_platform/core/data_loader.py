"""CSV / Excel 数据读取模块。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


class DataLoadError(ValueError):
    """当上传文件无法转换为 DataFrame 时抛出。"""


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    """尝试常见中文编码读取 CSV。"""
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.ParserError:
            # 对分隔符不标准的 CSV，交给 Python 引擎自动识别。
            try:
                return pd.read_csv(BytesIO(file_bytes), encoding=encoding, sep=None, engine="python")
            except Exception as exc:  # 继续尝试其他编码
                last_error = exc
    raise DataLoadError(f"CSV 编码或格式无法识别：{last_error}")


def load_dataframe(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    """根据扩展名读取 CSV 或 Excel，并做最基本的结构检查。"""
    suffix = Path(file_name).suffix.lower()
    try:
        if suffix == ".csv":
            df = _read_csv(file_bytes)
        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(BytesIO(file_bytes))
        else:
            raise DataLoadError("仅支持 .csv、.xlsx 和 .xls 文件。")
    except DataLoadError:
        raise
    except Exception as exc:
        raise DataLoadError(f"文件读取失败：{exc}") from exc

    if df.empty and len(df.columns) == 0:
        raise DataLoadError("文件中没有可读取的表格数据。")

    # 字段名统一转成字符串，并清除首尾空格，避免后续选择字段时报错。
    df.columns = [str(column).strip() or f"未命名字段_{index + 1}" for index, column in enumerate(df.columns)]
    return df

