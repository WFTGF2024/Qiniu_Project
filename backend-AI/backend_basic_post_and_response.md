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






