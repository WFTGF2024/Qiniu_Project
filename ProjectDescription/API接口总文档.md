此处介绍API的各个部署端口
## 服务部署端口
- **Embedding**:7202
- **ASR**:7205
- **TTS**:7206
- **LLM**:7207
- **VL**:7208
- **Web Search**:5080 (需要先部署容器才能部署)
- **File Server**:7201
- **basic backen**:7210

## 容器部署端口
- **postgreSQL**:5432
- **Qdrant**:6333
- **mySQL**:3306

## 文件服务器
这个部分可有可无，我把它独立了出来。如果公网服务器本身可以支持通过URL让别人下载文件，这一个可以省略。

由于部署AI后端的GPU服务器费用较高，按量付费。文件这部分也较为独立，把文件服务器放在CPU服务器上节省开销。

这部分也可以使用云服务提供商提供的对象存储服务，比如七牛云，阿里云OSS等实现。
### 1. 上传文件 `test.wav`

```cmd
curl -X POST http://127.0.0.1:7201/upload/2 -F "file=@test.wav"
```


```json
{
  "filename": "test.wav",
  "message": "File uploaded successfully"
}
```

---

### 2. 查看用户 2 的所有文件

```cmd
curl -X GET http://127.0.0.1:7201/files/2
```


```json
[
  {
    "file_id": 1,
    "filename": "test.wav"
  }
]

```


### 3. 下载文件（设`file_id=2`）

```cmd
curl -X GET http://127.0.0.1:7201/download/1 -o downloaded_test.wav
```
会把文件保存为 `downloaded_test.wav`。

### 4. 删除文件（设 `file_id=1`）

```cmd
curl -X DELETE http://127.0.0.1:7201/files/1
```

```json
{"message": "File deleted successfully"}
```


### 5. 批量上传多个文件

```cmd
curl -X POST http://127.0.0.1:7201/upload/2 -F "file=@test.wav" -F "file=@readme.txt"
```

下面给你一套**Windows CMD 环境**可直接粘贴运行的 `curl` 测试脚本示例（默认后端监听 `http://localhost:7210`）。
先手动把登录返回的 `token` 复制到 `%TOKEN%` 环境变量里再测需要鉴权的接口。

---

## 0) 预设变量（CMD）

```bat
REM ===== 基础变量 =====
set BASE=http://localhost:7210

REM 登录后把 JWT 粘贴到这里（只包含长长的一串 token，不要包含“Bearer ”前缀）
set TOKEN=PASTE_YOUR_JWT_TOKEN_HERE

REM 通用 JSON 头
set JSONHDR=Content-Type: application/json
```

---

## A. core（用户 / 认证 / 会员 / 订单）——无前缀

### 1) 注册

```bat
curl -X POST "%BASE%/api/auth/register" -H "%JSONHDR%" -d "{\"username\":\"alice\",\"password\":\"Passw0rd!\",\"full_name\":\"Alice Zhang\",\"email\":\"alice@example.com\",\"phone_number\":\"13800000000\",\"security_question1\":\"Q1\",\"security_answer1\":\"A1\",\"security_question2\":\"Q2\",\"security_answer2\":\"A2\"}"
```

### 2) 登录（复制响应中的 `token` 到 `%TOKEN%`）

```bat
curl -X POST "%BASE%/api/auth/login" -H "%JSONHDR%" -d "{\"username\":\"alice\",\"password\":\"Passw0rd!\"}"
```

### 3) 获取当前用户信息

```bat
curl -X GET "%BASE%/api/auth/me" -H "Authorization: Bearer %TOKEN%"
```

### 4) 更新用户信息

```bat
curl -X PUT "%BASE%/api/users/1" -H "%JSONHDR%" -H "Authorization: Bearer %TOKEN%" -d "{\"full_name\":\"Alice Z.\",\"email\":\"alicez@example.com\",\"phone_number\":\"13900000000\"}"
```

### 5) 删除用户

```bat
curl -X DELETE "%BASE%/api/users/1" -H "Authorization: Bearer %TOKEN%"
```

### 6) 校验密保 → 获取重置令牌

```bat
curl -X POST "%BASE%/api/auth/verify-security" -H "%JSONHDR%" -d "{\"username\":\"alice\",\"security_answer1\":\"A1\",\"security_answer2\":\"A2\"}"
```

### 7) 使用重置令牌重置密码

