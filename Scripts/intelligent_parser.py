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

import argparse


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
        "Heading 1": "# ",
        "Heading 2": "## ",
        "Heading 3": "### ",
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
    results = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 提取页面文本
        text = page.get_text()
        if text:
            results.append({
                "content": f"# 第{page_num+1}页\n{text}",
                "page": page_num + 1,
                "is_table": False
            })
            
        # 提取表格
        tables = page.find_tables()
        for table in tables:
            data = table.extract()
            if data:
                try:
                    # 尝试将表格转换为Markdown
                    if len(data) > 1:
                        df = pd.DataFrame(data[1:], columns=data[0])
                    else:
                        df = pd.DataFrame(data)
                        
                    markdown_table = df.to_markdown(index=False)
                    
                    results.append({
                        "content": f"[TABLE] Page {page_num+1}\n{markdown_table}",
                        "page": page_num + 1,
                        "is_table": True
                    })
                except Exception as e:
                    print(f"Error processing table on page {page_num+1}: {e}")
                    
    return results
    




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
                    parsed_data = parse_file(str(file_path))
                    
                    # 统一转换为列表格式
                    if not isinstance(parsed_data, list):
                        parsed_data = [{"content": parsed_data}]
                        
                    for item in parsed_data:
                        obj = {
                            "source": str(file_path),
                            "file_type": file_path.suffix.lstrip(".").lower(),
                        }
                        
                        # 如果是字典（如PDF解析结果），则合并元数据
                        if isinstance(item, dict):
                            obj.update(item)
                        else:
                            # 字符串内容（其他格式）
                            obj["content"] = item
                            
                        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        
                    print(f"成功解析文件: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Intelligent Parser")
    parser.add_argument("--input_dir", type=str, default="data/input", help="Path to input directory")
    parser.add_argument("--output_file", type=str, default="data/output/parsed.jsonl", help="Path to output JSONL file")
    
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_file)
