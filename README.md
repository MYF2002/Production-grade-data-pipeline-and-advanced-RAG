# 第四周课程作业：生产级数据管道与高级RAG（第一部分）

> **提交方式**：GitHub仓库链接

> **作业目标**：构建一个完整的文档处理流水线，能够解析多种格式的文档、进行结构化分块、生成向量嵌入，并部署本地向量数据库

---

## 作业概述

本次作业分为两个部分：

| 部分 | 类型 | 分值占比 | 说明 |
|------|------|----------|------|
| Part A | 基础要求（必做） | 80分 | 完成核心功能，所有学生必须完成 |
| Part B | 进阶挑战（选做） | 20分 | 额外加分项，鼓励深入探索 |

**总分计算**：最高100分，Part B为加分项，总分不超过100分。

---

## Part A：基础要求（必做，80分）

### A1. 项目仓库初始化（5分）

创建一个公开的GitHub仓库，包含以下基本结构：

```
your-repo/
├── scripts/
│   ├── intelligent_parser.py
│   ├── advanced_chunker.py
│   └── embedding_client.py
├── data/
│   ├── input/              # 测试用的原始文档
│   └── output/             # 处理后的输出文件
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```

**要求**：
- 仓库必须公开（Public）
- 包含合理的 `.gitignore` 文件（忽略 `__pycache__`、`.env`、大型模型文件等）
- `README.md` 包含项目简介、环境配置和运行说明
- `data/input/` 目录包含至少3个测试文件（1个PDF、1个Word、1个TXT或Markdown）

---

### A2. 智能文档解析器（25分）

在 `/scripts` 目录下完成 `intelligent_parser.py`：

**功能要求**：

1. **文件类型路由**（5分）
- 根据文件后缀名自动选择对应的解析器
- 支持 `.pdf`、`.docx`、`.txt`、`.md`、`.html` 格式
- 遇到不支持的格式时输出警告并跳过

2. **PDF解析**（8分）
- 使用 PyMuPDF 提取文本内容
- 使用 `page.find_tables()` 提取表格，转换为Markdown格式
- 保留页码信息

3. **Word解析**（7分）
- 使用 python-docx 提取段落内容
- 读取段落样式（Heading 1、Heading 2等），转换为Markdown标题格式
- 正确处理空段落

4. **统一输出格式**（5分）
- 输出为JSONL格式，每行一个JSON对象
- 每个对象包含：`source`（文件路径）、`content`（提取的文本）、`file_type`（文件类型）

**示例输出**：
```json
{"source": "data/input/report.pdf", "content": "# 第一章 概述\n\n本文档介绍...", "file_type": "pdf"}
{"source": "data/input/manual.docx", "content": "# 用户手册\n\n## 1.1 安装说明...", "file_type": "docx"}
```

**命令行接口**：
```bash
python scripts/intelligent_parser.py --input data/input --output data/output/parsed.jsonl
```

---

### A3. 链式分块器（20分）

在 `/scripts` 目录下完成 `advanced_chunker.py`：

**功能要求**：

1. **结构化分块**（8分）
- 使用 `MarkdownHeaderTextSplitter` 按标题层级分块
- 配置识别 `#`、`##`、`###` 三级标题
- 将标题信息注入每个chunk的metadata

2. **长度控制分块**（7分）
- 使用 `RecursiveCharacterTextSplitter` 进行二次分块
- 配置 `chunk_size=500`、`chunk_overlap=50`
- 使用 `split_documents()` 保留metadata

3. **元数据富集**（5分）
- 为每个chunk添加 `source`（来源文件）、`chunk_index`（块序号）
- 保留第一步注入的标题层级信息（h1、h2、h3）

**示例输出**：
```json
{"text": "本系统采用微服务架构...", "metadata": {"h1": "第一章 系统概述", "h2": "1.2 技术架构", "source": "manual.docx", "chunk_index": 5}}
```

**命令行接口**：
```bash
python scripts/advanced_chunker.py --input data/output/parsed.jsonl --output data/output/chunked.jsonl
```

---

### A4. 嵌入模型客户端（15分）

在 `/scripts` 目录下完成 `embedding_client.py`：

**功能要求**：

1. **EmbeddingClient类实现**（8分）
- 使用 sentence-transformers 加载模型
- 选择 C-MTEB Retrieval 任务排名前列的中文模型（如 `BAAI/bge-small-zh-v1.5` 或其他）
- 实现 `encode(texts: List[str]) -> np.ndarray` 方法，支持批量编码
- 实现 `encode_single(text: str) -> np.ndarray` 方法

2. **向量化处理**（7分）
- 读取 chunked.jsonl，提取所有文本
- 批量生成向量嵌入（建议 batch_size=32）
- 输出包含 `text`、`metadata`、`vector` 的JSONL文件

**示例输出**：
```json
{"text": "本系统采用微服务架构...", "metadata": {"h1": "...", "source": "..."}, "vector": [0.12, -0.34, 0.56, ...]}
```

