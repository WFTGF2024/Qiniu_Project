# api.py
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify

from core import (
    initialize, ingest_url, ingest_urls,
    search_keyword, search_semantic, search_hybrid,
    get_conn
)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "websearch-api"})

# --------- Ingestion ---------
@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(force=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400
    try:
        res = ingest_url(url)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/bulk_ingest", methods=["POST"])
def bulk_ingest():
    data = request.get_json(force=True) or {}
    urls = data.get("urls") or []
    if not isinstance(urls, list) or not urls:
        return jsonify({"error": "missing non-empty 'urls'[]"}), 400
    res = ingest_urls(urls)
    return jsonify(res)

# --------- Search ---------
@app.route("/search/keyword", methods=["GET"])
def route_keyword():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", "10"))
    if not q:
        return jsonify({"error": "missing q"}), 400
    try:
        res = search_keyword(q, limit)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search/semantic", methods=["GET"])
def route_semantic():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", "10"))
    if not q:
        return jsonify({"error": "missing q"}), 400
    try:
        res = search_semantic(q, limit)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search/hybrid", methods=["GET"])
def route_hybrid():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", "10"))
    alpha = float(request.args.get("alpha", "0.7"))
    if not q:
        return jsonify({"error": "missing q"}), 400
    alpha = max(0.0, min(1.0, alpha))
    try:
        res = search_hybrid(q, limit, alpha)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------- Page lookup ---------
@app.route("/page", methods=["GET"])
def page():
    pid = request.args.get("id")
    url = request.args.get("url")
    if not (pid or url):
        return jsonify({"error": "need id or url"}), 400
    sql = "SELECT id, url, title, published_at, fetched_at, lang, site, content, html FROM pages WHERE "
    param = None
    if pid:
        sql += "id=%s"
        param = (int(pid),)
    else:
        sql += "url=%s"
        param = (url,)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, param)
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "not found"}), 404
    # 用 RealDictCursor 会更便于转 JSON；此处简单返回裸元组不如改:
    with get_conn() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, param)
            row = cur.fetchone()
            if row and row.get("html"):
                row["html"] = row["html"][:4000] + ("..." if len(row["html"]) > 4000 else "")
            return jsonify(row or {})

if __name__ == "__main__":
    initialize()
    app.run(host="0.0.0.0", port=5080, debug=True)