```bat
REM 将上一步响应中的 reset_token 替换到下行 JSON 里
curl -X POST "%BASE%/api/auth/reset-password" -H "%JSONHDR%" -d "{\"reset_token\":\"PASTE_RESET_TOKEN\",\"new_password\":\"NewPassw0rd!\"}"
```

### 8) 会员信息：创建 / 获取 / 列表 / 更新 / 删除

```bat
REM 创建
curl -X POST "%BASE%/api/membership" -H "%JSONHDR%" -H "Authorization: Bearer %TOKEN%" -d "{\"user_id\":1,\"start_date\":\"2025-10-01\",\"expire_date\":\"2026-09-30\",\"status\":\"active\"}"

REM 按用户获取最近一条
curl -X GET "%BASE%/api/membership/1" -H "Authorization: Bearer %TOKEN%"

REM 全量列表
curl -X GET "%BASE%/api/membership" -H "Authorization: Bearer %TOKEN%"

REM 更新（把 membership_id 换成实际返回的值）
curl -X PUT "%BASE%/api/membership/1001" -H "%JSONHDR%" -H "Authorization: Bearer %TOKEN%" -d "{\"status\":\"expired\"}"

REM 删除
curl -X DELETE "%BASE%/api/membership/1001" -H "Authorization: Bearer %TOKEN%"
```

### 9) 订单：创建 / 最近一条 / 最近 N 条

```bat
REM 创建订单
curl -X POST "%BASE%/api/membership/orders" -H "%JSONHDR%" -H "Authorization: Bearer %TOKEN%" -d "{\"user_id\":1,\"duration_months\":12,\"amount\":199.0,\"payment_method\":\"alipay\"}"

REM 最近一条订单
curl -X GET "%BASE%/api/membership/orders/1/latest" -H "Authorization: Bearer %TOKEN%"

REM 最近 N 条（示例 N=5）
curl -X GET "%BASE%/api/membership/orders/1/recent?n=5" -H "Authorization: Bearer %TOKEN%"
```

### 10) 健康检查（core）

```bat
curl -X GET "%BASE%/healthz"
```

---

## B. chat（聊天记录 + 文件永久化）——前缀 `/chat`

### 1) 保存（或幂等更新）聊天记录元数据

```bat
curl -X POST "%BASE%/chat/api/chat/save" -H "%JSONHDR%" -H "Authorization: Bearer %TOKEN%" -d "{\"user_id\":1,\"record_id\":\"rec_20250928_0001\",\"content_url\":\"http://files.local/chatlogs/rec_20250928_0001.json\"}"
```

### 2) 列出用户聊天记录

```bat
curl -X GET "%BASE%/chat/api/chat/1" -H "Authorization: Bearer %TOKEN%"
```

### 3) 获取最近一条

```bat
curl -X GET "%BASE%/chat/api/chat/1/latest" -H "Authorization: Bearer %TOKEN%"
```

### 4) 获取最近 N 条

```bat
curl -X GET "%BASE%/chat/api/chat/1/recent?n=10" -H "Authorization: Bearer %TOKEN%"
```

### 5) 更新聊天记录并上传文件到永久存储（`FormData`）

```bat
REM 将路径替换为你的本地文件路径
curl -X PUT "%BASE%/chat/api/chat/1234" -H "Authorization: Bearer %TOKEN%" -F "file=@C:\path\to\chat_1234.json"
```

### 6) 删除聊天记录

```bat
curl -X DELETE "%BASE%/chat/api/chat/1234" -H "Authorization: Bearer %TOKEN%"
```

### 7) 健康检查（chat）

```bat
curl -X GET "%BASE%/chat/healthz"
```

---

## C. web（抓取 / 切块 / 向量入库）——前缀 `/web`

### 1) 单条抓取入库

```bat
curl -X POST "%BASE%/web/ingest" -H "%JSONHDR%" -d "{\"url\":\"https://example.com\"}"
```

### 2) 批量抓取入库

```bat
curl -X POST "%BASE%/web/bulk_ingest" -H "%JSONHDR%" -d "{\"urls\":[\"https://example.com\",\"https://www.python.org/\"]}"
```

### 3) 健康检查（web）

```bat
curl -X GET "%BASE%/web/health"
```

---

### 使用提示

