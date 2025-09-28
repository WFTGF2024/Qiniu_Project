# app.py
# -*- coding: utf-8 -*-
"""
Unified Flask API @7210 with 3 Blueprints:
- web  : Web ingest & chunk & embed & Qdrant (prefix /web)
- chat : Chat history CRUD + file_server bridge (prefix /chat)
- core : Users/Membership/Orders/Auth/Security-Reset (no prefix; keep original paths)

依赖：
pip install flask flask-cors pyjwt werkzeug pymysql psycopg2-binary requests trafilatura bs4 qdrant-client

注意：
- PostgreSQL 用于 web 抓取存储（pages/chunks，pg_trgm）
- MySQL 用于 chat/core（users/membership/...）
- Qdrant 用于向量检索
"""

import os
import re
import json
import hashlib
import datetime as dt
from functools import wraps
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime

import requests
import trafilatura
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from flask import Flask, Blueprint, request, jsonify, g
from flask_cors import CORS
import pymysql
from pymysql.cursors import DictCursor
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

# =========================
# 全局配置（可用环境变量覆盖）
# =========================
# --- Web 抓取/Embedding/Qdrant/PostgreSQL ---
WEB_CONFIG = {
    "DATABASE_URL": os.getenv("WEB_PG_URL", "postgresql://postgres:postgres@localhost:5432/websearch"),
    "EMBEDDING_API_BASE": os.getenv("EMB_BASE", "http://120.79.25.184:7202").rstrip("/"),
    "EMBEDDING_API_PATH": os.getenv("EMB_PATH", "/Qwen3-Embedding-4B"),
    "EMB_POOLING": os.getenv("EMB_POOLING", "last"),
    "EMB_NORMALIZE": bool(int(os.getenv("EMB_NORMALIZE", "1"))),
    "QDRANT_URL": os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
    "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY", None),
    "QDRANT_COLLECTION": os.getenv("QDRANT_COLLECTION", "web_chunks"),
    "CHUNK_SIZE": int(os.getenv("CHUNK_SIZE", "800")),
    "CHUNK_OVERLAP": int(os.getenv("CHUNK_OVERLAP", "200")),
    "HTTP_TIMEOUT": int(os.getenv("HTTP_TIMEOUT", "15")),
    "HTTP_UA": os.getenv("HTTP_UA", "Mozilla/5.0 (compatible; mini-websearch/0.1)"),
}

# --- MySQL (chat/core 共用) ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "Qiniu"),
    "password": os.getenv("DB_PASSWORD", "20250922"),
    "database": os.getenv("DB_NAME", "Qiniu_Project"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": True,
}

# --- JWT & 文件服务器（chat/core 共用） ---
SECRET_KEY = os.getenv("SECRET_KEY", "PLEASE_CHANGE_ME_TO_A_RANDOM_SECRET")
ISSUER = os.getenv("JWT_ISS", "qiniu-project")
ACCESS_TOKEN_TTL_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "120"))
RESET_TOKEN_TTL_MIN = int(os.getenv("RESET_TOKEN_TTL_MIN", "15"))
ACCESS_TOKEN_TYPE = "access"

FILE_SERVER_BASE = os.getenv("FILE_SERVER_BASE", "http://127.0.0.1:7201")
HTTP_TIMEOUT = int(os.getenv("CHAT_HTTP_TIMEOUT", "20"))

ENABLE_ACTION_LOG = True  # core 的用户动作日志

# 端口
APP_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("FLASK_PORT", "7210"))
APP_DEBUG = bool(int(os.getenv("FLASK_DEBUG", "0")))

# =========================
# Flask 应用与蓝图
# =========================
app = Flask(__name__)
CORS(app)

web_bp = Blueprint("web", __name__, url_prefix="/web")
chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
core_bp = Blueprint("core", __name__)  # 保持原路径不加前缀

# =========================
# 公用：MySQL 连接（chat/core）
# =========================
def get_mysql_conn():
    if "db_conn" not in g:
        g.db_conn = pymysql.connect(**DB_CONFIG)
    return g.db_conn

@app.teardown_appcontext
def _teardown_mysql(exc):
    conn = g.pop("db_conn", None)
    if conn:
        conn.close()

# =========================
# 公用：JWT & 工具（chat/core）
# =========================
def json_response(data=None, success=True, status=200, **kwargs):
    payload = {"success": success}
    if data is not None:
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload), status

def now_utc():
    return dt.datetime.utcnow()

def isoformat(ts: dt.datetime | None):
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def make_jwt(sub: str, ttl_minutes: int, token_type: str = "access", extra_claims: dict | None = None):
    exp = now_utc() + dt.timedelta(minutes=ttl_minutes)
    claims = {"iss": ISSUER, "sub": str(sub), "exp": exp, "iat": now_utc(), "type": token_type}
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, SECRET_KEY, algorithm="HS256")
    return token, exp

