# app.py
# -*- coding: utf-8 -*-
"""
整合版：Flask API + 核心逻辑
- 抓取网页、解析正文
- PostgreSQL: pages/chunks 表及 pg_trgm 扩展
- 切块（CHUNK_SIZE/CHUNK_OVERLAP）
- 调用外部 Embedding API 向量化
- Qdrant 写入/检索
- REST API: ingest / bulk_ingest / search / page
"""

import os
import re
import json
import hashlib
import requests
import trafilatura
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

# -----------------------
# 配置
# -----------------------
CONFIG = {
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/websearch",
    "EMBEDDING_API_BASE": "http://120.79.25.184:7202",
    "EMBEDDING_API_PATH": "/Qwen3-Embedding-4B",
    "EMB_POOLING": "last",
    "EMB_NORMALIZE": True,
    "QDRANT_URL": "http://127.0.0.1:6333",
    "QDRANT_API_KEY": None,
    "QDRANT_COLLECTION": "web_chunks",
    "CHUNK_SIZE": 800,
    "CHUNK_OVERLAP": 200,
    "HTTP_TIMEOUT": 15,
    "HTTP_UA": "Mozilla/5.0 (compatible; mini-websearch/0.1)",
}

DATABASE_URL = CONFIG["DATABASE_URL"]
EMBEDDING_API_BASE = CONFIG["EMBEDDING_API_BASE"].rstrip("/")
EMBEDDING_API_PATH = CONFIG["EMBEDDING_API_PATH"]
EMB_POOLING = CONFIG["EMB_POOLING"]
EMB_NORMALIZE = CONFIG["EMB_NORMALIZE"]
EMB_DIM: Optional[int] = None

QDRANT_URL = CONFIG["QDRANT_URL"]
QDRANT_COLLECTION = CONFIG["QDRANT_COLLECTION"]
CHUNK_SIZE = CONFIG["CHUNK_SIZE"]
CHUNK_OVERLAP = CONFIG["CHUNK_OVERLAP"]
HTTP_TIMEOUT = CONFIG["HTTP_TIMEOUT"]
UA = CONFIG["HTTP_UA"]

# -----------------------
# 数据库
# -----------------------
def get_conn():
    return psycopg2.connect(DATABASE_URL)