**命令行接口**：
```bash
python scripts/embedding_client.py --input data/output/chunked.jsonl --output data/output/vectorized.jsonl
```

---

### A5. Milvus本地部署（10分）

**要求**：

1. **docker-compose.yml配置**（5分）
- 从Milvus官方获取standalone模式的配置文件
- 包含 `milvus-standalone`、`etcd`、`minio` 三个服务
- 配置正确的端口映射（Milvus: 19530）

2. **部署验证**（5分）
- 执行 `docker compose up -d` 能成功启动所有服务
- 提供部署成功的截图（显示三个容器状态为running）
- 截图保存为 `data/output/milvus_deployment.png`

---

### A6. 流水线文档（5分）

编写 `README.md` 文件：

**要求**：
- 说明项目功能和整体流程
- 列出环境依赖和安装步骤
- 提供完整的运行命令示例（从原始文档到最终向量化数据）
- 说明选择的嵌入模型及选择理由（参考C-MTEB榜单）

---

## Part B：进阶挑战（选做，20分）

以下任务为选做加分项，完成任意一项或多项均可获得对应分数。

---

### B1. PDF表格高级处理（6分）

增强PDF表格的处理能力：

**要求**：

1. **表格检测与提取**（3分）
- 对于包含多个表格的PDF页面，能够分别提取每个表格
- 将表格转换为Pandas DataFrame，再转为Markdown表格格式

2. **表格元数据**（3分）
- 在输出中标注表格所在的页码
- 为表格内容添加特殊标记（如 `[TABLE]` 前缀），便于后续处理时识别

**示例输出**：
```json
{"source": "report.pdf", "content": "[TABLE] Page 3\n| 年份 | 营收 |\n|------|------|\n| 2023 | 1.2亿 |", "file_type": "pdf", "is_table": true, "page": 3}
```

---

### B2. 自适应分块策略（6分）

根据内容特点动态调整分块参数：

**要求**：

1. **内容类型识别**（3分）
- 识别文本是"表格"、"代码块"还是"普通文本"
- 不同类型使用不同的分块策略（如表格不切分，代码块按函数切分）

2. **动态chunk_size**（3分）
- 对于信息密度高的内容（如表格、列表），使用较小的chunk_size
- 对于叙述性文本，使用较大的chunk_size
- 在metadata中记录使用的chunk_size

---

### B3. 嵌入模型对比实验（4分）

对比不同嵌入模型的效果：

**要求**：

1. **多模型测试**（2分）
- 选择至少2个不同的嵌入模型
- 使用相同的测试数据生成向量

2. **对比报告**（2分）
- 记录每个模型的维度、编码速度（条/秒）、模型大小
- 编写简短的对比报告（放在 `data/output/model_comparison.md`）

---

### B4. 数据导入Milvus（4分）

将向量数据导入Milvus数据库：

**要求**：

1. **创建Collection**（2分）
- 使用pymilvus创建Collection
- 定义正确的Schema（包含id、text、vector字段）
- 配置HNSW索引

2. **数据导入与验证**（2分）
- 将 vectorized.jsonl 中的数据导入Milvus
- 执行一次简单的向量搜索验证导入成功
- 提供导入脚本 `scripts/import_to_milvus.py`

---

## 提交要求

### 提交内容

1. **GitHub仓库链接**（必须）
   - 仓库必须公开
   - 提交前确保所有脚本能正常运行

2. **提交说明**（推荐）
   - 在提交时注明完成了哪些 Part B 的进阶任务

### 提交检查清单

提交前请自行检查以下内容：

**Part A 检查项**：
- [ ] 仓库结构完整（scripts/、data/、docker-compose.yml等）
- [ ] `data/input/` 包含至少3个测试文件（PDF、Word、TXT/MD）
- [ ] `intelligent_parser.py` 能正确解析三种格式的文件
- [ ] `advanced_chunker.py` 输出的chunk包含标题层级metadata
- [ ] `embedding_client.py` 能批量生成向量
- [ ] `docker compose up -d` 能成功启动Milvus
- [ ] 包含Milvus部署成功的截图
- [ ] README.md 包含完整的运行说明和模型选择理由

**Part B 检查项**（如适用）：
- [ ] B1：PDF表格能正确提取并转换为Markdown格式
- [ ] B2：不同类型内容使用不同分块策略
- [ ] B3：model_comparison.md 包含对比数据
- [ ] B4：数据成功导入Milvus并能执行搜索

---

## 参考资源

- PyMuPDF文档：https://pymupdf.readthedocs.io
- python-docx文档：https://python-docx.readthedocs.io
- unstructured文档：https://docs.unstructured.io
- LangChain TextSplitters：https://python.langchain.com/docs/modules/data_connection/document_transformers
- sentence-transformers文档：https://www.sbert.net
- C-MTEB排行榜：https://huggingface.co/spaces/mteb/leaderboard
- Milvus文档：https://milvus.io/docs
- pymilvus文档：https://pymilvus.readthedocs.io

---
