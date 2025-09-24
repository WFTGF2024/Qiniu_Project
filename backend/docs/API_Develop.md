# 七牛云项目后端

## 项目概述

本项目是一个基于Go语言的后端服务，实现了用户CRUD、会员管理和聊天记录等功能。本项目使用Gin框架作为HTTP服务器，GORM作为ORM框架，MySQL作为数据库。项目采用分层架构设计，包括Handler层、Service层、Model层、Database层等，实现了业务逻辑与HTTP处理逻辑的分离，提高了代码的可维护性和可测试性。

## 项目结构

```
backend/
├── config/           # 配置文件
│   └── config.go     # 配置加载和管理，使用全局变量存储配置
├── database/         # 数据库连接和初始化
│   └── database.go   # 数据库连接和模型迁移，使用logrus记录日志
├── docs/             # 项目文档
│   ├── API.md        # API接口文档
│   ├── API_Develop.md # API开发文档
│   └── MySQL.sql     # 数据库初始化脚本
├── handlers/         # HTTP请求处理层
│   └── user_handler.go # 用户相关HTTP处理函数
├── middleware/       # 中间件
│   └── auth.go       # JWT认证中间件
├── models/           # 数据模型层
│   └── user.go       # 用户模型定义
├── services/         # 业务逻辑层
│   └── user_service.go # 用户相关业务逻辑
├── utils/            # 工具函数
│   └── utils.go      # 密码哈希、JWT等工具函数
└── main.go           # 主程序入口，负责初始化配置、日志系统和数据库连接
```

## 架构设计

本项目采用分层架构设计，实现了关注点分离：

1. **Handler层**：负责HTTP请求处理、参数解析、响应格式化和错误处理
2. **Service层**：负责业务逻辑处理、数据验证和业务规则实现
3. **Model层**：负责数据结构和数据关系定义
4. **Database层**：负责数据库连接和操作
5. **Middleware层**：负责横切关注点，如认证、日志记录等
6. **Utils层**：提供通用工具函数
7. **Config层**：负责配置管理

### 架构优势

- **职责分离**：每个层次有明确的职责，便于维护和理解
- **代码复用**：业务逻辑可以在多个地方复用
- **易于测试**：可以独立测试业务逻辑，不需要HTTP上下文
- **更好的扩展性**：添加新功能时，可以在不同层次进行扩展
- **更清晰的错误处理**：错误处理更加集中和一致

## 用户CRUD接口实现

本部分详细说明用户CRUD接口的实现逻辑，包括各个文件的功能和函数作用。

### 1. 数据模型层 (models/user.go)

`user.go`文件定义了用户相关的数据结构，包括：

- `User`结构体：对应数据库中的users表，包含用户ID、用户名、密码哈希、姓名、邮箱、手机号、密保问题和答案等字段。
- `UserRegisterRequest`结构体：用于处理用户注册请求，包含注册所需的所有字段。
- `UserLoginRequest`结构体：用于处理用户登录请求，包含用户名和密码。
- `UserProfileResponse`结构体：用于返回用户信息，不包含敏感信息如密码和密保答案。
- `UpdateUserRequest`结构体：用于处理用户信息更新请求。
- `SecurityVerifyRequest`结构体：用于处理密保问题验证请求。
- `ResetPasswordRequest`结构体：用于处理密码重置请求。

### 2. 业务逻辑层 (services/user_service.go)

`user_service.go`文件实现了用户相关的业务逻辑，采用接口设计模式：

- `UserService`接口：定义了用户相关的业务方法，包括注册、登录、获取用户信息、更新用户、删除用户、验证密保问题和重置密码等。
- `userService`结构体：实现了UserService接口，包含了具体的业务逻辑实现。
- `NewUserService()`函数：创建UserService实例，采用工厂模式。

#### 主要业务方法：

