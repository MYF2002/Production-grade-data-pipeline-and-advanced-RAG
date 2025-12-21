import json
import re
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter, Language

def split_code_and_text(text):
    """
    将文本分割为代码块和普通文本
    """
    pattern = r"```(\w*)\n(.*?)```"
    parts = []
    last_end = 0
    
    for match in re.finditer(pattern, text, re.DOTALL):
        start, end = match.span()
        
        # 代码块前的文本
        if start > last_end:
            parts.append({"type": "text", "content": text[last_end:start]})
            
        # 代码块
        lang = match.group(1)
        code_content = match.group(2)
        # 如果没有指定语言，默认为 python (或者可以根据需求调整)
        language = Language.PYTHON 
        if lang.lower() in ['js', 'javascript']:
            language = Language.JS
        elif lang.lower() in ['java']:
            language = Language.JAVA
        elif lang.lower() in ['go']:
            language = Language.GO
        elif lang.lower() in ['cpp', 'c++']:
            language = Language.CPP
            
        parts.append({"type": "code", "content": code_content, "language": language})
        
        last_end = end
        
    # 剩余文本
    if last_end < len(text):
        parts.append({"type": "text", "content": text[last_end:]})
        
    if not parts: # 如果没有匹配到代码块，则整体为文本
        parts.append({"type": "text", "content": text})
        
    return parts

def determine_chunk_size(text, content_type):
    """
    根据内容密度和类型决定 chunk_size
    """
    if content_type == "code":
        return 600 # 代码块通常需要更多上下文
        
    # 简单的密度检测：如果包含大量列表项或短行，视为高密度
    lines = text.split('\n')
    short_lines = sum(1 for line in lines if len(line.strip()) < 50 and len(line.strip()) > 0)
    density_ratio = short_lines / len(lines) if lines else 0
    
    if density_ratio > 0.4:
        # 高密度内容（列表、短句等），使用较小的 chunk_size
        return 300
    else:
        # 叙述性文本，使用较大的 chunk_size
        return 800

def chunk_documents(input_file, output_file):
    # 1. 定义分块器
    # Markdown分块配置
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    chunks_data = []
    
    # 读取输入文件
    print(f"Reading from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            source = doc.get('source', '')
            content = doc.get('content', '')
            file_type = doc.get('file_type', '')
            page = doc.get('page', None)
            is_table = doc.get('is_table', False)

            # 表格不切分
            if is_table:
                chunk_meta = {
                    "source": source,
                    "file_type": file_type,
                    "page": page,
                    "content_type": "table",
                    "chunk_size": len(content), # 记录实际长度
                    "chunk_index": 0 
                }
                chunks_data.append({
                    "text": content,
                    "metadata": chunk_meta
                })
                continue

            # Markdown 结构化分块
            md_docs = md_splitter.split_text(content)
            
            chunk_global_index = 0
            
            for md_doc in md_docs:
                # 获取当前Markdown块的元数据（标题）
                base_meta = md_doc.metadata.copy()
                base_meta['source'] = source
                base_meta['file_type'] = file_type
                if page:
                    base_meta['page'] = page
                
                # 内容类型识别 (Code vs Text)
                segments = split_code_and_text(md_doc.page_content)
                
                for seg in segments:
                    content_type = "text"
                    if seg['type'] == 'code':
                        content_type = "code"
                        
                    # 动态决定 chunk_size
                    chunk_size = determine_chunk_size(seg['content'], content_type)
                    chunk_overlap = int(chunk_size * 0.1) # 10% overlap
                    
                    if content_type == 'code':
                        # 代码块分块策略
                        splitter = RecursiveCharacterTextSplitter.from_language(
                            language=seg['language'], 
                            chunk_size=chunk_size, 
                            chunk_overlap=chunk_overlap
                        )
                    else:
                        # 普通文本分块策略
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap
                        )
                        
                    sub_docs = splitter.create_documents([seg['content']])
                    
                    # 4. 元数据富集与结果收集
                    for sub_doc in sub_docs:
                        chunk_meta = base_meta.copy()
                        chunk_meta['chunk_index'] = chunk_global_index
                        chunk_meta['content_type'] = content_type
                        chunk_meta['chunk_size'] = chunk_size # 记录使用的 chunk_size
                        
                        chunks_data.append({
                            "text": sub_doc.page_content,
                            "metadata": chunk_meta
                        })
                        chunk_global_index += 1

    # 写入输出文件
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks_data:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    print(f"分块完成，共生成 {len(chunks_data)} 个分块。结果已保存至 {output_file}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Advanced Chunker")
    parser.add_argument("--input_file", type=str, default="data/output/contents.jsonl", help="Path to input JSONL file")
    parser.add_argument("--output_file", type=str, default="data/output/chunks.jsonl", help="Path to output JSONL file")
    
    args = parser.parse_args()
    
    chunk_documents(args.input_file, args.output_file)
