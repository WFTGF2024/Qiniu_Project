package models

import "time"

// Membership 会员模型
type Membership struct {
	MembershipID   uint      `json:"membership_id" gorm:"primaryKey"`
	UserID         uint      `json:"user_id" gorm:"not null"`
	MembershipType string    `json:"membership_type" gorm:"not null"` // 如: "basic", "premium", "vip"
	StartDate      time.Time `json:"start_date"`
	EndDate        time.Time `json:"end_date"`
	Status         string    `json:"status" gorm:"not null"` // 如: "active", "expired"
	LastUpdated    time.Time `json:"last_updated"`
}

// Order 订单模型
type Order struct {
	OrderID        uint      `json:"order_id" gorm:"primaryKey"`
	UserID         uint      `json:"user_id" gorm:"not null"`
	PurchaseDate   time.Time `json:"purchase_date"`
	DurationMonths int       `json:"duration_months"`
	Amount         float64   `json:"amount"`
	PaymentMethod  string    `json:"payment_method"` // 如: "wechat", "alipay"
}

// CreateMembershipRequest 创建会员信息请求
type CreateMembershipRequest struct {
	MembershipType string    `json:"membership_type" binding:"required"` // 如: "basic", "premium", "vip"
	StartDate      time.Time `json:"start_date"`
	EndDate        time.Time `json:"end_date"`
	Status         string    `json:"status"` // 如: "active", "expired"
}

// CreateMembershipResponse 创建会员信息响应
type CreateMembershipResponse struct {
	MembershipID uint   `json:"membership_id"`
	Message      string `json:"message"`
}

// GetMembershipInfoRequest 查询会员信息请求
type GetMembershipInfoRequest struct {
	UserID uint `json:"user_id" binding:"required"`
}

// GetMembershipInfoResponse 查询会员信息响应
type GetMembershipInfoResponse struct {
	MembershipID   uint      `json:"membership_id"`
	UserID         uint      `json:"user_id"`
	MembershipType string    `json:"membership_type"`
	StartDate      time.Time `json:"start_date"`
	EndDate        time.Time `json:"end_date"`
	Status         string    `json:"status"`
}

// GetAllMembershipsRequest 查询所有会员信息请求
type GetAllMembershipsRequest struct {
}

// GetAllMembershipsResponse 查询所有会员信息响应
type GetAllMembershipsResponse struct {
	Memberships []Membership `json:"memberships"`
}

// UpdateMembershipRequest 更新会员信息请求
type UpdateMembershipRequest struct {
	MembershipID uint      `uri:"membership_id" binding:"required"`
	StartDate    time.Time `json:"start_date"`
	EndDate      time.Time `json:"end_date"`
	Status       string    `json:"status"`
}

// UpdateMembershipResponse 更新会员信息响应
type UpdateMembershipResponse struct {
	Message string `json:"message"`
}

// DeleteMembershipRequest 删除会员信息请求
type DeleteMembershipRequest struct {
	MembershipID uint `uri:"membership_id" binding:"required"`
}

// DeleteMembershipResponse 删除会员信息响应
type DeleteMembershipResponse struct {
	Message string `json:"message"`
}

// MembershipInfoResponse 会员信息响应 (兼容旧代码)
type MembershipInfoResponse struct {
	Membership Membership // 显式字段名
}

// CreateOrderRequest 创建订单请求
type CreateOrderRequest struct {
	UserID         uint    `json:"user_id" binding:"required"`
	DurationMonths int     `json:"duration_months" binding:"required"`
	Amount         float64 `json:"amount" binding:"required"`
	PaymentMethod  string  `json:"payment_method" binding:"required"` // 如: "wechat", "alipay"
}

// CreateOrderResponse 创建订单响应
type CreateOrderResponse struct {
	OrderID uint   `json:"order_id"`
	Message string `json:"message"`
}

// GetMembershipOrdersRequest 查询会员订单请求
type GetMembershipOrdersRequest struct {
	UserID uint `uri:"user_id" binding:"required"`
}

// GetMembershipOrdersResponse 查询会员订单响应
type GetMembershipOrdersResponse struct {
	Orders []Order `json:"orders"`
}

// GetLatestOrderRequest 查询最近一条订单请求
type GetLatestOrderRequest struct {
	UserID uint `uri:"user_id" binding:"required"`
}

// GetLatestOrderResponse 查询最近一条订单响应
type GetLatestOrderResponse struct {
	Order Order `json:"order"`
}

// GetRecentOrdersRequest 查询最近N条订单请求
type GetRecentOrdersRequest struct {
	UserID uint `uri:"user_id" binding:"required"`
	N      int  `form:"n" binding:"required,min=1,max=100"` // 查询最近N条订单，限制1-100
}

// GetRecentOrdersResponse 查询最近N条订单响应
type GetRecentOrdersResponse struct {
	Orders []Order `json:"orders"`
}