- `RegisterUser()`：处理用户注册业务逻辑，包括数据验证、重复检查、密码哈希和用户创建。
- `LoginUser()`：处理用户登录业务逻辑，包括用户查找、密码验证和JWT令牌生成。
- `GetUserProfile()`：获取用户信息，不包含敏感数据。
- `UpdateUser()`：更新用户信息，包括数据验证和重复检查。
- `DeleteUser()`：删除用户记录。
- `VerifySecurity()`：验证用户的密保问题答案。
- `ResetPassword()`：重置用户密码。

### 3. HTTP处理层 (handlers/user_handler.go)

`user_handler.go`文件实现了所有用户相关的HTTP处理函数，主要负责：

- 请求参数解析和验证
- 调用Service层处理业务逻辑
- 格式化响应数据
- 错误处理和日志记录

#### 主要处理函数：

- `Register()`：处理用户注册HTTP请求，调用`userService.RegisterUser()`方法。
- `Login()`：处理用户登录HTTP请求，调用`userService.LoginUser()`方法。
- `GetProfile()`：获取用户信息HTTP请求，调用`userService.GetUserProfile()`方法。
- `UpdateUser()`：更新用户信息HTTP请求，调用`userService.UpdateUser()`方法。
- `DeleteUser()`：删除用户HTTP请求，调用`userService.DeleteUser()`方法。
- `VerifySecurity()`：验证密保问题HTTP请求，调用`userService.VerifySecurity()`方法。
- `ResetPassword()`：重置密码HTTP请求，调用`userService.ResetPassword()`方法。

### 4. 配置管理 (config/config.go)

`config.go`文件负责统一管理应用程序配置：

- `Config`结构体：定义了应用程序所需的配置项，包括MySQL连接信息和服务器设置。
- `GlobalConfig`全局变量：存储已加载的配置，供整个应用程序使用。
- `LoadConfig()`函数：从指定路径加载YAML配置文件，并将配置存储到全局变量中。

### 5. 数据库连接 (database/database.go)

`database.go`文件负责数据库连接和初始化：

- `InitDB()`函数：初始化数据库连接，连接MySQL数据库并自动迁移模型到数据库表。
- `autoMigrate()`函数：使用GORM的AutoMigrate功能自动创建或更新数据库表。

### 6. 工具函数 (utils/utils.go)

`utils.go`文件提供了各种工具函数：

- `HashPassword()`：使用bcrypt算法对密码进行哈希加密，确保密码存储安全。
- `CheckPassword()`：验证用户输入的密码是否与数据库中存储的哈希值匹配。
- `GenerateJWTToken()`：生成JWT令牌，用于用户认证，包含用户ID和过期时间。
- `ParseJWTToken()`：解析JWT令牌并提取用户ID，用于验证用户身份。
- `GenerateResetToken()`：生成重置密码的令牌，用于密码重置功能。

### 7. 认证中间件 (middleware/auth.go)

`auth.go`文件实现了JWT认证中间件：

- `JWTAuthMiddleware()`函数：验证HTTP请求中的JWT令牌，提取用户ID并存储在上下文中，用于保护需要认证的API端点。

### 8. 主程序 (main.go)

`main.go`文件是程序的入口点，负责：

- 解析命令行参数，获取配置文件路径
- 初始化logrus日志系统，配置日志输出到文件
- 使用config包加载配置文件
- 初始化数据库连接
- 设置HTTP路由
- 启动HTTP服务器

`setupRouter()`函数：配置Gin路由，包括设置中间件、CORS支持、API路由分组等。

配置加载流程：
1. 通过命令行参数 `-r` 指定配置文件路径
2. 调用 `config.LoadConfig()` 加载配置
3. 配置信息存储在 `config.GlobalConfig` 中供全局使用
4. 数据库连接和其他组件使用全局配置变量

#### 架构初始化流程