def ensure_pg_schema():
    sqls = [
        "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
        """
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            site TEXT,
            title TEXT,
            published_at TIMESTAMP NULL,
            fetched_at TIMESTAMP NOT NULL,
            lang TEXT,
            html TEXT,
            content TEXT,
            checksum TEXT
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_pages_fetched_at ON pages(fetched_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_pages_published_at ON pages(published_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_pages_title_trgm ON pages USING gin (title gin_trgm_ops);",
        "CREATE INDEX IF NOT EXISTS idx_pages_content_trgm ON pages USING gin (content gin_trgm_ops);",
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id BIGINT PRIMARY KEY,
            page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
            chunk_index INTEGER,
            content TEXT,
            checksum TEXT
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_chunks_page_id ON chunks(page_id);",
        "CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm ON chunks USING gin (content gin_trgm_ops);",
    ]
    with get_conn() as conn, conn.cursor() as cur:
        for s in sqls:
            cur.execute(s)
        conn.commit()

# -----------------------
# Qdrant
# -----------------------
_qdrant_client: Optional[QdrantClient] = None
def get_qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=None, prefer_grpc=False,
                                      timeout=30, check_compatibility=False)
    return _qdrant_client

def ensure_qdrant_collection(dim: int):
    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        info = r.json()
        current_dim = info["result"]["config"]["params"]["vectors"]["size"]
        if current_dim != dim:
            requests.delete(url, timeout=10)
            payload = {"vectors": {"size": dim, "distance": "Cosine"}}
            requests.put(url, headers={"Content-Type": "application/json"},
                         data=json.dumps(payload), timeout=15)
        return info
    elif r.status_code == 404:
        payload = {"vectors": {"size": dim, "distance": "Cosine"}}
        requests.put(url, headers={"Content-Type": "application/json"},
                     data=json.dumps(payload), timeout=15)
    else:
        raise RuntimeError(f"访问 Qdrant 出错: {r.status_code}, {r.text}")

# -----------------------
# Embedding
# -----------------------
def _embed_api_url() -> str:
    return f"{EMBEDDING_API_BASE}{EMBEDDING_API_PATH}"

def embed_batch(texts: List[str], pooling=None, normalize=None, dim=None,
                instruction=None, prefix=None) -> Dict[str, Any]:
    url = _embed_api_url()
    payload = {"texts": [str(t or "").strip() for t in texts]}
    if pooling is not None:   payload["pooling"] = pooling
    if normalize is not None: payload["normalize"] = bool(normalize)
    if dim is not None:       payload["dim"] = int(dim)
    if instruction:           payload["instruction"] = instruction
    if prefix:                payload["prefix"] = prefix
    r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data

def probe_embedding_dim() -> int:
    global EMB_DIM
    if EMB_DIM:
        return EMB_DIM
    data = embed_batch(["__dim_probe__"], pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    EMB_DIM = int(data.get("dim") or len(data["vectors"][0]))
    return EMB_DIM

# -----------------------
# 抓取 & 解析
# -----------------------
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text

def clean_extract(url: str, html: str) -> Dict[str, Any]:
    text = trafilatura.extract(html) or ""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
    site = urlparse(url).netloc
    lang = soup.html.get("lang").lower() if soup and soup.html and soup.html.get("lang") else None
    return {
        "title": title[:512],
        "content": re.sub(r"\s+", " ", text).strip(),
        "published_at": None,
        "site": site,
        "lang": lang
    }

def checksum_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if not t:
        return []
    chunks, start, n = [], 0, len(t)
    while start < n:
        end = min(n, start + size)
        chunks.append(t[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

# -----------------------
# 入库
# -----------------------
def upsert_page(url: str, html: str, parsed: Dict[str, Any]) -> int:
    now = datetime.utcnow()
    content = parsed["content"] or ""
    chksum = checksum_text(content or html)
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, checksum FROM pages WHERE url=%s", (url,))
        row = cur.fetchone()
        if row:
            if row["checksum"] == chksum:
                return row["id"]
            else:
                cur.execute("DELETE FROM chunks WHERE page_id=%s", (row["id"],))
                cur.execute("""UPDATE pages SET title=%s, content=%s, checksum=%s, fetched_at=%s WHERE id=%s""",
                            (parsed["title"], content, chksum, now, row["id"]))
                conn.commit()
                return row["id"]
        else:
            cur.execute("""INSERT INTO pages (url, site, title, published_at, fetched_at, lang, html, content, checksum)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (url, parsed["site"], parsed["title"], parsed["published_at"], now,
                         parsed["lang"], html, content, chksum))
            pid = cur.fetchone()["id"]
            conn.commit()
            return pid

def upsert_chunks_and_vectors(page_id: int, url: str, title: str, published_at, content: str) -> int:
    blocks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
    if not blocks:
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        chunk_ids = []
        for idx, block in enumerate(blocks):
            cid = page_id * 1000000 + idx
            cur.execute("""INSERT INTO chunks (id, page_id, chunk_index, content)
                           VALUES (%s,%s,%s,%s)
                           ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content""",
                        (cid, page_id, idx, block))
            chunk_ids.append(cid)
        conn.commit()
    dim = probe_embedding_dim()
    data = embed_batch(blocks, pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    vectors = data["vectors"]
    ensure_qdrant_collection(dim)
    client = get_qdrant()
    points = [PointStruct(id=cid, vector=vec, payload={"page_id": page_id, "url": url, "title": title})
              for cid, vec in zip(chunk_ids, vectors)]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)

def ingest_url(url: str) -> Dict[str, Any]:
    html = fetch_html(url)
    parsed = clean_extract(url, html)
    pid = upsert_page(url, html, parsed)
    n_chunks = 0
    if parsed["content"]:
        n_chunks = upsert_chunks_and_vectors(pid, url, parsed["title"], parsed["published_at"], parsed["content"])
    return {"url": url, "page_id": pid, "title": parsed["title"], "chunks": n_chunks}

def ingest_urls(urls: List[str]) -> List[Dict[str, Any]]:
    return [ingest_url(u) for u in urls]

# -----------------------
# API 层
# -----------------------
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "websearch-api"})

@app.route("/ingest", methods=["POST"])
def api_ingest():
    data = request.get_json(force=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400
    return jsonify(ingest_url(url))

@app.route("/bulk_ingest", methods=["POST"])
def api_bulk_ingest():
    data = request.get_json(force=True) or {}
    urls = data.get("urls") or []
    if not urls:
        return jsonify({"error": "missing urls"}), 400
    return jsonify(ingest_urls(urls))

# -----------------------
# 初始化 & 入口
# -----------------------
def initialize():
    ensure_pg_schema()
    dim = probe_embedding_dim()
    ensure_qdrant_collection(dim)

if __name__ == "__main__":
    initialize()
    app.run(host="0.0.0.0", port=5080, debug=True)
