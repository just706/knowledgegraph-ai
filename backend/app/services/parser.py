"""文件解析：从上传文件中提取纯文本。

支持 TXT / Markdown（直接读取）/ PDF（pypdf 提取）。
docx / 图片 OCR 等留作后续扩展。
"""
import io

from pypdf import PdfReader

# 支持的类型 → 标准化后缀
SUPPORTED_TYPES = {"txt", "md", "markdown", "pdf"}


def normalize_file_type(filename: str) -> str:
    """从文件名提取标准化类型；不支持时返回空串。"""
    if "." not in filename:
        return ""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "markdown":
        ext = "md"
    return ext if ext in SUPPORTED_TYPES else ""


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """从文件字节提取纯文本。

    Args:
        file_bytes: 文件原始字节
        file_type: 标准化类型（txt/md/pdf）
    Returns:
        提取后的纯文本（可能为空串，由调用方处理）
    """
    if file_type in ("txt", "md"):
        # 优先 utf-8，失败回退宽松解码
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("utf-8", errors="ignore")

    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
        return "\n".join(parts)

    raise ValueError(f"不支持的文件类型: {file_type}")
