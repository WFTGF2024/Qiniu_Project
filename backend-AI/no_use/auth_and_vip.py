# app.py
# -*- coding: utf-8 -*-
"""
Flask 单文件实现：用户CRUD + 会员CRUD + 订单接口 + 密保找回密码
- MySQL 连接使用 PyMySQL
- 密码 & 密保答案使用 werkzeug.security 哈希
- 鉴权使用 JWT（PyJWT）
- 简单动作审计日志写入 user_action_logs（可按需关闭）

运行方式：
1) pip install flask pyjwt werkzeug pymysql python-dotenv flask-cors
2) python app.py
3) 默认监听 http://127.0.0.1:5000

生产注意：
- 请将 SECRET_KEY 改为更安全的随机值或通过环境变量注入
- 数据库账号请使用受限权限（最小权限原则）
- 对外务必加 HTTPS、限流、CSRF/暴力破解防护、输入校验与错误隐藏
"""

import os
import json
import datetime as dt
from functools import wraps

import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# 配置
# =========================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "120.79.25.184"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "Qiniu"),
    "password": os.getenv("DB_PASSWORD", "20250922"),
    "database": os.getenv("DB_NAME", "Qiniu_Project"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": True,
}

SECRET_KEY = os.getenv("SECRET_KEY", "PLEASE_CHANGE_ME_TO_A_RANDOM_SECRET")
ACCESS_TOKEN_TTL_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "120"))  # 登录JWT有效期（分钟）
RESET_TOKEN_TTL_MIN = int(os.getenv("RESET_TOKEN_TTL_MIN", "15"))     # 重置JWT有效期（分钟）
ISSUER = os.getenv("JWT_ISS", "qiniu-project")

ENABLE_ACTION_LOG = True  # 是否写 user_action_logs

# =========================
# 应用
# =========================
app = Flask(__name__)
CORS(app)


# =========================
# 数据库连接管理
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
# 工具函数
# =========================
def json_response(data=None, success=True, status=200, **kwargs):
    payload = {"success": success}
    if data is not None:
        payload.update(data if isinstance(data, dict) else {"data": data})
    payload.update(kwargs)
    return jsonify(payload), status

def now_utc():
    return dt.datetime.utcnow()

def isoformat(ts: dt.datetime):
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def make_jwt(sub: str, ttl_minutes: int, token_type: str = "access", extra_claims: dict | None = None):
    exp = now_utc() + dt.timedelta(minutes=ttl_minutes)
    claims = {
        "iss": ISSUER,
        "sub": str(sub),
        "exp": exp,
        "iat": now_utc(),
        "type": token_type,
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, SECRET_KEY, algorithm="HS256")
    return token, exp

def decode_jwt(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"require": ["exp", "iat", "iss", "sub"]})

def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return json_response(success=False, status=401, message="缺少或非法的Authorization头")
        token = auth.split(" ", 1)[1].strip()
        try:
            claims = decode_jwt(token)
            if claims.get("type") != "access":
                return json_response(success=False, status=401, message="令牌类型错误")
            g.user_id = int(claims["sub"])
            g.jwt_claims = claims
        except jwt.ExpiredSignatureError:
            return json_response(success=False, status=401, message="令牌已过期")
        except jwt.InvalidTokenError:
            return json_response(success=False, status=401, message="无效令牌")
        return f(*args, **kwargs)
    return wrapper

def log_action(user_id, action_type, resource_type, resource_id, extra=None):
    if not ENABLE_ACTION_LOG:
        return
    try:
        conn = get_conn()
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
        # 审计日志失败不影响主流程
        pass

