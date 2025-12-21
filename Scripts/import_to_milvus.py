import json
import argparse
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

def connect_milvus(host="localhost", port="19530"):
    print(f"Connecting to Milvus at {host}:{port}...")
    connections.connect("default", host=host, port=port)
    print("Connected.")

def create_collection(collection_name, dim):
    if utility.has_collection(collection_name):
        print(f"Collection {collection_name} already exists. Dropping it...")
        utility.drop_collection(collection_name)

    print(f"Creating collection {collection_name} with dim={dim}...")
    
    # 1. 定义Schema
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535), # 使用较大的长度以适应长文本
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="page", dtype=DataType.INT64), # 存储页码信息
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50) # 存储内容类型
    ]
    
    schema = CollectionSchema(fields, description="RAG Documents Collection")
    
    # 2. 创建Collection
    collection = Collection(collection_name, schema)
    print(f"Collection {collection_name} created.")
    
    # 3. 创建索引
    print("Creating HNSW index...")
    index_params = {
        "metric_type": "IP", # 内积相似度，通常用于归一化后的向量 (相当于Cosine)
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 256}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    print("Index created.")
    return collection

def import_data(collection, input_file):
    print(f"Reading data from {input_file}...")
    
    # 准备数据
    texts = []
    vectors = []
    sources = []
    pages = []
    content_types = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            
            # 提取字段
            text = item.get('text', '')
            vector = item.get('vector', [])
            meta = item.get('metadata', {})
            source = meta.get('source', '')
            page = meta.get('page', -1) # -1 表示未知
            content_type = meta.get('content_type', 'text')
            
            # 简单验证
            if not vector:
                print("Skipping item with empty vector.")
                continue
                
            texts.append(text)
            vectors.append(vector)
            sources.append(str(source))
            pages.append(int(page) if page is not None else -1)
            content_types.append(str(content_type))
            
    if not texts:
        print("No data to import.")
        return

    # 插入数据
    # Schema: id, text, vector, source, page, content_type
    # Insert: [texts, vectors, sources, pages, content_types]
    
    print(f"Inserting {len(texts)} entities...")
    entities = [
        texts,
        vectors,
        sources,
        pages,
        content_types
    ]
    
    collection.insert(entities)
    collection.flush()
    print(f"Inserted {collection.num_entities} entities.")


#模拟查询向量，测试查询结果
def search_test(collection, dim):
    print("Running search test...")
    collection.load()
    
    # 生成一个随机向量或使用全0向量进行测试 (这里简单模拟一个查询)
    # 在实际场景中，应该使用 EmbeddingClient 生成查询向量
    import random
    query_vector = [random.random() for _ in range(dim)]
    
    search_params = {
        "metric_type": "IP",
        "params": {"ef": 64}
    }
    
    results = collection.search(
        data=[query_vector],
        anns_field="vector",
        param=search_params,
        limit=3,
        output_fields=["text", "source", "content_type"]
    )
    
    print(f"Found {len(results[0])} results:")
    for hit in results[0]:
        print(f"Score: {hit.score:.4f}, Type: {hit.entity.get('content_type')}, Source: {hit.entity.get('source')}")
        # print(f"Text: {hit.entity.get('text')[:50]}...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import data to Milvus")
    parser.add_argument("--input", type=str, default="data/output/vectorized.jsonl")
    parser.add_argument("--collection", type=str, default="rag_collection")
    parser.add_argument("--dim", type=int, default=768)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=str, default="19530")
    
    args = parser.parse_args()
    
    try:
        connect_milvus(args.host, args.port)
        collection = create_collection(args.collection, args.dim)
        import_data(collection, args.input)
        #search_test(collection, args.dim)
    except Exception as e:
        print(f"Error: {e}")
