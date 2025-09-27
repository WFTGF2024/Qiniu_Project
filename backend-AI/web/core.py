# core.py
# -*- coding: utf-8 -*-
"""
核心逻辑：
- 抓取网页、解析正文
- PostgreSQL: pages/chunks 表及 pg_trgm 扩展
- 切块（CHUNK_SIZE/CHUNK_OVERLAP）
- 通过外部 Embedding API (:7202) 批量向量化
- Qdrant 写入/检索
- 关键词检索（Postgres）/ 语义检索（Qdrant）/ 混合检索
"""

import os
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
import trafilatura
import psycopg2
from psycopg2.extras import RealDictCursor

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse
# -----------------------
# 环境变量
# -----------------------

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
CONFIG = {
    # PostgreSQL
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/websearch",

    # Embedding 服务
    "EMBEDDING_API_BASE": "http://localhost:7202",
    "EMBEDDING_API_PATH": "/Qwen3-Embedding-4B",
    "EMB_POOLING": "last",
    "EMB_NORMALIZE": True,

    # Qdrant
    "QDRANT_URL": "http://127.0.0.1:6333",
    "QDRANT_API_KEY": None,      # 明确禁用
    "QDRANT_COLLECTION": "web_chunks",

    # 切块参数
    "CHUNK_SIZE": 800,
    "CHUNK_OVERLAP": 200,

    # 抓取
    "HTTP_TIMEOUT": 15,
    "HTTP_UA": "Mozilla/5.0 (compatible; mini-websearch/0.1)",
}
DATABASE_URL = CONFIG["DATABASE_URL"]
EMBEDDING_API_BASE = CONFIG["EMBEDDING_API_BASE"].rstrip("/")
EMBEDDING_API_PATH = CONFIG["EMBEDDING_API_PATH"]
EMB_POOLING = CONFIG["EMB_POOLING"]
EMB_NORMALIZE = CONFIG["EMB_NORMALIZE"]
EMB_DIM: Optional[int] = None  # 全局变量

QDRANT_URL = CONFIG["QDRANT_URL"]
QDRANT_API_KEY = CONFIG["QDRANT_API_KEY"]
QDRANT_COLLECTION = CONFIG["QDRANT_COLLECTION"]

CHUNK_SIZE = CONFIG["CHUNK_SIZE"]
CHUNK_OVERLAP = CONFIG["CHUNK_OVERLAP"]

HTTP_TIMEOUT = CONFIG["HTTP_TIMEOUT"]
UA = CONFIG["HTTP_UA"]

# -----------------------
# 数据库工具
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
        _qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=None,
            prefer_grpc=False,
            timeout=30,
            check_compatibility=False   # 关掉兼容性检查，避免 warning / 502
        )
    return _qdrant_client


def ensure_qdrant_collection(dim: int):
    client = get_qdrant()
    try:
        info = client.get_collection(QDRANT_COLLECTION)
        # 如果能取到，直接返回
        return info
    except UnexpectedResponse as e:
        # 404 才说明 collection 不存在
        if getattr(e, "status_code", None) == 404:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            return
        # 其它情况：打印更详细的提示，再抛出
        raise RuntimeError(
            f"无法获取 Qdrant collection {QDRANT_COLLECTION}，状态码 {getattr(e, 'status_code', '?')}。"
            " 请确认 Qdrant 服务正常运行，URL 配置正确（建议 http://127.0.0.1:6333）。"
        )

# -----------------------
# Embedding API
# -----------------------
def _embed_api_url() -> str:
    return f"{EMBEDDING_API_BASE}{EMBEDDING_API_PATH}"

def embed_batch(texts: List[str],
                pooling: Optional[str] = None,
                normalize: Optional[bool] = None,
                dim: Optional[int] = None,
                instruction: Optional[str] = None,
                prefix: Optional[str] = None) -> Dict[str, Any]:
    """
    调用你的 Embedding POST 批量接口
    返回: {"vectors": [[...], ...], "dim": D, ...}
    """
    url = _embed_api_url()
    payload: Dict[str, Any] = {"texts": [str(t or "").strip() for t in texts]}
    if pooling is not None:   payload["pooling"] = pooling
    if normalize is not None: payload["normalize"] = bool(normalize)
    if dim is not None:       payload["dim"] = int(dim)
    if instruction:           payload["instruction"] = instruction
    if prefix:                payload["prefix"] = prefix

    r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if "vectors" not in data:
        raise RuntimeError(f"Embedding API 返回异常：{data}")
    return data

