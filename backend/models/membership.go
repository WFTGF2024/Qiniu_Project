package models

import "time"

// Membership 会员模型
type Membership struct {
	MembershipID       uint      `json:"membership_id" gorm:"primaryKey"`
	UserID             uint      `json:"user_id" gorm:"not null"`
	MembershipType     string    `json:"membership_type" gorm:"not null"` // 如: "basic", "premium", "vip"
	StartDate          time.Time `json:"start_date"`
	EndDate            time.Time `json:"end_date"`
	Status             string    `json:"status" gorm:"not null"` // 如: "active", "expired", "cancelled"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedAt          time.Time `json:"updated_at"`
}

// MembershipInfoRequest 查询会员信息请求
type MembershipInfoRequest struct {
	UserID uint `json:"user_id" binding:"required"`
}

// MembershipInfoResponse 会员信息响应
type MembershipInfoResponse struct {
	MembershipID   uint      `json:"membership_id"`
	UserID         uint      `json:"user_id"`
	MembershipType string    `json:"membership_type"`
	StartDate      time.Time `json:"start_date"`
	EndDate        time.Time `json:"end_date"`
	Status         string    `json:"status"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}