* Windows CMD 里 JSON 需要使用双引号，内部引号用 `\"` 转义，示例里已处理。
* 需要鉴权的请求都加：`-H "Authorization: Bearer %TOKEN%"`。登录后把 token 贴到 `set TOKEN=...` 即可。
* `PUT /chat/api/chat/{chat_id}` 上传文件使用 `-F "file=@绝对路径"`，CMD 不支持 `~` 展开，请写完整盘符路径。
# <font color="red">1.用户CRUD</font>
## 1.1 用户注册 (Register)
**Endpoint**: `POST /api/auth/register`
**输入**:

```json
{
  "username": "alice123",
  "password": "plain_password",
  "full_name": "Alice Zhang",
  "email": "alice@example.com",
  "phone_number": "13800001234",
  "security_question1": "你母亲的名字？",
  "security_answer1": "hashed_answer1",
  "security_question2": "你小学的名字？",
  "security_answer2": "hashed_answer2"
}
```

**输出**:

```json
{
  "success": true,
  "user_id": 1001,
  "message": "注册成功"
}
```



## 1.2 用户登录 (Login)

**Endpoint**: `POST /api/auth/login`
**输入**:

```json
{
  "username": "alice123",
  "password": "plain_password"
}
```

**输出**:

```json
{
  "success": true,
  "token": "jwt_token_string",
  "user_id": 1001,
  "expire_at": "2025-09-30T10:00:00Z"
}
```

## 1.3 获取用户信息 (Get Profile)

**Endpoint**: `GET /api/auth/me`
**Header**: `Authorization: Bearer <jwt_token>`

**输出**:

```json
{
  "user_id": 1001,
  "username": "alice123",
  "full_name": "Alice Zhang",
  "email": "alice@example.com",
  "phone_number": "13800001234",
  "created_at": "2025-09-20T12:00:00Z",
  "updated_at": "2025-09-22T14:00:00Z"
}
```
## 1.4 更新用户信息 (Update User)

`PUT /api/users/:user_id`

**输入**:

```json
{
  "full_name": "Alice Z.",
  "email": "alice_new@example.com",
  "phone_number": "13800009999"
}
```

**输出**:

```json
{
  "success": true,
  "message": "用户信息已更新"
}
```

## 1.5 删除用户 (Delete User)

`DELETE /api/users/:user_id`

**输出**:

```json
{
  "success": true,
  "message": "用户已删除"
}
```


## 1.6 找回密码 - 验证密保 (Verify Security Questions)

**Endpoint**: `POST /api/auth/verify-security`
**输入**:

```json
{
  "username": "alice123",
  "security_answer1": "hashed_answer1",
  "security_answer2": "hashed_answer2"
}
```

**输出**:

```json
{
  "success": true,
  "reset_token": "reset_token_string"
}
```


## 1.7 重置密码 (Reset Password)

**Endpoint**: `POST /api/auth/reset-password`
**输入**:

```json
{
  "reset_token": "reset_token_string",
  "new_password": "new_secure_password"
}
```

**输出**:

```json
{
  "success": true,
  "message": "密码已更新"
}
```



# <font color="red">2.会员CRUD</font>
## 2.1 查询会员信息 (Get Membership Info)

**Endpoint**: `GET /api/membership/:user_id`

**输出**:

```json
{
  "membership_id": 2001,
  "user_id": 1001,
  "start_date": "2025-09-01",
  "expire_date": "2026-09-01",
  "status": "active"
}
```


## 2.2 查询会员订单记录 (Get Membership Orders)

**Endpoint**: `GET /api/membership/orders/:user_id`

**输出**:

```json
[
  {
    "order_id": 3001,
    "purchase_date": "2025-09-01T10:30:00Z",
    "duration_months": 12,
    "amount": 199.99,
    "payment_method": "wechat"
  },
  {
    "order_id": 3002,
    "purchase_date": "2024-09-01T10:30:00Z",
    "duration_months": 12,
    "amount": 199.99,
    "payment_method": "alipay"
  }
]
```
## 2.3 新增会员信息 (Create Membership Info)

`POST /api/membership`

**输入**:

```json
{
  "user_id": 1001,
  "start_date": "2025-09-01",
  "expire_date": "2026-09-01",
  "status": "active"
}
```

**输出**:

```json
{
  "success": true,
  "membership_id": 2001,
  "message": "会员信息已创建"
}
```

---

## 2.4 查询所有会员信息 (Get All Memberships)

`GET /api/membership`

**输出**:

