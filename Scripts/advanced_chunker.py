import json
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_documents(input_file, output_file):
    # 1. 定义分块器
    # Markdown分块配置
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # 分块配置
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks_data = []
    
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            source = doc['source']
            content = doc['content']
            file_type = doc['file_type']

            # 2. 初次分块 (Markdown)
            # 只有 md, pdf(已转md格式), docx(已转md格式) 适用 MarkdownHeaderTextSplitter
            # 如果内容不是 markdown 格式，可能需要直接用 RecursiveCharacterTextSplitter
            
            md_docs = md_splitter.split_text(content)
            
            # 3. 二次分块 (Length Control)
            # split_documents 会保留并合并 metadata
            final_docs = text_splitter.split_documents(md_docs)
            
            # 4. 元数据富集
            for idx, chunk in enumerate(final_docs):
                # 合并 Markdown 分块的 metadata
                chunk_meta = chunk.metadata.copy()
                chunk_meta['source'] = source
                chunk_meta['chunk_index'] = idx
                chunk_meta['file_type'] = file_type
                
                chunks_data.append({
                    "text": chunk.page_content,
                    "metadata": chunk_meta
                })

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks_data:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    print(f"分块完成，共生成 {len(chunks_data)} 个分块。结果已保存至 {output_file}")

if __name__ == "__main__":
    input_path = r"data/output/parsed.jsonl" 
    output_path = r"data/output/chunks.jsonl"
    chunk_documents(input_path, output_path)