def probe_embedding_dim() -> int:
    global EMB_DIM
    if EMB_DIM:
        return EMB_DIM
    data = embed_batch(["__dim_probe__"], pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    dim = int(data.get("dim") or len(data["vectors"][0]))
    EMB_DIM = dim
    return dim

# -----------------------
# 抓取 & 解析
# -----------------------
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text

META_DATE_KEYS = [
    ("meta", {"property": "article:published_time"}),
    ("meta", {"name": "pubdate"}),
    ("meta", {"name": "publishdate"}),
    ("meta", {"name": "timestamp"}),
    ("meta", {"itemprop": "datePublished"}),
]

def guess_published_at(soup: BeautifulSoup) -> Optional[datetime]:
    for tag, attrs in META_DATE_KEYS:
        el = soup.find(tag, attrs=attrs)
        if el:
            raw = el.get("content") or el.get("value")
            if raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    pass
    # 兜底：从全文匹配日期
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"(\d{4}-\d{2}-\d{2})([ T]\d{2}:\d{2}(:\d{2})?)?", txt)
    if m:
        try:
            return datetime.fromisoformat(m.group(0).replace(" ", "T")).replace(tzinfo=None)
        except Exception:
            return None
    return None

def clean_extract(url: str, html: str) -> Dict[str, Any]:
    text = trafilatura.extract(html) or ""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
    published = guess_published_at(soup)
    site = urlparse(url).netloc
    lang = soup.html.get("lang").lower() if soup and soup.html and soup.html.get("lang") else None
    return {
        "title": title[:512],
        "content": (re.sub(r"\s+", " ", text).strip() if text else ""),
        "published_at": published,
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
# 入库 & 向量化
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
                cur.execute("UPDATE pages SET fetched_at=%s, title=%s WHERE id=%s", (now, parsed["title"], row["id"]))
                conn.commit()
                return row["id"]
            else:
                cur.execute("""
                    UPDATE pages SET
                      site=%s, title=%s, published_at=%s, fetched_at=%s,
                      lang=%s, html=%s, content=%s, checksum=%s
                    WHERE id=%s
                """, (parsed["site"], parsed["title"], parsed["published_at"], now,
                      parsed["lang"], html, content, chksum, row["id"]))
                # 旧 chunk 删除，重新切块
                cur.execute("DELETE FROM chunks WHERE page_id=%s", (row["id"],))
                conn.commit()
                return row["id"]
        else:
            cur.execute("""
                INSERT INTO pages (url, site, title, published_at, fetched_at, lang, html, content, checksum)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (url, parsed["site"], parsed["title"], parsed["published_at"], now,
                  parsed["lang"], html, content, chksum))
            pid = cur.fetchone()["id"]
            conn.commit()
            return pid

def upsert_chunks_and_vectors(page_id: int, url: str, title: str, published_at: Optional[datetime], content: str) -> int:
    blocks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
    if not blocks:
        return 0

    # 写 chunks 文本
    with get_conn() as conn, conn.cursor() as cur:
        chunk_ids = []
        for idx, block in enumerate(blocks):
            cid = page_id * 1000000 + idx
            cur.execute("""
                INSERT INTO chunks (id, page_id, chunk_index, content)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content
            """, (cid, page_id, idx, block))
            chunk_ids.append(cid)
        conn.commit()

    # 调 Embedding 批量向量化
    dim = probe_embedding_dim()
    data = embed_batch(blocks, pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    vectors = data["vectors"]
    if not vectors or len(vectors) != len(blocks):
        raise RuntimeError("Embedding 返回数量与切块数量不一致")

    # 写入 Qdrant
    ensure_qdrant_collection(dim)
    client = get_qdrant()
    points = []
    for cid, vec, idx in zip(chunk_ids, vectors, range(len(blocks))):
        points.append(PointStruct(
            id=cid,
            vector=vec,
            payload={
                "page_id": page_id,
                "url": url,
                "title": title,
                "chunk_index": idx,
                "published_at": (published_at.isoformat() if published_at else None),
            }
        ))
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)

def ingest_url(url: str) -> Dict[str, Any]:
    html = fetch_html(url)
    parsed = clean_extract(url, html)
    pid = upsert_page(url, html, parsed)
    n_chunks = 0
    if parsed["content"]:
        n_chunks = upsert_chunks_and_vectors(pid, url, parsed["title"], parsed["published_at"], parsed["content"])
    return {
        "url": url,
        "page_id": pid,
        "title": parsed["title"],
        "published_at": parsed["published_at"].isoformat() if parsed["published_at"] else None,
        "chunks": n_chunks
    }

def ingest_urls(urls: List[str]) -> List[Dict[str, Any]]:
    out = []
    for u in urls:
        try:
            out.append({"ok": True, **ingest_url(u)})
        except Exception as e:
            out.append({"ok": False, "url": u, "error": str(e)})
    return out

# -----------------------
# 检索
# -----------------------
def _snippet(text: str, q: str, width: int = 180) -> str:
    if not text:
        return ""
    pos = text.lower().find(q.lower())
    if pos == -1:
        return (text[:width] + ("..." if len(text) > width else ""))
    start = max(0, pos - width // 3)
    end = min(len(text), pos + len(q) + 2 * width // 3)
    return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

def search_keyword(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    sql = """
        SELECT p.url, p.title, c.chunk_index, c.content,
               GREATEST(similarity(c.content, %s), similarity(p.title, %s)) AS s
        FROM chunks c JOIN pages p ON p.id=c.page_id
        WHERE c.content ILIKE %s OR p.title ILIKE %s
        ORDER BY s DESC
        LIMIT %s
    """
    try:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (q, q, f"%{q}%", f"%{q}%", limit))
            rows = cur.fetchall()
    except Exception:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.url, p.title, c.chunk_index, c.content
                FROM chunks c JOIN pages p ON p.id=c.page_id
                WHERE c.content ILIKE %s OR p.title ILIKE %s
                LIMIT %s
            """, (f"%{q}%", f"%{q}%", limit))
            rows = cur.fetchall()

    return [{
        "url": r["url"],
        "title": r["title"],
        "chunk_index": r.get("chunk_index"),
        "snippet": _snippet(r.get("content") or "", q),
        "score_hint": "keyword"
    } for r in rows]

def search_semantic(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    # 嵌入查询
    data = embed_batch([q], pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    qvec = data["vectors"][0]

    client = get_qdrant()
    hits = client.search(collection_name=QDRANT_COLLECTION, query_vector=qvec, limit=limit)

    # 取正文
    ids = [h.id for h in hits]
    content_map: Dict[str, str] = {}
    meta_map: Dict[str, Dict[str, Any]] = {}
    if ids:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.id, c.content, p.url, p.title
                FROM chunks c JOIN pages p ON p.id=c.page_id
                WHERE c.id = ANY(%s)
            """, (ids,))
            for r in cur.fetchall():
                content_map[r["id"]] = r["content"]
                meta_map[r["id"]] = {"url": r["url"], "title": r["title"]}

    out = []
    for h in hits:
        cid = h.id
        payload = h.payload or {}
        meta = meta_map.get(cid, {})
        content = content_map.get(cid, "")
        out.append({
            "url": meta.get("url") or payload.get("url"),
            "title": meta.get("title") or payload.get("title"),
            "chunk_index": payload.get("chunk_index"),
            "score": float(h.score),
            "snippet": _snippet(content, q),
            "score_hint": "semantic"
        })
    return out

def search_hybrid(q: str, limit: int = 10, alpha: float = 0.7) -> List[Dict[str, Any]]:
    # 语义候选
    data = embed_batch([q], pooling=EMB_POOLING, normalize=EMB_NORMALIZE)
    qvec = data["vectors"][0]
    client = get_qdrant()
    sem_hits = client.search(collection_name=QDRANT_COLLECTION, query_vector=qvec, limit=max(limit, 20))

    # 关键词候选
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT c.id FROM chunks c JOIN pages p ON p.id=c.page_id
            WHERE c.content ILIKE %s OR p.title ILIKE %s
            LIMIT %s
        """, (f"%{q}%", f"%{q}%", max(limit, 60)))
        kw_ids = {r["id"] for r in cur.fetchall()}

    # 融合：final = alpha*semantic + (1-alpha)*(kw_hit ? 1 : 0)
    merged = []
    for h in sem_hits:
        s = float(h.score)
        k = 1.0 if h.id in kw_ids else 0.0
        merged.append((alpha * s + (1 - alpha) * k, h))
    merged.sort(key=lambda x: x[0], reverse=True)
    merged = merged[:limit]

    ids = [h.id for _, h in merged]
    content_map: Dict[str, str] = {}
    meta_map: Dict[str, Dict[str, Any]] = {}
    if ids:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.id, c.content, p.url, p.title
                FROM chunks c JOIN pages p ON p.id=c.page_id
                WHERE c.id = ANY(%s)
            """, (ids,))
            for r in cur.fetchall():
                content_map[r["id"]] = r["content"]
                meta_map[r["id"]] = {"url": r["url"], "title": r["title"]}

    out = []
    for final, h in merged:
        cid = h.id
        payload = h.payload or {}
        meta = meta_map.get(cid, {})
        content = content_map.get(cid, "")
        out.append({
            "url": meta.get("url") or payload.get("url"),
            "title": meta.get("title") or payload.get("title"),
            "chunk_index": payload.get("chunk_index"),
            "score": final,
            "snippet": _snippet(content, q),
            "score_hint": "hybrid"
        })
    return out

# -----------------------
# 初始化（供 API 层调用）
# -----------------------
def initialize():
    ensure_pg_schema()
    dim = probe_embedding_dim()
    ensure_qdrant_collection(dim)
