from argparse import FileType
from docx import Document
import json
from pathlib import Path
import pymupdf
import pandas as pd
import os
# 禁用 unstructured 的 analytics
os.environ["SCARF_NO_ANALYTICS"] = "true"

from unstructured.partition.html import partition_html
from unstructured.partition.md import partition_md
from unstructured.documents.elements import Title, NarrativeText

def parse_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def parse_html(file_path):

    elements = partition_html(filename=file_path)
    return "\n".join([element.text for element in elements if isinstance(element, NarrativeText)])

def parse_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text



def parse_docx(file_path):
    style_map = {
        "Heading 1": "#",
        "Heading 2": "##",
        "Heading 3": "###",
    }
    doc = Document(file_path)
    contents = []
    for para in doc.paragraphs:
        style = para.style.name if para.style else "Normal"
        prefix = style_map.get(style, "")
        contents.append(f"{prefix}{para.text}")
    text = "\n".join(contents)
    return text


def parse_pdf(file_path):
    doc = pymupdf.open(file_path)
    chunks = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        header = f"## 第{page_num+1}页"
        text = page.get_text()
        chunks.append(header)
        if text:
            chunks.append(text)
        tables = page.find_tables()
        for table in tables:
            data = table.extract()
            if data and len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                chunks.append(df.to_markdown(index=False))
    return "\n\n".join(chunks)
    




PARSER = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "md": parse_markdown,
    "html": parse_html,
    "txt": parse_txt,
}

def parse_file(file_path):
    filetype = Path(file_path).suffix.lstrip(".").lower()
    parser = PARSER.get(filetype)
    if parser:
        return parser(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {filetype}")


def process_directory(input_path, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for file_path in Path(input_path).iterdir():
            if file_path.is_file():
                try:
                    content = parse_file(str(file_path))
                    obj = {
                        "source": str(file_path),
                        "content": content,
                        "file_type": file_path.suffix.lstrip(".").lower(),
                    }
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    print(f"成功解析文件: {file_path}")
                except Exception as e:
                    print(f"解析文件 {file_path} 时出错: {e}")


if __name__ == "__main__":
    input_path = r"data/input"
    output_path = r"data/output/parsed.jsonl"
    process_directory(input_path, output_path)