1. **配置初始化**：`main.go`首先加载配置文件，并将配置存储在全局变量中
2. **日志系统初始化**：配置logrus日志系统，输出到文件并设置日志级别
3. **数据库连接初始化**：调用`database.InitDB()`建立数据库连接并执行模型迁移
4. **HTTP路由设置**：`setupRouter()`函数配置Gin路由，包括：
   - 全局中间件：日志中间件、恢复中间件、CORS中间件
   - 认证路由组：`/api/auth`，包括注册、登录、验证密保和重置密码等接口
   - 用户管理路由组：`/api/users`，包括获取、更新和删除用户等接口，需要JWT认证
5. **服务器启动**：在指定端口启动HTTP服务器

#### 分层协作

- **Handler层**通过依赖注入使用Service层，如`userService := services.NewUserService()`
- **Service层**通过依赖注入使用Database层和Utils层，如`database.DB`和`utils.HashPassword()`
- **Database层**使用Config层的配置信息建立数据库连接
- **Middleware层**作为横切关注点，应用到特定的路由组上

## 接口文档

本项目的用户CRUD接口实现了API.md中"1.用户CRUD"部分的所有功能，采用分层架构设计，实现了业务逻辑与HTTP处理逻辑的分离：

### 认证接口

1. **用户注册** (POST /api/auth/register)
   - Handler层：`handlers.Register()`
   - Service层：`services.UserService.RegisterUser()`
   - 功能：创建新用户，验证数据唯一性，哈希密码和密保答案

2. **用户登录** (POST /api/auth/login)
   - Handler层：`handlers.Login()`
   - Service层：`services.UserService.LoginUser()`
   - 功能：验证用户凭据，生成JWT令牌

3. **获取用户信息** (GET /api/auth/me)
   - Handler层：`handlers.GetProfile()`
   - Service层：`services.UserService.GetUserProfile()`
   - 功能：获取当前登录用户信息，需要JWT认证

4. **验证密保问题** (POST /api/auth/verify-security)
   - Handler层：`handlers.VerifySecurity()`
   - Service层：`services.UserService.VerifySecurity()`
   - 功能：验证用户的密保问题答案，生成重置令牌

5. **重置密码** (POST /api/auth/reset-password)
   - Handler层：`handlers.ResetPassword()`
   - Service层：`services.UserService.ResetPassword()`
   - 功能：使用重置令牌更新用户密码

### 用户管理接口

6. **更新用户信息** (PUT /api/users/:user_id)
   - Handler层：`handlers.UpdateUser()`
   - Service层：`services.UserService.UpdateUser()`
   - 功能：更新用户信息，需要JWT认证

7. **删除用户** (DELETE /api/users/:user_id)
   - Handler层：`handlers.DeleteUser()`
   - Service层：`services.UserService.DeleteUser()`
   - 功能：删除用户记录，需要JWT认证

详细的接口请求和响应格式请参考API.md文件。

### 架构优势

通过引入Service层，我们实现了以下优势：

1. **关注点分离**：Handler层专注于HTTP处理，Service层专注于业务逻辑
2. **代码复用**：业务逻辑可以在多个地方复用，而不仅仅是HTTP接口
3. **易于测试**：可以独立测试业务逻辑，不需要HTTP上下文
4. **更好的扩展性**：添加新功能时，可以在不同层次进行扩展
5. **更清晰的错误处理**：错误处理更加集中和一致

## 运行项目

1. 确保已安装Go 1.17.13版本
2. 确保MySQL数据库已启动并创建了Qiniu_Project数据库
3. 根据实际情况修改config.yaml中的数据库连接信息和服务器设置
4. 运行`go mod tidy`安装依赖
5. 运行`go run main.go -r /path/to/config.yaml`启动服务器，其中`/path/to/config.yaml`是配置文件的完整路径

配置文件格式示例：
```yaml
mysql:
  host: localhost
  port: 3306
  user: root
  password: yourpassword
  database: Qiniu_Project
app_log_file: logs/app.log
server_port: 8080
```

日志系统配置：
- 日志输出到文件，路径由配置文件中的`app_log_file`指定
- 日志格式为JSON格式，便于日志分析工具处理
- 日志级别为Info，记录关键操作和错误信息
