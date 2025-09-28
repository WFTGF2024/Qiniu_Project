# -*- coding: utf-8 -*-
"""
Chat History CRUD API (Flask)
- 使用现有 MySQL 表: chat_history / users / user_action_logs / user_permanent_files
- JWT 鉴权: HS256，与现有 auth_and_vip.py 对齐 (Authorization: Bearer <token>)
- 文件持久化: 调用 file_server.py 永久存储接口
- 监听端口: 7209
"""

import os
import json
import datetime as dt
from functools import wraps

import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, request, jsonify, g
import jwt
import requests

# =========================
# 环境配置（按需覆盖）
# =========================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "test"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": True,
}

# 与 auth_and_vip.py 的签发保持一致
SECRET_KEY = os.getenv("SECRET_KEY", "PLEASE_CHANGE_ME_TO_A_RANDOM_SECRET")
ISSUER = os.getenv("JWT_ISS", "your-issuer")
ACCESS_TOKEN_TYPE = "access"

# file_server 基址（file_server.py 监听端口按你的实际部署）
FILE_SERVER_BASE = os.getenv("FILE_SERVER_BASE", "http://127.0.0.1:7201")
HTTP_TIMEOUT = 20

# =========================
# Flask
# =========================
app = Flask(__name__)

# =========================
# DB 连接
# =========================
def get_conn():
    if "db_conn" not in g:
        g.db_conn = pymysql.connect(**DB_CONFIG)
    return g.db_conn

@app.teardown_appcontext
def close_conn(exc):
    conn = g.pop("db_conn", None)
    if conn:
        conn.close()

# =========================
# 工具
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

def isoformat(ts):
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def decode_jwt(token: str):
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=["HS256"],
        options={"require": ["exp", "iat", "iss", "sub"]},
        issuer=ISSUER,
    )

def auth_required(f):
    @wraps(f)
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
        return f(*args, **kwargs)
    return wrapper

def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")

def log_action(user_id: int, action_type: str, resource_type: str, resource_id: str, extra: dict | None = None):
    """
    写入 user_action_logs
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO user_action_logs
               (user_id, action_type, resource_type, resource_id, request_id, ip_addr, user_agent, extra_json)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                int(user_id),
                action_type,
                resource_type,
                str(resource_id),
                request.headers.get("X-Request-ID", None),
                get_client_ip(),
                request.headers.get("User-Agent", "")[:512],
                json.dumps(extra or {}, ensure_ascii=False),
            ),
        )

# =========================
# File Server 适配：永久区
# =========================
def fs_permanent_upload(user_id: int, file_storage) -> str:
    """
    上传文件至永久存储，返回可下载直链 content_url:
    {FILE_SERVER_BASE}/permanent/download/{file_id}
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

    # 2) 查询该用户的永久文件，找到刚上传的同名文件的 file_id
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

# =========================
# 3. 聊天记录 CRUD（严格匹配你的接口规范）
# =========================

