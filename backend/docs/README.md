这里存放后端代码，Go代码由高俊编写，接口文档由朱佳鸿编写。

# 任务完成情况（完成请打勾，按顺序完成）
- 身份认证CRUD
- 聊天记录CRUD
- 会员CRUD

# 后端API接口

[请狠狠读我](API.md)

# 注意事项
1. 用户的密码请用密文存储，不要明文存储。
2. 登录后才能使用的API都需要在Header中包含`Authorization: Bearer <jwt_token>`，其中`<jwt_token>`是用户登录后获取的token。
3. 无状态的API不包含`Authorization` Header。

# 数据库
**数据库名**：Qiniu_Project
**用户名**：Qiniu
**密码**: 20250922