def decode_jwt(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"require": ["exp", "iat", "iss", "sub"]}, issuer=ISSUER)

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return json_response(success=False, status=401, message="缺少或非法的Authorization头")
        token = auth.split(" ", 1)[1].strip()
        try:
            claims = decode_jwt(token)
            if claims.get("type") != ACCESS_TOKEN_TYPE:
                return json_response(success=False, status=401, message="令牌类型错误")
            g.user_id = int(claims["sub"])
            g.jwt_claims = claims
        except jwt.ExpiredSignatureError:
            return json_response(success=False, status=401, message="令牌已过期")
        except jwt.InvalidTokenError:
            return json_response(success=False, status=401, message="无效令牌")
        return fn(*args, **kwargs)
    return wrapper

def log_action(user_id, action_type, resource_type, resource_id, extra=None):
    if not ENABLE_ACTION_LOG:
        return
    try:
        conn = get_mysql_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_action_logs
                  (user_id, action_type, resource_type, resource_id, request_id, ip_addr, user_agent, extra_json, created_at)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (
                    int(user_id) if user_id is not None else 0,
                    action_type or "",
                    resource_type or "",
                    str(resource_id) if resource_id is not None else "",
                    request.headers.get("X-Request-ID"),
                    request.headers.get("X-Forwarded-For") or request.remote_addr,
                    request.headers.get("User-Agent"),
                    json.dumps(extra, ensure_ascii=False) if extra else None,
                ),
            )
    except Exception:
        pass  # 审计失败不影响主流程

# =========================
# A. web 蓝图（PostgreSQL + Qdrant + Embedding）
# =========================
# PG 连接
def get_pg_conn():
    return psycopg2.connect(WEB_CONFIG["DATABASE_URL"])

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
    with get_pg_conn() as conn, conn.cursor() as cur:
        for s in sqls:
            cur.execute(s)
        conn.commit()

# Qdrant
_qdrant_client: Optional[QdrantClient] = None
EMB_DIM: Optional[int] = None

def get_qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=WEB_CONFIG["QDRANT_URL"],
            api_key=WEB_CONFIG["QDRANT_API_KEY"],
            prefer_grpc=False,
            timeout=30,
            check_compatibility=False,
        )
    return _qdrant_client