# 3.1 保存聊天记录
@app.post("/api/chat/save")
@auth_required
def chat_save():
    payload = request.get_json(force=True, silent=True) or {}
    user_id = int(payload.get("user_id") or 0)
    record_id = (payload.get("record_id") or "").strip()
    content_url = (payload.get("content_url") or "").strip()

    if not (user_id and record_id and content_url):
        log_action(g.user_id, "chat_save_bad_request", "chat_history", record_id or "", {"reason": "missing fields"})
        return json_response(success=False, status=400, message="缺少 user_id/record_id/content_url")

    # 只能本人保存
    if g.user_id != user_id:
        log_action(g.user_id, "chat_save_forbidden", "chat_history", record_id, {"try_user_id": user_id})
        return json_response(success=False, status=403, message="无权限保存他人聊天记录")

    conn = get_conn()
    with conn.cursor() as cur:
        # 检查 record_id 是否已存在（全局唯一）
        cur.execute("SELECT chat_id, user_id FROM chat_history WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if row:
            # 存在但归属他人 → 409
            if int(row["user_id"]) != user_id:
                log_action(g.user_id, "chat_save_conflict", "chat_history", record_id, {"owner_user_id": row["user_id"]})
                return json_response(success=False, status=409, message="record_id 已存在且归属他人")
            # 同一用户相同 record_id → 幂等更新 content_url
            cur.execute("UPDATE chat_history SET content_url=%s WHERE chat_id=%s", (content_url, row["chat_id"]))
            chat_id = row["chat_id"]
        else:
            # 新增
            cur.execute(
                "INSERT INTO chat_history (user_id, record_id, content_url) VALUES (%s, %s, %s)",
                (user_id, record_id, content_url),
            )
            chat_id = cur.lastrowid

    log_action(g.user_id, "chat_save", "chat_history", record_id, {"chat_id": chat_id})
    return jsonify({"success": True, "chat_id": chat_id, "message": "聊天记录已保存"}), 200


# 3.2 获取聊天记录列表
@app.get("/api/chat/<int:user_id>")
@auth_required
def chat_list(user_id: int):
    if g.user_id != user_id:
        log_action(g.user_id, "chat_list_forbidden", "chat_history", str(user_id))
        return json_response(success=False, status=403, message="无权限访问他人聊天记录")
    conn = get_conn()
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


# 3.3 获取最近一条
@app.get("/api/chat/<int:user_id>/latest")
@auth_required
def chat_latest(user_id: int):
    if g.user_id != user_id:
        log_action(g.user_id, "chat_latest_forbidden", "chat_history", str(user_id))
        return json_response(success=False, status=403, message="无权限访问他人聊天记录")
    conn = get_conn()
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
        log_action(g.user_id, "chat_latest_empty", "chat_history", str(user_id))
        return json_response(success=False, status=404, message="无聊天记录")
    row["created_at"] = isoformat(row["created_at"])
    row["updated_at"] = isoformat(row["updated_at"])
    log_action(g.user_id, "chat_latest", "chat_history", str(user_id), {"chat_id": row["chat_id"]})
    return jsonify(row), 200


# 3.4 获取最近 N 条
@app.get("/api/chat/<int:user_id>/recent")
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
    conn = get_conn()
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


# 3.5 更新聊天记录（上传文件 -> 永久存储 -> 回写 content_url）
@app.put("/api/chat/<int:chat_id>")
@auth_required
def chat_update(chat_id: int):
    if "file" not in request.files:
        log_action(g.user_id, "chat_update_bad_request", "chat_history", str(chat_id), {"reason": "missing file"})
        return json_response(success=False, status=400, message="缺少 file (FormData)")

    conn = get_conn()
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
        # 截断保护（content_url 列长 255）
        if len(new_url) > 255:
            raise RuntimeError("生成的 content_url 超过 255 字符")
    except Exception as e:
        log_action(g.user_id, "chat_update_upload_fail", "chat_history", str(chat_id), {"error": str(e)})
        return json_response(success=False, status=502, message=f"上传文件到文件服务器失败: {e}")

    with conn.cursor() as cur:
        cur.execute("UPDATE chat_history SET content_url=%s WHERE chat_id=%s", (new_url, chat_id))

    log_action(g.user_id, "chat_update", "chat_history", str(chat_id), {"content_url": new_url})
    return jsonify({"success": True, "chat_id": chat_id, "message": "聊天记录已更新"}), 200


# 3.6 删除聊天记录（仅删元数据；如需物理删除可在此解析 file_id 调 file_server 删除接口）
@app.delete("/api/chat/<int:chat_id>")
@auth_required
def chat_delete(chat_id: int):
    conn = get_conn()
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


# 健康检查
@app.get("/healthz")
def healthz():
    try:
        with get_conn().cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    # 生产建议将 debug=0
    app.run(host="0.0.0.0", port=7209, debug=bool(int(os.getenv("FLASK_DEBUG", "0"))))
