# 生产级数据管道与高级RAG

## 1. 项目功能与整体流程

本项目实现了一个端到端的 RAG（检索增强生成）数据处理流水线，旨在将非结构化文档（PDF, Markdown, DOCX，HTML）转化为高质量的向量数据并存储于 Milvus 向量数据库中。

**核心流程：**
1.  **智能解析 (`intelligent_parser.py`)**：
    *   支持多格式解析：利用 `PyMuPDF` 解析 PDF 并提取表格，利用 `python-docx` 处理 Word 文档，利用 `unstructured` 处理 HTML 文档。
    *   统一输出格式：将所有文档统一为 JSONL 格式，保留源文件路径、页码（PDF）、是否为表格等元数据。
2.  **高级分块 (`advanced_chunker.py`)**：
    *   **内容类型感知**：自动识别代码块、表格和普通文本。
    *   **动态 Chunk Size**：根据信息密度（如列表密度）动态调整分块大小（300 vs 800）。
    *   **结构化分块**：利用 Markdown 标题层级保持语义连贯性。
3.  **向量化处理 (`embedding_client.py`)**：
    *   使用高性能嵌入模型进行文本向量化。
    *   支持 **MRL (Matryoshka Representation Learning)** 技术，灵活截断向量维度以平衡精度与存储成本。
4.  **向量存储 (`import_to_milvus.py`)**：
    *   自动化创建 Milvus Collection 和 HNSW 索引。
    *   支持大规模向量数据的批量导入与验证。

## 2. 环境依赖与安装

### 前置条件
- Python 3.8+
- Docker & Docker Compose (用于运行 Milvus)

### 安装步骤

1. **克隆代码库**
   ```bash
   git clone https://github.com/MYF2002/Production-grade-data-pipeline-and-advanced-RAG.git
   cd Production-grade-data-pipeline-and-advanced-RAG
   ```

2. **安装项目依赖**
   本项目使用 `pyproject.toml` 管理依赖。请运行以下命令安装：
   ```bash
   # 安装运行依赖
   pip install .
   ```
   *(注：建议使用虚拟环境)*

3. **启动 Milvus 服务**
   确保已安装 Docker 和 Docker Compose，然后运行：
   ```bash
   docker-compose up -d
   ```

## 3. 运行流水线

以下命令展示了从原始数据到向量入库的完整过程：

### 第一步：智能解析
将 `data/input` 目录下的文档解析为统一的 JSONL 格式。
```bash
python Scripts/intelligent_parser.py --input_dir data/input --output_file data/output/contents.jsonl
```

### 第二步：高级分块
对解析后的内容进行智能分块，应用动态 Chunk Size 策略。
```bash
python Scripts/advanced_chunker.py --input_file data/output/contents.jsonl --output_file data/output/chunks.jsonl
```

### 第三步：向量化
使用嵌入模型将文本转换为向量。此处使用 MRL 技术将向量截断为 768 维。
```bash
python Scripts/embedding_client.py --input data/output/chunks.jsonl --output data/output/vectorized.jsonl --truncate_dim 768
```

### 第四步：数据入库
将向量数据导入 Milvus 数据库并创建索引。
```bash
python Scripts/import_to_milvus.py --input data/output/vectorized.jsonl --collection rag_collection --dim 768
```

## 4. 嵌入模型选择与理由

**模型选择**：`fangxq/XYZ-embedding` （768维）

**选择理由**：
1.  **C-MTEB 榜单表现**：该模型在 C-MTEB 中的检索（Retrieval）分数为77.24，排名第十，榜单显示维度为768维。
2.  **MRL 技术支持**：原始维度可能高达 1792 维，但可以截断为768维，以减少存储成本。