def ensure_qdrant_collection(dim: int):
    url = f"{WEB_CONFIG['QDRANT_URL']}/collections/{WEB_CONFIG['QDRANT_COLLECTION']}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        info = r.json()
        current_dim = info["result"]["config"]["params"]["vectors"]["size"]
        if current_dim != dim:
            # 维度不一致 → 直接删重建（也可改为报错）
            requests.delete(url, timeout=10)
            payload = {"vectors": {"size": dim, "distance": "Cosine"}}
            requests.put(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
        return
    elif r.status_code == 404:
        payload = {"vectors": {"size": dim, "distance": "Cosine"}}
        requests.put(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
    else:
        raise RuntimeError(f"访问 Qdrant 出错: {r.status_code}, {r.text}")

# Embedding
def _embed_api_url() -> str:
    return f"{WEB_CONFIG['EMBEDDING_API_BASE']}{WEB_CONFIG['EMBEDDING_API_PATH']}"

def embed_batch(texts: List[str], pooling=None, normalize=None, dim=None,
                instruction=None, prefix=None) -> Dict[str, Any]:
    url = _embed_api_url()
    payload = {"texts": [str(t or "").strip() for t in texts]}
    if pooling is not None:   payload["pooling"] = pooling
    if normalize is not None: payload["normalize"] = bool(normalize)
    if dim is not None:       payload["dim"] = int(dim)
    if instruction:           payload["instruction"] = instruction
    if prefix:                payload["prefix"] = prefix
    r = requests.post(url, json=payload, timeout=WEB_CONFIG["HTTP_TIMEOUT"])
    r.raise_for_status()
    return r.json()

def probe_embedding_dim() -> int:
    global EMB_DIM
    if EMB_DIM:
        return EMB_DIM
    data = embed_batch(["__dim_probe__"], pooling=WEB_CONFIG["EMB_POOLING"], normalize=WEB_CONFIG["EMB_NORMALIZE"])
    EMB_DIM = int(data.get("dim") or len(data["vectors"][0]))
    return EMB_DIM

# 抓取解析与切块
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": WEB_CONFIG["HTTP_UA"]}, timeout=WEB_CONFIG["HTTP_TIMEOUT"])
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

# 入库
def upsert_page(url: str, html: str, parsed: Dict[str, Any]) -> int:
    now = datetime.utcnow()
    content = parsed["content"] or ""
    chksum = checksum_text(content or html)
    with get_pg_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
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
    blocks = chunk_text(content, WEB_CONFIG["CHUNK_SIZE"], WEB_CONFIG["CHUNK_OVERLAP"])
    if not blocks:
        return 0
    with get_pg_conn() as conn, conn.cursor() as cur:
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
    data = embed_batch(blocks, pooling=WEB_CONFIG["EMB_POOLING"], normalize=WEB_CONFIG["EMB_NORMALIZE"])
    vectors = data["vectors"]
    ensure_qdrant_collection(dim)
    client = get_qdrant()
    points = [PointStruct(id=cid, vector=vec, payload={"page_id": page_id, "url": url, "title": title})
              for cid, vec in zip(chunk_ids, vectors)]
    client.upsert(collection_name=WEB_CONFIG["QDRANT_COLLECTION"], points=points)
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
# --- 辅助：查询向量 & Qdrant 搜索 ---
def _embed_query(q: str) -> List[float]:
    data = embed_batch([q], pooling=WEB_CONFIG["EMB_POOLING"], normalize=WEB_CONFIG["EMB_NORMALIZE"])
    return data["vectors"][0]

def _qdrant_search(qvec: List[float], top_k: int = 10):
    client = get_qdrant()
    res = client.query_points(
        collection_name=WEB_CONFIG["QDRANT_COLLECTION"],
        query_vector=qvec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )
    # 结果：[{point.id, score, payload:{page_id,url,title}}...]
    return res

# --- 辅助：PG基于 pg_trgm 的词法检索（按 content 相似度）---
def _pg_lexical_search(q: str, limit: int = 10):
    sql = """
    SELECT p.id AS page_id, p.url, p.title, p.site, p.published_at, p.fetched_at,
           substring(p.content for 400) AS snippet,
           similarity(p.content, %s) AS score
    FROM pages p
    WHERE p.content ILIKE %s
    ORDER BY score DESC
    LIMIT %s
    """
    with get_pg_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (q, f"%{q}%", limit))
        rows = cur.fetchall() or []
    return rows

# --- 辅助：按 chunk_id 批量取 chunk 内容（用于向量检索的片段预览）---
def _get_chunks_by_ids(chunk_ids: List[int]) -> Dict[int, str]:
    if not chunk_ids:
        return {}
    sql = "SELECT id, content FROM chunks WHERE id = ANY(%s)"
    with get_pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (chunk_ids,))
        rows = cur.fetchall() or []
    return {rid: rcontent for (rid, rcontent) in rows}

# --- 辅助：取页面基本信息 ---
def _get_pages_by_ids(page_ids: List[int]) -> Dict[int, dict]:
    if not page_ids:
        return {}
    sql = """SELECT id AS page_id, url, title, site, published_at, fetched_at
             FROM pages WHERE id = ANY(%s)"""
    with get_pg_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (page_ids,))
        rows = cur.fetchall() or []
    return {row["page_id"]: row for row in rows}

