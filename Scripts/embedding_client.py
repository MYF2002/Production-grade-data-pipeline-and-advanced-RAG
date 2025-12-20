import argparse
import json
import numpy as np
import torch
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from tqdm import tqdm

class EmbeddingClient:
    def __init__(self, model_name: str = "fangxq/XYZ-embedding", device: str = "cpu", truncate_dim: Optional[int] = None):
        """嵌入客户端模型"""
        #使用GPU
        if torch.cuda.is_available():
            device = "cuda:0"
        
        print(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name, device=device)
        self.truncate_dim = truncate_dim
        
    def encode(self, texts: List[str], batch_size: int = 32, normalize_embeddings: bool = True) -> np.ndarray:
        """
        批量编码文本
        """
        # 如果设置了截断维度，我们需要特殊处理：
        # 1. encode(normalize_embeddings=False)
        # 2. 截断到 truncate_dim 维
        # 3. 再次 normalize
        
        if self.truncate_dim is not None:
             # 获取原始向量
            embeddings = self.model.encode(
                texts, 
                batch_size=batch_size, 
                show_progress_bar=True, 
                normalize_embeddings=False #先不进行归一化，后续截断后进行
            )
            # 截断到指定维度
            embeddings = embeddings[:, :self.truncate_dim]
            # 归一化
            if normalize_embeddings:
                embeddings = normalize(embeddings)
            return embeddings
        else:
            # 普通模型直接调用
            return self.model.encode(
                texts, 
                batch_size=batch_size, 
                show_progress_bar=True, 
                normalize_embeddings=normalize_embeddings
            )

    def encode_single(self, text: str) -> np.ndarray:
        """
        编码单个文本
        """
        return self.encode([text])[0]

def process_file(input_path: str, output_path: str, model_name: str, batch_size: int = 32, truncate_dim: Optional[int] = None):
    client = EmbeddingClient(model_name=model_name, truncate_dim=truncate_dim)
    
    # 读取所有数据
    data_list = []
    texts = []
    print(f"Reading from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            data_list.append(item)
            texts.append(item['text'])
            
    if not texts:
        print("No data found.")
        return

    # 批量生成向量
    print(f"Encoding {len(texts)} documents...")
    embeddings = client.encode(texts, batch_size=batch_size)
    
    # 写入结果
    print(f"Writing to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        for item, vector in zip(data_list, embeddings):
            # 将 numpy array 转换为 list 以便序列化
            item['vector'] = vector.tolist()
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embedding Client")
    parser.add_argument("--input", type=str, default=r"data/output/chunks.jsonl", help="Path to input JSONL file")
    parser.add_argument("--output", type=str, default=r"data/output/vectorized.jsonl", help="Path to output JSONL file")
    parser.add_argument("--model", type=str, default="fangxq/XYZ-embedding", help="Model name")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for encoding")
    parser.add_argument("--truncate_dim", type=int, default=None, help="Dimension to truncate embeddings to")
    
    args = parser.parse_args()
    
    process_file(args.input, args.output, args.model, args.batch_size, args.truncate_dim)
