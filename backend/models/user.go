package models

import "time"

// User 用户模型
type User struct {
	UserID              uint      `json:"user_id" gorm:"primaryKey"`
	Username            string    `json:"username" gorm:"unique;not null"`
	PasswordHash        string    `json:"-" gorm:"not null"` // 不在JSON中返回密码
	FullName            string    `json:"full_name"`
	Email               string    `json:"email" gorm:"unique;not null"`
	PhoneNumber         string    `json:"phone_number" gorm:"unique;not null"`
	SecurityQuestion1   string    `json:"security_question1"`
	SecurityAnswer1Hash string    `json:"-" gorm:"not null"` // 不在JSON中返回答案
	SecurityQuestion2   string    `json:"security_question2"`
	SecurityAnswer2Hash string    `json:"-" gorm:"not null"` // 不在JSON中返回答案
	CreatedAt           time.Time `json:"created_at"`
	UpdatedAt           time.Time `json:"updated_at"`
}

// UserRegisterRequest 用户注册请求
type UserRegisterRequest struct {
	Username          string `json:"username" binding:"required"`
	Password          string `json:"password" binding:"required"`
	FullName          string `json:"full_name"`
	Email             string `json:"email" binding:"required,email"`
	PhoneNumber       string `json:"phone_number" binding:"required"`
	SecurityQuestion1 string `json:"security_question1" binding:"required"`
	SecurityAnswer1   string `json:"security_answer1" binding:"required"`
	SecurityQuestion2 string `json:"security_question2" binding:"required"`
	SecurityAnswer2   string `json:"security_answer2" binding:"required"`
}

// UserLoginRequest 用户登录请求
type UserLoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// UserProfileResponse 用户信息响应
type UserProfileResponse struct {
	UserID      uint      `json:"user_id"`
	Username    string    `json:"username"`
	FullName    string    `json:"full_name"`
	Email       string    `json:"email"`
	PhoneNumber string    `json:"phone_number"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// UpdateUserRequest 更新用户信息请求
type UpdateUserRequest struct {
	FullName    string `json:"full_name"`
	Email       string `json:"email"`
	PhoneNumber string `json:"phone_number"`
}

// SecurityVerifyRequest 安全问题验证请求
type SecurityVerifyRequest struct {
	Username        string `json:"username" binding:"required"`
	SecurityAnswer1 string `json:"security_answer1" binding:"required"`
	SecurityAnswer2 string `json:"security_answer2" binding:"required"`
}

// ResetPasswordRequest 重置密码请求
type ResetPasswordRequest struct {
	ResetToken  string `json:"reset_token" binding:"required"`
	NewPassword string `json:"new_password" binding:"required"`
}