# --- /web/search：支持 vector / lexical / hybrid ---
@web_bp.post("/search")
@app.route("/web/search", methods=["POST"])
def web_search():
    """
    输入:
      {
        "q": "query string",
        "top_k": 10,
        "mode": "hybrid",   # "vector" | "lexical" | "hybrid"
        "alpha": 0.6
      }
    输出：统一为 page 粒度，含 snippet
    """
    data = request.get_json(force=True) or {}
    q = (data.get("q") or "").strip()
    if not q:
        return jsonify({"success": False, "error": "missing q"}), 400

    top_k = int(data.get("top_k") or 10)
    mode = (data.get("mode") or "hybrid").lower()
    alpha = float(data.get("alpha") or 0.6)
    top_k = max(1, min(50, top_k))
    alpha = min(1.0, max(0.0, alpha))

    vec_res, lex_res = [], []

    # 1) 向量检索
    if mode in ("vector", "hybrid"):
        try:
            qvec = _embed_query(q)
            # ⚠️ 用 query_points 替代 search
            vec_hits = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=qvec,
                limit=top_k * 3,
                with_payload=True,
            ).points or []
        except Exception as e:
            print("Qdrant 查询失败:", e)
            vec_hits = []

        page_best = {}
        if vec_hits:
            chunk_ids = [int(h.id) for h in vec_hits]
            id2chunk = _get_chunks_by_ids(chunk_ids)

            for h in vec_hits:
                try:
                    pid = int(h.payload.get("page_id"))
                except Exception:
                    continue
                score = float(h.score or 0.0)
                if (pid not in page_best) or (score > page_best[pid]["score"]):
                    chunk_text = (id2chunk.get(int(h.id)) or "")[:400]
                    page_best[pid] = {
                        "page_id": pid,
                        "url": h.payload.get("url"),
                        "title": h.payload.get("title"),
                        "score": score,
                        "snippet": chunk_text,
                        "source": "vector",
                    }
        vec_res = sorted(page_best.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    # 2) 词法检索
    if mode in ("lexical", "hybrid"):
        try:
            lex_rows = _pg_lexical_search(q, limit=top_k * 3) or []
        except Exception as e:
            print("Postgres 词法检索失败:", e)
            lex_rows = []

        for r in lex_rows:
            r["source"] = "lexical"
        lex_res = lex_rows[:top_k]

    # 3) 融合
    if mode == "vector":
        merged = vec_res
    elif mode == "lexical":
        merged = lex_res
    else:
        # hybrid 融合
        def _norm(scores):
            if not scores:
                return {}
            mn, mx = min(scores), max(scores)
            if mx <= mn:
                return {i: 1.0 for i in range(len(scores))}
            return {i: (s - mn) / (mx - mn) for i, s in enumerate(scores)}

        v_scores = _norm([x["score"] for x in vec_res]) if vec_res else {}
        l_scores = _norm([x["score"] for x in lex_res]) if lex_res else {}

        pid2vec = {x["page_id"]: (i, x) for i, x in enumerate(vec_res)}
        pid2lex = {x["page_id"]: (i, x) for i, x in enumerate(lex_res)}
        all_pids = set(pid2vec) | set(pid2lex)

        by_pid = {}
        for pid in all_pids:
            v_i, v_item = pid2vec.get(pid, (None, None))
            l_i, l_item = pid2lex.get(pid, (None, None))
            vnorm = v_scores.get(v_i, 0.0) if v_item else 0.0
            lnorm = l_scores.get(l_i, 0.0) if l_item else 0.0
            fused = alpha * vnorm + (1 - alpha) * lnorm

            base = v_item or l_item
            rec = {
                "page_id": pid,
                "url": base.get("url"),
                "title": base.get("title"),
                "snippet": base.get("snippet"),
                "score_vector": v_item["score"] if v_item else 0.0,
                "score_lexical": l_item["score"] if l_item else 0.0,
                "score": fused,
                "source": "hybrid",
            }
            by_pid[pid] = rec

        merged = sorted(by_pid.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    # 4) 补充页面元数据
    pages = _get_pages_by_ids([m["page_id"] for m in merged]) if merged else {}
    for m in merged:
        meta = pages.get(m["page_id"]) or {}
        m["site"] = meta.get("site")
        m["published_at"] = (
            meta.get("published_at").isoformat() if meta.get("published_at") else None
        )
        m["fetched_at"] = (
            meta.get("fetched_at").isoformat() if meta.get("fetched_at") else None
        )

    return jsonify({
        "success": True,
        "q": q,
        "mode": mode,
        "alpha": alpha,
        "top_k": top_k,
        "results": merged or []
    })

# --- /web/page：返回 page 详情与其 chunks（可分页）---
@web_bp.get("/page")
def web_page():
    """
    查询参数：
      - page_id: 必填
      - with_chunks: 0/1（默认1）
      - limit: 返回 chunk 数量（默认 50）
      - offset: 偏移（默认 0）
    """
    try:
        page_id = int(request.args.get("page_id", "0"))
    except ValueError:
        return jsonify({"error": "invalid page_id"}), 400
    if page_id <= 0:
        return jsonify({"error": "missing page_id"}), 400

    with_chunks = request.args.get("with_chunks", "1") != "0"
    limit = int(request.args.get("limit", "50"))
    offset = int(request.args.get("offset", "0"))
    limit = max(1, min(200, limit))
    offset = max(0, offset)

    # 取 page
    with get_pg_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id AS page_id, url, title, site, published_at, fetched_at, lang
                       FROM pages WHERE id=%s""", (page_id,))
        page = cur.fetchone()
        if not page:
            return jsonify({"error": "page not found"}), 404

        page["published_at"] = page["published_at"].isoformat() if page.get("published_at") else None
        page["fetched_at"] = page["fetched_at"].isoformat() if page.get("fetched_at") else None

        resp = {"page": page, "chunks": []}

        if with_chunks:
            cur.execute("""SELECT id AS chunk_id, chunk_index, substring(content for 1200) AS content
                           FROM chunks
                           WHERE page_id=%s
                           ORDER BY chunk_index ASC
                           LIMIT %s OFFSET %s
                        """, (page_id, limit, offset))
            resp["chunks"] = cur.fetchall() or []

    return jsonify(resp)
# 路由（web）
@web_bp.get("/health")
def web_health():
    return jsonify({"status": "ok", "service": "websearch-api"})

@web_bp.post("/ingest")
def api_ingest():
    data = request.get_json(force=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400
    return jsonify(ingest_url(url))

@web_bp.post("/bulk_ingest")
def api_bulk_ingest():
    data = request.get_json(force=True) or {}
    urls = data.get("urls") or []
    if not urls:
        return jsonify({"error": "missing urls"}), 400
    return jsonify(ingest_urls(urls))

# =========================
# B. chat 蓝图（聊天记录 + 文件永久化）
# =========================
def fs_permanent_upload(user_id: int, file_storage) -> str:
    """
    上传文件至永久存储，返回可下载直链 content_url: {FILE_SERVER_BASE}/permanent/download/{file_id}
    """
    # 1) 上传
    url_up = f"{FILE_SERVER_BASE}/permanent/upload/{user_id}"
    files = {"file": (file_storage.filename, file_storage.stream, file_storage.mimetype)}
    r = requests.post(url_up, files=files, timeout=HTTP_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"file_server upload failed: {r.status_code} {r.text}")
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    filename = data.get("filename") or file_storage.filename
    if not filename:
        raise RuntimeError("file_server upload resp missing filename")

    # 2) 列表查询 file_id
    url_ls = f"{FILE_SERVER_BASE}/permanent/files/{user_id}"
    r2 = requests.get(url_ls, timeout=HTTP_TIMEOUT)
    if r2.status_code != 200:
        raise RuntimeError(f"file_server list failed: {r2.status_code} {r2.text}")
    files_json = r2.json() or []
    target = next((x for x in files_json if x.get("filename") == filename), None)
    if not target or "file_id" not in target:
        raise RuntimeError("cannot resolve file_id by filename after upload")
    file_id = target["file_id"]
    return f"{FILE_SERVER_BASE}/permanent/download/{file_id}"

# 路由（chat）
@chat_bp.post("/api/chat/save")
@auth_required
def chat_save():
    if "file" not in request.files:
        return json_response(success=False, status=400, message="缺少 file")
    record_id = request.form.get("record_id")
    if not record_id:
        return json_response(success=False, status=400, message="缺少 record_id")

    file_storage = request.files["file"]
    # 调用文件服务器上传
    new_url = fs_permanent_upload(g.user_id, file_storage)

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_history (user_id, record_id, content_url) VALUES (%s,%s,%s)",
            (g.user_id, record_id, new_url),
        )
        chat_id = cur.lastrowid

    return jsonify({"success": True, "chat_id": chat_id, "url": new_url})

@chat_bp.get("/api/chat/<int:user_id>")
@auth_required
def chat_list(user_id: int):
    if g.user_id != user_id:
        log_action(g.user_id, "chat_list_forbidden", "chat_history", str(user_id))
        return json_response(success=False, status=403, message="无权限访问他人聊天记录")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT chat_id, record_id, content_url, created_at, updated_at
               FROM chat_history
               WHERE user_id=%s
               ORDER BY created_at DESC, chat_id DESC""",
            (user_id,),
        )
        rows = cur.fetchall() or []
    for r in rows:
        r["created_at"] = isoformat(r["created_at"])
        r["updated_at"] = isoformat(r["updated_at"])
    log_action(g.user_id, "chat_list", "chat_history", str(user_id), {"count": len(rows)})
    return jsonify(rows), 200

@chat_bp.get("/api/chat/<int:user_id>/latest")
@auth_required
def chat_latest(user_id: int):
    if g.user_id != user_id:
        log_action(g.user_id, "chat_latest_forbidden", "chat_history", str(user_id))
        return json_response(success=False, status=403, message="无权限访问他人聊天记录")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT chat_id, record_id, content_url, created_at, updated_at
               FROM chat_history
               WHERE user_id=%s
               ORDER BY created_at DESC, chat_id DESC
               LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return jsonify({"success": True, "history": None}), 200
    
    row["created_at"] = isoformat(row["created_at"])
    row["updated_at"] = isoformat(row["updated_at"])
    log_action(g.user_id, "chat_latest", "chat_history", str(user_id), {"chat_id": row["chat_id"]})
    return jsonify(row), 200

@chat_bp.get("/api/chat/<int:user_id>/recent")
@auth_required
def chat_recent(user_id: int):
    if g.user_id != user_id:
        log_action(g.user_id, "chat_recent_forbidden", "chat_history", str(user_id))
        return json_response(success=False, status=403, message="无权限访问他人聊天记录")
    try:
        n = int(request.args.get("n", "10"))
        n = max(1, min(100, n))
    except ValueError:
        n = 10
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT chat_id, record_id, content_url, created_at, updated_at
               FROM chat_history
               WHERE user_id=%s
               ORDER BY created_at DESC, chat_id DESC
               LIMIT %s""",
            (user_id, n),
        )
        rows = cur.fetchall() or []
    for r in rows:
        r["created_at"] = isoformat(r["created_at"])
        r["updated_at"] = isoformat(r["updated_at"])
    log_action(g.user_id, "chat_recent", "chat_history", str(user_id), {"n": n, "count": len(rows)})
    return jsonify(rows), 200

@chat_bp.put("/api/chat/<int:chat_id>")
@auth_required
def chat_update(chat_id: int):
    if "file" not in request.files:
        log_action(g.user_id, "chat_update_bad_request", "chat_history", str(chat_id), {"reason": "missing file"})
        return json_response(success=False, status=400, message="缺少 file (FormData)")

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM chat_history WHERE chat_id=%s", (chat_id,))
        row = cur.fetchone()
        if not row:
            log_action(g.user_id, "chat_update_not_found", "chat_history", str(chat_id))
            return json_response(success=False, status=404, message="聊天记录不存在")
        if int(row["user_id"]) != g.user_id:
            log_action(g.user_id, "chat_update_forbidden", "chat_history", str(chat_id))
            return json_response(success=False, status=403, message="无权限更新他人聊天记录")

    file_storage = request.files["file"]
    try:
        new_url = fs_permanent_upload(g.user_id, file_storage)
        if len(new_url) > 255:
            raise RuntimeError("生成的 content_url 超过 255 字符")
    except Exception as e:
        log_action(g.user_id, "chat_update_upload_fail", "chat_history", str(chat_id), {"error": str(e)})
        return json_response(success=False, status=502, message=f"上传文件到文件服务器失败: {e}")

    with conn.cursor() as cur:
        cur.execute("UPDATE chat_history SET content_url=%s WHERE chat_id=%s", (new_url, chat_id))

    log_action(g.user_id, "chat_update", "chat_history", str(chat_id), {"content_url": new_url})
    return jsonify({"success": True, "chat_id": chat_id, "message": "聊天记录已更新"}), 200

@chat_bp.delete("/api/chat/<int:chat_id>")
@auth_required
def chat_delete(chat_id: int):
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, record_id FROM chat_history WHERE chat_id=%s", (chat_id,))
        row = cur.fetchone()
        if not row:
            log_action(g.user_id, "chat_delete_not_found", "chat_history", str(chat_id))
            return json_response(success=False, status=404, message="聊天记录不存在")
        if int(row["user_id"]) != g.user_id:
            log_action(g.user_id, "chat_delete_forbidden", "chat_history", str(chat_id))
            return json_response(success=False, status=403, message="无权限删除他人聊天记录")

        cur.execute("DELETE FROM chat_history WHERE chat_id=%s", (chat_id,))

    log_action(g.user_id, "chat_delete", "chat_history", str(chat_id), {"record_id": row["record_id"]})
    return jsonify({"success": True, "message": "聊天记录已删除"}), 200

@chat_bp.get("/healthz")
def chat_healthz():
    try:
        with get_mysql_conn().cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# =========================
# C. core 蓝图（用户/会员/订单/认证/密保）
# =========================
def get_user_by_username(username: str):
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        return cur.fetchone()

def get_user_by_id(user_id: int):
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        return cur.fetchone()

def public_user_view(row: dict):
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "full_name": row.get("full_name"),
        "email": row["email"],
        "phone_number": row["phone_number"],
        "created_at": isoformat(row.get("created_at")),
        "updated_at": isoformat(row.get("updated_at")),
    }

# 1) 注册
@core_bp.post("/api/auth/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    required = [
        "username", "password", "full_name", "email", "phone_number",
        "security_question1", "security_answer1",
        "security_question2", "security_answer2",
    ]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return json_response(success=False, status=400, message=f"缺少字段: {', '.join(missing)}")

    username = data["username"].strip()
    if get_user_by_username(username):
        return json_response(success=False, status=409, message="用户名已存在")

    password_hash = generate_password_hash(data["password"])
    ans1_hash = generate_password_hash(data["security_answer1"])
    ans2_hash = generate_password_hash(data["security_answer2"])

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO users
                  (username, password_hash, full_name, email, phone_number,
                   security_question1, security_answer1_hash,
                   security_question2, security_answer2_hash,
                   created_at, updated_at)
                VALUES
                  (%s,%s,%s,%s,%s,%s,%s,%s,%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    username, password_hash, data["full_name"], data["email"], data["phone_number"],
                    data["security_question1"], ans1_hash,
                    data["security_question2"], ans2_hash
                )
            )
            user_id = cur.lastrowid
        except pymysql.err.IntegrityError as e:
            msg = "唯一性约束冲突（用户名/邮箱/手机号已存在）"
            return json_response(success=False, status=409, message=msg, error=str(e))

    log_action(user_id, "register", "user", user_id, {"username": username})
    return jsonify({"success": True, "user_id": user_id, "message": "注册成功"}), 201

# 2) 登录
@core_bp.post("/api/auth/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return json_response(success=False, status=401, message="用户名或密码错误")

    token, exp = make_jwt(user["user_id"], ACCESS_TOKEN_TTL_MIN, token_type="access")
    log_action(user["user_id"], "login", "user", user["user_id"])
    return jsonify({
        "success": True,
        "token": token,
        "user_id": user["user_id"],
        "expire_at": exp.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    })

# 3) 我
@core_bp.get("/api/auth/me")
@auth_required
def me():
    user = get_user_by_id(g.user_id)
    if not user:
        return json_response(success=False, status=404, message="用户不存在")
    return jsonify(public_user_view(user))

# 4) 更新用户
@core_bp.put("/api/users/<int:user_id>")
@auth_required
def update_user(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限修改其他用户")
    data = request.get_json(force=True, silent=True) or {}
    allow = ["full_name", "email", "phone_number"]
    updates = {k: data[k] for k in allow if k in data}
    if not updates:
        return json_response(success=False, status=400, message="无可更新字段")

    sets = ", ".join([f"{k}=%s" for k in updates])
    params = list(updates.values()) + [user_id]
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        try:
            cur.execute(f"UPDATE users SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s", params)
            if cur.rowcount == 0:
                return json_response(success=False, status=404, message="用户不存在")
        except pymysql.err.IntegrityError as e:
            return json_response(success=False, status=409, message="唯一性约束冲突", error=str(e))
    log_action(user_id, "update", "user", user_id, {"fields": list(updates.keys())})
    return jsonify({"success": True, "message": "用户信息已更新"})

# 5) 删除用户
@core_bp.delete("/api/users/<int:user_id>")
@auth_required
def delete_user(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限删除其他用户")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        if cur.rowcount == 0:
            return json_response(success=False, status=404, message="用户不存在")
    log_action(user_id, "delete", "user", user_id)
    return jsonify({"success": True, "message": "用户已删除"})

# 6) 验证密保
@core_bp.post("/api/auth/verify-security")
def verify_security():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    ans1 = data.get("security_answer1", "")
    ans2 = data.get("security_answer2", "")

    user = get_user_by_username(username)
    if not user:
        return json_response(success=False, status=401, message="验证失败")

    ok1 = check_password_hash(user["security_answer1_hash"], ans1)
    ok2 = check_password_hash(user["security_answer2_hash"], ans2)
    if not (ok1 and ok2):
        return json_response(success=False, status=401, message="验证失败")

    reset_token, _ = make_jwt(user["user_id"], RESET_TOKEN_TTL_MIN, token_type="reset")
    log_action(user["user_id"], "verify_security", "user", user["user_id"])
    return jsonify({"success": True, "reset_token": reset_token})

# 7) 重置密码
@core_bp.post("/api/auth/reset-password")
def reset_password():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("reset_token", "")
    new_password = data.get("new_password", "")
    if not token or not new_password:
        return json_response(success=False, status=400, message="缺少 reset_token 或 new_password")
    try:
        claims = decode_jwt(token)
        if claims.get("type") != "reset":
            return json_response(success=False, status=401, message="令牌类型错误")
        user_id = int(claims["sub"])
    except jwt.ExpiredSignatureError:
        return json_response(success=False, status=401, message="重置令牌已过期")
    except jwt.InvalidTokenError:
        return json_response(success=False, status=401, message="无效重置令牌")

    pwd_hash = generate_password_hash(new_password)
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET password_hash=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s", (pwd_hash, user_id))
        if cur.rowcount == 0:
            return json_response(success=False, status=404, message="用户不存在")

    log_action(user_id, "reset_password", "user", user_id)
    return jsonify({"success": True, "message": "密码已更新"})

# 8) 会员视图/订单
def membership_view(row: dict):
    return {
        "membership_id": row["membership_id"],
        "user_id": row["user_id"],
        "start_date": row["start_date"].isoformat(),
        "expire_date": row["expire_date"].isoformat(),
        "status": row["status"],
    }

def order_view(row: dict):
    return {
        "order_id": row["order_id"],
        "user_id": row.get("user_id"),
        "purchase_date": isoformat(row.get("purchase_date")),
        "duration_months": row["duration_months"],
        "amount": float(row["amount"]),
        "payment_method": row["payment_method"],
    }

@core_bp.get("/api/membership/<int:user_id>")
@auth_required
def get_membership(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人会员信息")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_info WHERE user_id=%s ORDER BY last_updated DESC, membership_id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="未找到会员信息")
    return jsonify(membership_view(row))

@core_bp.get("/api/membership/orders/<int:user_id>")
@auth_required
def list_orders(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC",
            (user_id,)
        )
        rows = cur.fetchall()
    return jsonify([order_view(r) for r in rows])

@core_bp.post("/api/membership")
@auth_required
def create_membership():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "start_date", "expire_date", "status"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return json_response(success=False, status=400, message=f"缺少字段: {', '.join(missing)}")
    if g.user_id != int(data["user_id"]):
        return json_response(success=False, status=403, message="无权限为他人创建会员")

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO membership_info
              (user_id, start_date, expire_date, status, last_updated)
            VALUES
              (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (data["user_id"], data["start_date"], data["expire_date"], data["status"])
        )
        membership_id = cur.lastrowid
    log_action(data["user_id"], "create", "membership_info", membership_id)
    return jsonify({"success": True, "membership_id": membership_id, "message": "会员信息已创建"}), 201

@core_bp.get("/api/membership")
@auth_required
def list_all_memberships():
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM membership_info ORDER BY last_updated DESC, membership_id DESC")
        rows = cur.fetchall()
    return jsonify([membership_view(r) for r in rows])

@core_bp.put("/api/membership/<int:membership_id>")
@auth_required
def update_membership(membership_id: int):
    data = request.get_json(force=True, silent=True) or {}
    allow = ["start_date", "expire_date", "status"]
    updates = {k: data[k] for k in allow if k in data}
    if not updates:
        return json_response(success=False, status=400, message="无可更新字段")

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM membership_info WHERE membership_id=%s", (membership_id,))
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="会员信息不存在")
        if g.user_id != int(row["user_id"]):
            return json_response(success=False, status=403, message="无权限更新他人会员信息")

        sets = ", ".join([f"{k}=%s" for k in updates])
        params = list(updates.values()) + [membership_id]
        cur.execute(f"UPDATE membership_info SET {sets}, last_updated=CURRENT_TIMESTAMP WHERE membership_id=%s", params)

    log_action(g.user_id, "update", "membership_info", membership_id, {"fields": list(updates.keys())})
    return jsonify({"success": True, "message": "会员信息已更新"})

@core_bp.delete("/api/membership/<int:membership_id>")
@auth_required
def delete_membership(membership_id: int):
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM membership_info WHERE membership_id=%s", (membership_id,))
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="会员信息不存在")
        if g.user_id != int(row["user_id"]):
            return json_response(success=False, status=403, message="无权限删除他人会员信息")

        cur.execute("DELETE FROM membership_info WHERE membership_id=%s", (membership_id,))

    log_action(g.user_id, "delete", "membership_info", membership_id)
    return jsonify({"success": True, "message": "会员信息已删除"})

@core_bp.post("/api/membership/orders")
@auth_required
def create_order():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "duration_months", "amount", "payment_method"]
    missing = [k for k in required if data.get(k) in (None, "")]
    if missing:
        return json_response(success=False, status=400, message=f"缺少字段: {', '.join(missing)}")
    if g.user_id != int(data["user_id"]):
        return json_response(success=False, status=403, message="无权限为他人创建订单")

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO membership_orders
              (user_id, purchase_date, duration_months, amount, payment_method)
            VALUES
              (%s, CURRENT_TIMESTAMP, %s, %s, %s)
            """,
            (data["user_id"], data["duration_months"], data["amount"], data["payment_method"])
        )
        order_id = cur.lastrowid
    log_action(data["user_id"], "create", "membership_orders", order_id, {"payment_method": data["payment_method"]})
    return jsonify({"success": True, "order_id": order_id, "message": "订单已创建"}), 201

@core_bp.get("/api/membership/orders/<int:user_id>/latest")
@auth_required
def latest_order(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="无订单记录")
    return jsonify(order_view(row))

@core_bp.get("/api/membership/orders/<int:user_id>/recent")
@auth_required
def recent_orders(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")
    try:
        n = int(request.args.get("n", "5"))
        n = max(1, min(n, 100))
    except ValueError:
        n = 5
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC LIMIT %s",
            (user_id, n)
        )
        rows = cur.fetchall()
    return jsonify([order_view(r) for r in rows])

# root 健康检查（core）
@core_bp.get("/healthz")
def core_healthz():
    try:
        with get_mysql_conn().cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# =========================
# 注册蓝图 & 启动前初始化
# =========================
app.register_blueprint(web_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(core_bp)

def initialize_startup():
    # 初始化 PostgreSQL schema / 探测维度 / 确保 Qdrant collection
    ensure_pg_schema()
    dim = probe_embedding_dim()
    ensure_qdrant_collection(dim)

if __name__ == "__main__":
    initialize_startup()
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
