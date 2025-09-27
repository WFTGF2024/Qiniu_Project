package models

import (
	"time"
)

// MembershipInfo 会员信息模型
type MembershipInfo struct {
	MembershipID uint      `json:"membership_id" gorm:"primaryKey"`
	UserID       uint      `json:"user_id" gorm:"not null"`
	StartDate    string    `json:"start_date" gorm:"type:date;not null"`
	ExpireDate   string    `json:"expire_date" gorm:"type:date;not null"`
	Status       string    `json:"status" gorm:"type:enum('active','expired');default:'active'"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

// CreateMembershipRequest 创建会员信息请求
type CreateMembershipRequest struct {
	UserID     uint   `json:"user_id" binding:"required"`
	StartDate  string `json:"start_date" binding:"required"`
	ExpireDate string `json:"expire_date" binding:"required"`
	Status     string `json:"status" binding:"required"`
}

// UpdateMembershipRequest 更新会员信息请求
type UpdateMembershipRequest struct {
	ExpireDate string `json:"expire_date"`
	Status     string `json:"status"`
}

// MembershipResponse 会员信息响应
type MembershipResponse struct {
	MembershipID uint   `json:"membership_id"`
	UserID       uint   `json:"user_id"`
	StartDate    string `json:"start_date"`
	ExpireDate   string `json:"expire_date"`
	Status       string `json:"status"`
}

// MembershipOrder 会员订单模型
type MembershipOrder struct {
	OrderID         uint      `json:"order_id" gorm:"primaryKey"`
	UserID          uint      `json:"user_id" gorm:"not null"`
	PurchaseDate    time.Time `json:"purchase_date"`
	DurationMonths  int       `json:"duration_months" gorm:"not null"`
	Amount          float64   `json:"amount" gorm:"type:decimal(10,2);not null"`
	PaymentMethod   string    `json:"payment_method" gorm:"type:enum('alipay','wechat','card','other');default:'other'"`
	CreatedAt       time.Time `json:"created_at"`
}

// CreateOrderRequest 创建订单请求
type CreateOrderRequest struct {
	UserID         uint    `json:"user_id" binding:"required"`
	DurationMonths int     `json:"duration_months" binding:"required"`
	Amount         float64 `json:"amount" binding:"required"`
	PaymentMethod string  `json:"payment_method" binding:"required"`
}

// OrderResponse 订单响应
type OrderResponse struct {
	OrderID        uint      `json:"order_id"`
	UserID         uint      `json:"user_id"`
	PurchaseDate   time.Time `json:"purchase_date"`
	DurationMonths int       `json:"duration_months"`
	Amount         float64   `json:"amount"`
	PaymentMethod  string    `json:"payment_method"`
}
