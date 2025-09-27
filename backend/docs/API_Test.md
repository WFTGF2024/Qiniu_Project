# 1.用户CRUD
## 1.1 用户注册 (Register)

curl -X POST http://localhost:8080/api/auth/register \
-H "Content-Type: application/json" \
-d '{
    "username": "test2",   
    "password": "password123",
    "email": "test2@example.com",
    "phone_number": "13800138000",
    "full_name": "Test User2",
    "security_question1": "你的小学名称是什么？",
    "security_answer1": "阳光小学",
    "security_question2": "你的出生城市是哪里？",
    "security_answer2": "北京"
}'

响应：
{"message":"注册成功","success":true,"user_id":3}

![alt text](UserRegister1.png)
![alt text](UserRegister2.png)

## 1.2 用户登录 (Login)

curl -X POST http://localhost:8080/api/auth/login \
-H "Content-Type: application/json" \
-d '{
    "username": "test2",   
    "password": "password123"
}'

响应：
{"expire_at":"2025-09-29T00:33:55+08:00","success":true,"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTkwNzcyMzUsInVzZXJfaWQiOjN9.zTtvTtZtE9EIUEtguJmznz7-SVDXw7IgJxOQ8xnUr1I"}%  

![alt text](UserLogin1.png)
![alt text](UserLogin2.png)

## 1.3 获取用户信息 (Get Profile)

curl -X GET http://localhost:8080/api/auth/me \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTkwNzcyNjEsInVzZXJfaWQiOjN9.ovN8LxVQJR384d-oKvR20Oz_MG1wwARFFIYjEA93mYc"

响应：
{"user_id":3,"username":"test2","full_name":"Test User2","email":"test2@example.com","phone_number":"13800138000","created_at":"2025-09-28T00:28:40.463+08:00","updated_at":"2025-09-28T00:28:40.463+08:00"}%  

![alt text](UserGetProfile1.png)
![alt text](UserGetProfile2.png)

## 1.4 更新用户信息 (Update User)

curl -X PUT http://localhost:8080/api/users/:3 \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTkwNzcyNjEsInVzZXJfaWQiOjN9.ovN8LxVQJR384d-oKvR20Oz_MG1wwARFFIYjEA93mYc" \
-H "Content-Type: application/json" \
-d '{
    "full_name": "test Update",
    "email": "updated@example.com",
    "phone_number": "13900139000"
}'

响应：
{"message":"用户信息已更新","success":true}%  

![alt text](UserUpdate1.png)
![alt text](UserUpdate2.png)


## 1.5 删除用户 (Delete User)

curl -X DELETE http://localhost:8080/api/users/:2 \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTkwNzcyNjEsInVzZXJfaWQiOjN9.ovN8LxVQJR384d-oKvR20Oz_MG1wwARFFIYjEA93mYc"

响应：
{"message":"用户已删除","success":true}%   

![alt text](UserDelete1.png)
![alt text](UserDelete2.png)


## 1.6 找回密码 - 验证密保 (Verify Security Questions)

curl -X POST http://localhost:8080/api/auth/verify-security \
-H "Content-Type: application/json" \
-d '{
    "username": "test2",
    "security_answer1": "阳光小学",
    "security_answer2": "北京"
}'

响应：
{"reset_token":"d5fd01d26cd944628a4c9614f9dd4bc9","success":true}%  

![alt text](UserVerify1.png)
![alt text](UserVerify2.png)

## 1.7 重置密码 (Reset Password)

curl -X POST http://localhost:8080/api/auth/reset-password \
-H "Content-Type: application/json" \
-d '{
    "reset_token": "4599bba20750045ad6f1a2115ce9a604",
    "new_password": "newpassword123"
}'

响应：
{"message":"密码重置失败","success":false}%    

![alt text](UserResetPwd1.png)
![alt text](UserResetPwd2.png)

ps. 这个接口后续还要改，暂不知道为什么会失败



# 2.会员CRUD

## 2.1 查询会员信息 (Get Membership Info)

curl -X GET http://localhost:8080/api/membership/4

响应：
{"membership_id":1,"user_id":4,"start_date":"2025-09-01T00:00:00+08:00","expire_date":"2026-09-01T00:00:00+08:00","status":"active"}%    

![alt text](MemberGetMembershipInfo1.png)
![alt text](MemberGetMembershipInfo2.png)


## 2.2 查询会员订单记录 (Get Membership Orders)
curl -X GET http://localhost:8080/api/membership/orders/1



## 2.3 新增会员信息 (Create Membership Info)

curl -X POST http://localhost:8080/api/membership \
-H "Content-Type: application/json" \
-d '{
    "user_id": 4,
    "start_date": "2025-09-01",
    "expire_date": "2026-09-01",
    "status": "active"
}'

响应：
{"membership_id":1,"message":"会员信息已创建","success":true}%  

![alt text](MemberCreateMembership1.png)
![alt text](MemberCreateMembership2.png)


## 2.4 查询所有会员信息 (Get All Memberships)

curl -X GET http://localhost:8080/api/membership

响应：
[{"membership_id":1,"user_id":4,"start_date":"2025-09-01T00:00:00+08:00","expire_date":"2026-09-01T00:00:00+08:00","status":"active"}]%    

![alt text](MemberGetAllMembership1.png)
![alt text](MemberGetAllMembership2.png)


## 2.5 更新会员信息 (Update Membership)

curl -X PUT http://localhost:8080/api/membership/1 \
-H "Content-Type: application/json" \
-d '{
    "expire_date": "2025-12-31",
    "status": "active"
}'

响应：
{"message":"会员信息已更新","success":true}%   

![alt text](MemberUpdateMembership1.png)
![alt text](MemberUpdateMembership2.png)


## 2.6 删除会员信息 (Delete Membership)

curl -X DELETE http://localhost:8080/api/membership/1

响应：
{"message":"会员信息已删除","success":true}%      

![alt text](MemberDeleteMembership1.png)
![alt text](MemberDeleteMembership2.png)


## 2.7 新增订单 (Create Order)
curl -X POST http://localhost:8080/api/membership/orders \
-H "Content-Type: application/json" \
-d '{
    "user_id": 1,
    "duration_months": 12,
    "amount": 299.00,
    "payment_method": "alipay",
    "membership_type": "premium"
}'


## 2.8 查询最近一条订单 (Get Latest Order)
curl -X GET http://localhost:8080/api/membership/orders/1/latest


## 2.9 查询最近 N 条订单
curl -X GET http://localhost:8080/api/membership/orders/1/recent?n=5