```json
[
  {
    "membership_id": 2001,
    "user_id": 1001,
    "start_date": "2025-09-01",
    "expire_date": "2026-09-01",
    "status": "active"
  },
  {
    "membership_id": 2002,
    "user_id": 1002,
    "start_date": "2025-07-01",
    "expire_date": "2026-07-01",
    "status": "active"
  }
]
```


## 2.5 更新会员信息 (Update Membership)

`PUT /api/membership/:membership_id`

**输入**:

```json
{
  "expire_date": "2026-12-01",
  "status": "active"
}
```

**输出**:

```json
{
  "success": true,
  "message": "会员信息已更新"
}
```

---

## 2.6 删除会员信息 (Delete Membership)

`DELETE /api/membership/:membership_id`

**输出**:

```json
{
  "success": true,
  "message": "会员信息已删除"
}
```



## 2.7 新增订单 (Create Order)

`POST /api/membership/orders`

**输入**:

```json
{
  "user_id": 1001,
  "duration_months": 12,
  "amount": 199.99,
  "payment_method": "wechat"
}
```

**输出**:

```json
{
  "success": true,
  "order_id": 3001,
  "message": "订单已创建"
}
```


## 2.8 查询最近一条订单 (Get Latest Order)

`GET /api/membership/orders/:user_id/latest`

**输出**:

```json
{
  "order_id": 3001,
  "user_id": 1001,
  "purchase_date": "2025-09-01T10:30:00Z",
  "duration_months": 12,
  "amount": 199.99,
  "payment_method": "wechat"
}
```

---

## 2.9 查询最近 N 条订单

`GET /api/membership/orders/:user_id/recent?n=5`

**输出**:

```json
[
  {
    "order_id": 3001,
    "purchase_date": "2025-09-01T10:30:00Z",
    "duration_months": 12,
    "amount": 199.99,
    "payment_method": "wechat"
  },
  {
    "order_id": 3002,
    "purchase_date": "2024-09-01T10:30:00Z",
    "duration_months": 12,
    "amount": 199.99,
    "payment_method": "alipay"
  }
]
```

#  <font color="red">3.聊天记录CRUD</font>

## 3.1 聊天记录保存 (Save Chat Record)

**Endpoint**: `POST /api/chat/save`
**输入**:

```json
{
  "user_id": 1001,
  "record_id": "uuid_12345",
  "content_url": "https://oss.example.com/chats/uuid_12345.json"
}
```

**输出**:

```json
{
  "success": true,
  "chat_id": 4001,
  "message": "聊天记录已保存"
}
```


## 3.2 获取聊天记录 (Get Chat History)

**Endpoint**: `GET /api/chat/:user_id`

**输出**:

```json
[
  {
    "chat_id": 4001,
    "record_id": "uuid_12345",
    "content_url": "https://oss.example.com/chats/uuid_12345.json",
    "created_at": "2025-09-23T12:30:00Z",
    "updated_at": "2025-09-23T12:40:00Z"
  }
]
```





## 3.3 获取最近一条聊天记录

`GET /api/chat/:user_id/latest`

**输出**:

```json
{
  "chat_id": 4001,
  "record_id": "uuid_12345",
  "content_url": "https://oss.example.com/chats/uuid_12345.json",
  "created_at": "2025-09-23T12:30:00Z",
  "updated_at": "2025-09-23T12:40:00Z"
}
```


## 3.4 获取最近 N 条聊天记录

`GET /api/chat/:user_id/recent?n=10`

**输出**:

```json
[
  {
    "chat_id": 4001,
    "record_id": "uuid_12345",
    "content_url": "https://oss.example.com/chats/uuid_12345.json",
    "created_at": "2025-09-23T12:30:00Z",
    "updated_at": "2025-09-23T12:40:00Z"
  },
  {
    "chat_id": 4002,
    "record_id": "uuid_12346",
    "content_url": "https://oss.example.com/chats/uuid_12346.json",
    "created_at": "2025-09-22T11:20:00Z",
    "updated_at": "2025-09-22T11:40:00Z"
  }
]
```



## 3.5 更新聊天记录 (Update Chat Record)

`PUT /api/chat/:chat_id`

**输入**:

```json
FormData:
- file: <本地文件>   # 聊天记录文件，比如 JSON/TXT
```

**输出**:

```json
{
  "success": true,
  "chat_id": 4001,
  "message": "聊天记录已更新"
}
```


## 3.6 删除聊天记录 (Delete Chat Record)

`DELETE /api/chat/:chat_id`

**输出**:

```json
{
  "success": true,
  "message": "聊天记录已删除"
}
```






