import json
import re
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def get_separators_for_language(language):
    """
    根据编程语言返回分割符（regex）
    """
    language = language.lower() if language else ""
    
    # 默认分隔符
    separators = [r"\n\n", r"\n", " ", ""]
    
    if language in ["py", "python"]:
        separators = [r"\nclass\s+", r"\ndef\s+", r"\n\n", r"\n", " ", ""]
    elif language in ["js", "javascript", "ts", "typescript"]:
        separators = [r"\nclass\s+", r"\nfunction\s+", r"\ninterface\s+", r"\ntype\s+", r"\nconst\s+", r"\nlet\s+", r"\nvar\s+", r"\n\n", r"\n", " ", ""]
    elif language in ["java"]:
        separators = [r"\nclass\s+", r"\npublic\s+", r"\nprotected\s+", r"\nprivate\s+", r"\n\n", r"\n", " ", ""]
    elif language in ["go"]:
        separators = [r"\nfunc\s+", r"\ntype\s+", r"\n\n", r"\n", " ", ""]
    elif language in ["cpp", "c++", "c"]:
        separators = [r"\nclass\s+", r"\nstruct\s+", r"\nvoid\s+", r"\nint\s+", r"\n\n", r"\n", " ", ""]
        
    return separators

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
        language = match.group(1)
        code_content = match.group(2)
        
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
    #代码块小于800的不进行切分，大于800的按类和函数进行切分
    if content_type == "code":
        return 800 # 允许切分代码块，设置合理的长度
        
    #根据文本密度决定 chunk_size
    #统计小于50个字符的行的占比，超过40%则视为高密度
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
    
    # 状态变量：用于在行之间保持标题上下文
    last_source = None
    current_headers = {}

    # 读取输入文件
    print(f"Reading from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            source = doc.get('source', '')
            
            # 如果切换了文件，重置标题上下文
            if source != last_source:
                current_headers = {}
                last_source = source
                
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
                # 注入当前上下文的标题
                chunk_meta.update(current_headers)
                
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
                
                # 更新当前上下文标题（如果当前块有标题，则更新；否则保留之前的标题）
                # 注意：这里假设MarkdownHeaderTextSplitter返回的每个doc如果属于同一层级，会覆盖之前的
                if md_doc.metadata:
                    # 只有当出现了新的标题时才更新对应的层级
                    # 但是由于结构化分块的特性，doc.metadata 包含了该内容所属的完整路径
                    # 所以我们可以直接合并/覆盖
                    current_headers.update(md_doc.metadata)
                
                # 将累积的标题信息合并回 base_meta (以防当前 doc metadata 不完整，尽管通常 split_text 会处理好)
                # 但更重要的是，我们需要确保 base_meta 包含了所有必要的字段
                # 实际上，对于 md_doc，它自己的 metadata 就是最准确的标题上下文
                # 我们主要需要 current_headers 来服务于后续可能出现的表格或无标题文本
                
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
                    
                    if content_type == "code":
                        language = seg.get('language', '')
                        separators = get_separators_for_language(language)
                        print(f"DEBUG: Splitting code. Language: {language}, Size: {chunk_size}, Separators: {separators[:2]}")
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            separators=separators,
                            is_separator_regex=True
                        )
                    else:
                        # 统一使用 RecursiveCharacterTextSplitter
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
    parser.add_argument("--input_file", type=str, default="data/output/parsed.jsonl", help="Path to input JSONL file")
    parser.add_argument("--output_file", type=str, default="data/output/chunks.jsonl", help="Path to output JSONL file")
    
    args = parser.parse_args()
    
    chunk_documents(args.input_file, args.output_file)
