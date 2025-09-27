-- MySQL数据库表结构设计
-- 用户表
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,      -- 用户唯一ID
    username VARCHAR(50) NOT NULL UNIQUE,        -- 用户账号
    password_hash VARCHAR(255) NOT NULL,         -- 加密后的密码（推荐哈希存储）
    full_name VARCHAR(100),                      -- 用户姓名
    email VARCHAR(100) NOT NULL UNIQUE,          -- 邮箱
    phone_number VARCHAR(20) NOT NULL UNIQUE,    -- 电话号码
    security_question1 VARCHAR(255) NOT NULL,    -- 密保问题1
    security_answer1_hash VARCHAR(255) NOT NULL, -- 密保答案1（建议哈希存储）
    security_question2 VARCHAR(255) NOT NULL,    -- 密保问题2
    security_answer2_hash VARCHAR(255) NOT NULL, -- 密保答案2（建议哈希存储）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP -- 更新时间
);

-- 会员信息表
CREATE TABLE membership_info (
    membership_id INT AUTO_INCREMENT PRIMARY KEY,    -- 会员信息ID
    user_id INT NOT NULL,                            -- 对应用户ID
    start_date DATE NOT NULL,                        -- 会员开始时间
    expire_date DATE NOT NULL,                       -- 会员到期时间
    status ENUM('active','expired') DEFAULT 'active',-- 当前状态
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 会员购买订单表
CREATE TABLE membership_orders (
    order_id BIGINT AUTO_INCREMENT PRIMARY KEY,   -- 订单ID
    user_id INT NOT NULL,                         -- 用户ID
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 购买时间
    duration_months INT NOT NULL,                 -- 购买的会员时长（月）
    amount DECIMAL(10,2) NOT NULL,                -- 支付金额
    payment_method ENUM('alipay','wechat','card','other') DEFAULT 'other', -- 支付方式
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 聊天记录表
CREATE TABLE chat_history (
    chat_id BIGINT AUTO_INCREMENT PRIMARY KEY,    -- 聊天记录唯一ID
    user_id INT NOT NULL,                         -- 对应用户ID
    record_id VARCHAR(64) NOT NULL UNIQUE,        -- 聊天记录ID（可用UUID生成，避免重复）
    content_url VARCHAR(255) NOT NULL,            -- 聊天记录存储的URL（可指向文件/对象存储）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 聊天开始时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 最近更新时间
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE user_files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(255) NOT NULL,
    size BIGINT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
