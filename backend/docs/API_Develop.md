# 七牛云项目后端

## 项目概述

本项目是一个基于Go语言的后端服务，实现了用户CRUD、会员管理和聊天记录等功能。本项目使用Gin框架作为HTTP服务器，GORM作为ORM框架，MySQL作为数据库。

## 项目结构

```
backend/
├── database/          # 数据库连接和初始化
│   └── database.go   # 数据库连接和模型迁移
├── handlers/         # 请求处理函数
│   └── user_handler.go # 用户相关处理函数
├── middleware/       # 中间件
│   └── auth.go       # JWT认证中间件
├── models/           # 数据模型
│   └── user.go       # 用户模型
├── utils/            # 工具函数
│   └── utils.go      # 密码哈希、JWT等工具函数
└── main.go           # 主程序入口
```

## 用户CRUD接口实现

本部分详细说明用户CRUD接口的实现逻辑，包括各个文件的功能和函数作用。

### 1. 数据模型 (models/user.go)

`user.go`文件定义了用户相关的数据结构，包括：

- `User`结构体：对应数据库中的users表，包含用户ID、用户名、密码哈希、姓名、邮箱、手机号、密保问题和答案等字段。
- `UserRegisterRequest`结构体：用于处理用户注册请求，包含注册所需的所有字段。
- `UserLoginRequest`结构体：用于处理用户登录请求，包含用户名和密码。
- `UserProfileResponse`结构体：用于返回用户信息，不包含敏感信息如密码和密保答案。
- `UpdateUserRequest`结构体：用于处理用户信息更新请求。
- `SecurityVerifyRequest`结构体：用于处理密保问题验证请求。
- `ResetPasswordRequest`结构体：用于处理密码重置请求。

### 2. 数据库连接 (database/database.go)

`database.go`文件负责数据库连接和初始化：

- `InitDB()`函数：初始化数据库连接，连接MySQL数据库并自动迁移模型到数据库表。
- `loadConfig()`函数：从配置文件中加载MySQL连接信息。
- `autoMigrate()`函数：使用GORM的AutoMigrate功能自动创建或更新数据库表。

### 3. 工具函数 (utils/utils.go)

`utils.go`文件提供了各种工具函数：

- `HashPassword()`：使用bcrypt算法对密码进行哈希加密，确保密码存储安全。
- `CheckPassword()`：验证用户输入的密码是否与数据库中存储的哈希值匹配。
- `GenerateJWTToken()`：生成JWT令牌，用于用户认证，包含用户ID和过期时间。
- `ParseJWTToken()`：解析JWT令牌并提取用户ID，用于验证用户身份。
- `GenerateResetToken()`：生成重置密码的令牌，用于密码重置功能。

### 4. 认证中间件 (middleware/auth.go)

`auth.go`文件实现了JWT认证中间件：

- `JWTAuthMiddleware()`函数：验证HTTP请求中的JWT令牌，提取用户ID并存储在上下文中，用于保护需要认证的API端点。

### 5. 用户处理函数 (handlers/user_handler.go)

`user_handler.go`文件实现了所有用户相关的处理函数：

- `Register()`：处理用户注册请求，验证输入数据，检查用户名、邮箱和手机号是否已存在，哈希密码和密保答案，然后创建新用户。
- `Login()`：处理用户登录请求，验证用户名和密码，生成JWT令牌返回给客户端。
- `GetProfile()`：获取当前登录用户的信息，需要JWT认证。
- `UpdateUser()`：更新用户信息，需要JWT认证，验证邮箱和手机号是否已被其他用户使用。
- `DeleteUser()`：删除用户，需要JWT认证。
- `VerifySecurity()`：验证用户的密保问题答案，正确则生成重置密码令牌。
- `ResetPassword()`：使用重置令牌更新用户密码。

### 6. 主程序 (main.go)

`main.go`文件是程序的入口点，负责：

- 初始化日志系统
- 加载配置文件
- 初始化数据库连接
- 设置HTTP路由
- 启动HTTP服务器

`setupRouter()`函数：配置Gin路由，包括设置中间件、CORS支持、API路由分组等。

## 接口文档

本项目的用户CRUD接口实现了API.md中"1.用户CRUD"部分的所有功能，包括：

1. 用户注册 (POST /api/auth/register)
2. 用户登录 (POST /api/auth/login)
3. 获取用户信息 (GET /api/auth/me)
4. 更新用户信息 (PUT /api/users/:user_id)
5. 删除用户 (DELETE /api/users/:user_id)
6. 验证密保问题 (POST /api/auth/verify-security)
7. 重置密码 (POST /api/auth/reset-password)

详细的接口请求和响应格式请参考API.md文件。

## 运行项目

1. 确保已安装Go 1.17.13版本
2. 确保MySQL数据库已启动并创建了Qiniu_Project数据库
3. 根据实际情况修改config.yaml中的数据库连接信息
4. 运行`go mod tidy`安装依赖
5. 运行`go run main.go`启动服务器