def get_user_by_username(username: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        return cur.fetchone()

def get_user_by_id(user_id: int):
    conn = get_conn()
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


# =========================
# 1. 用户 CRUD & 认证
# =========================

# 1.1 注册
@app.post("/api/auth/register")
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

    conn = get_conn()
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
            # 可能是邮箱/手机号唯一索引冲突
            msg = "唯一性约束冲突（用户名/邮箱/手机号已存在）"
            return json_response(success=False, status=409, message=msg, error=str(e))

    log_action(user_id, "register", "user", user_id, {"username": username})
    return jsonify({"success": True, "user_id": user_id, "message": "注册成功"}), 201


# 1.2 登录
@app.post("/api/auth/login")
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


# 1.3 获取个人信息
@app.get("/api/auth/me")
@auth_required
def me():
    user = get_user_by_id(g.user_id)
    if not user:
        return json_response(success=False, status=404, message="用户不存在")
    return jsonify(public_user_view(user))


# 1.4 更新用户信息
@app.put("/api/users/<int:user_id>")
@auth_required
def update_user(user_id: int):
    # 简单授权：仅本人可改（可扩展为管理员策略）
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限修改其他用户")

    data = request.get_json(force=True, silent=True) or {}
    allow = ["full_name", "email", "phone_number"]
    updates = {k: data[k] for k in allow if k in data}

    if not updates:
        return json_response(success=False, status=400, message="无可更新字段")

    sets = ", ".join([f"{k}=%s" for k in updates])
    params = list(updates.values()) + [user_id]

    conn = get_conn()
    with conn.cursor() as cur:
        try:
            cur.execute(f"UPDATE users SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s", params)
            if cur.rowcount == 0:
                return json_response(success=False, status=404, message="用户不存在")
        except pymysql.err.IntegrityError as e:
            return json_response(success=False, status=409, message="唯一性约束冲突", error=str(e))

    log_action(user_id, "update", "user", user_id, {"fields": list(updates.keys())})
    return jsonify({"success": True, "message": "用户信息已更新"})


# 1.5 删除用户
@app.delete("/api/users/<int:user_id>")
@auth_required
def delete_user(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限删除其他用户")

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        if cur.rowcount == 0:
            return json_response(success=False, status=404, message="用户不存在")

    log_action(user_id, "delete", "user", user_id)
    return jsonify({"success": True, "message": "用户已删除"})


# 1.6 找回密码 - 验证密保
@app.post("/api/auth/verify-security")
def verify_security():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    ans1 = data.get("security_answer1", "")
    ans2 = data.get("security_answer2", "")

    user = get_user_by_username(username)
    # 安全提示：不暴露用户是否存在
    if not user:
        # 与验证失败保持同一响应
        return json_response(success=False, status=401, message="验证失败")

    ok1 = check_password_hash(user["security_answer1_hash"], ans1)
    ok2 = check_password_hash(user["security_answer2_hash"], ans2)
    if not (ok1 and ok2):
        return json_response(success=False, status=401, message="验证失败")

    reset_token, _ = make_jwt(user["user_id"], RESET_TOKEN_TTL_MIN, token_type="reset")
    log_action(user["user_id"], "verify_security", "user", user["user_id"])
    return jsonify({"success": True, "reset_token": reset_token})


# 1.7 重置密码
@app.post("/api/auth/reset-password")
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
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET password_hash=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s", (pwd_hash, user_id))
        if cur.rowcount == 0:
            return json_response(success=False, status=404, message="用户不存在")

    log_action(user_id, "reset_password", "user", user_id)
    return jsonify({"success": True, "message": "密码已更新"})


# =========================
# 2. 会员 CRUD & 订单
# =========================

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

# 2.1 查询会员信息（按用户：返回最近更新的一条，若无则404）
@app.get("/api/membership/<int:user_id>")
@auth_required
def get_membership(user_id: int):
    # 简单授权：仅本人可查
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人会员信息")

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_info WHERE user_id=%s ORDER BY last_updated DESC, membership_id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="未找到会员信息")
    return jsonify(membership_view(row))


# 2.2 查询会员订单记录（按用户全部）
@app.get("/api/membership/orders/<int:user_id>")
@auth_required
def list_orders(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC",
            (user_id,)
        )
        rows = cur.fetchall()
    return jsonify([order_view(r) for r in rows])


# 2.3 新增会员信息
@app.post("/api/membership")
@auth_required
def create_membership():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "start_date", "expire_date", "status"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return json_response(success=False, status=400, message=f"缺少字段: {', '.join(missing)}")

    # 授权限制：仅本人可为自己建（可扩展管理员）
    if g.user_id != int(data["user_id"]):
        return json_response(success=False, status=403, message="无权限为他人创建会员")

    conn = get_conn()
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


# 2.4 查询所有会员信息（不做鉴权过滤；如需仅本人则可新增参数）
@app.get("/api/membership")
@auth_required
def list_all_memberships():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM membership_info ORDER BY last_updated DESC, membership_id DESC")
        rows = cur.fetchall()
    return jsonify([membership_view(r) for r in rows])


# 2.5 更新会员信息
@app.put("/api/membership/<int:membership_id>")
@auth_required
def update_membership(membership_id: int):
    data = request.get_json(force=True, silent=True) or {}
    allow = ["start_date", "expire_date", "status"]
    updates = {k: data[k] for k in allow if k in data}

    if not updates:
        return json_response(success=False, status=400, message="无可更新字段")

    conn = get_conn()
    with conn.cursor() as cur:
        # 先查到归属用户，做权限校验
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


# 2.6 删除会员信息
@app.delete("/api/membership/<int:membership_id>")
@auth_required
def delete_membership(membership_id: int):
    conn = get_conn()
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


# 2.7 新增订单
@app.post("/api/membership/orders")
@auth_required
def create_order():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "duration_months", "amount", "payment_method"]
    missing = [k for k in required if data.get(k) in (None, "")]
    if missing:
        return json_response(success=False, status=400, message=f"缺少字段: {', '.join(missing)}")

    if g.user_id != int(data["user_id"]):
        return json_response(success=False, status=403, message="无权限为他人创建订单")

    conn = get_conn()
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


# 2.8 查询最近一条订单
@app.get("/api/membership/orders/<int:user_id>/latest")
@auth_required
def latest_order(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return json_response(success=False, status=404, message="无订单记录")
    return jsonify(order_view(row))


# 2.9 查询最近 N 条订单（默认 5）
@app.get("/api/membership/orders/<int:user_id>/recent")
@auth_required
def recent_orders(user_id: int):
    if g.user_id != user_id:
        return json_response(success=False, status=403, message="无权限访问他人订单")
    try:
        n = int(request.args.get("n", "5"))
        n = max(1, min(n, 100))
    except ValueError:
        n = 5

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM membership_orders WHERE user_id=%s ORDER BY purchase_date DESC, order_id DESC LIMIT %s",
            (user_id, n)
        )
        rows = cur.fetchall()
    return jsonify([order_view(r) for r in rows])


# =========================
# 健康检查
# =========================
@app.get("/healthz")
def healthz():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# =========================
# 启动
# =========================
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "7210"))
    debug = bool(int(os.getenv("FLASK_DEBUG", "0")))
    app.run(host=host, port=port, debug=debug)
