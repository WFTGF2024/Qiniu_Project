package services

import (
	"errors"
	"qiniu_project/backend/database"
	"qiniu_project/backend/models"
	"time"
	log "github.com/sirupsen/logrus"
)

// MembershipService 会员服务接口
type MembershipService interface {
	GetMembershipInfo(userID uint) (*models.MembershipInfoResponse, error)
	CreateMembership(req models.Membership) error
	UpdateMembership(membershipID uint, req models.Membership) error
	CancelMembership(membershipID uint) error
}

// membershipService 会员服务实现
type membershipService struct{}

// NewMembershipService 创建会员服务实例
func NewMembershipService() MembershipService {
	return &membershipService{}
}

// GetMembershipInfo 获取会员信息
func (s *membershipService) GetMembershipInfo(userID uint) (*models.MembershipInfoResponse, error) {
	log.Info("开始处理获取会员信息请求")
	log.WithField("userID", userID).Debug("获取会员信息请求参数")
	
	// 查询会员信息
	var membership models.Membership
	if err := database.DB.Where("user_id = ? AND status = ?", userID, "active").First(&membership).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员信息失败")
		return nil, errors.New("未找到活跃的会员信息")
	}
	
	// 构建响应
	response := &models.MembershipInfoResponse{
		MembershipID:   membership.MembershipID,
		UserID:         membership.UserID,
		MembershipType: membership.MembershipType,
		StartDate:      membership.StartDate,
		EndDate:        membership.EndDate,
		Status:         membership.Status,
		CreatedAt:      membership.CreatedAt,
		UpdatedAt:      membership.UpdatedAt,
	}
	
	log.WithField("userID", userID).Info("成功获取会员信息")
	return response, nil
}

// CreateMembership 创建会员
func (s *membershipService) CreateMembership(req models.Membership) error {
	log.Info("开始处理创建会员请求")
	log.WithFields(log.Fields{
		"userID":         req.UserID,
		"membershipType": req.MembershipType,
	}).Debug("创建会员请求参数")
	
	// 检查用户是否已有活跃会员
	var existingMembership models.Membership
	if err := database.DB.Where("user_id = ? AND status = ?", req.UserID, "active").First(&existingMembership).Error; err == nil {
		log.WithField("userID", req.UserID).Warn("用户已有活跃会员")
		return errors.New("用户已有活跃会员")
	}
	
	// 设置默认值
	if req.StartDate.IsZero() {
		req.StartDate = time.Now()
	}
	
	if req.EndDate.IsZero() {
		// 根据会员类型设置默认结束时间
		switch req.MembershipType {
		case "basic":
			req.EndDate = req.StartDate.AddDate(0, 1, 0) // 1个月
		case "premium":
			req.EndDate = req.StartDate.AddDate(0, 3, 0) // 3个月
		case "vip":
			req.EndDate = req.StartDate.AddDate(0, 12, 0) // 1年
		default:
			req.EndDate = req.StartDate.AddDate(0, 1, 0) // 默认1个月
		}
	}
	
	if req.Status == "" {
		req.Status = "active"
	}
	
	// 保存到数据库
	if err := database.DB.Create(&req).Error; err != nil {
		log.WithError(err).Error("创建会员失败")
		return errors.New("创建会员失败")
	}
	
	log.WithFields(log.Fields{
		"userID":         req.UserID,
		"membershipID":   req.MembershipID,
	}).Info("创建会员成功")
	return nil
}

// UpdateMembership 更新会员信息
func (s *membershipService) UpdateMembership(membershipID uint, req models.Membership) error {
	log.Info("开始处理更新会员信息请求")
	log.WithFields(log.Fields{
		"membershipID":   membershipID,
		"membershipType": req.MembershipType,
	}).Debug("更新会员信息请求参数")
	
	// 查找会员
	var membership models.Membership
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("会员不存在")
		return errors.New("会员不存在")
	}
	
	// 更新字段
	if req.MembershipType != "" {
		membership.MembershipType = req.MembershipType
	}
	if !req.StartDate.IsZero() {
		membership.StartDate = req.StartDate
	}
	if !req.EndDate.IsZero() {
		membership.EndDate = req.EndDate
	}
	if req.Status != "" {
		membership.Status = req.Status
	}
	
	// 保存更新
	if err := database.DB.Save(&membership).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("更新会员信息失败")
		return errors.New("更新会员信息失败")
	}
	
	log.WithField("membershipID", membershipID).Info("更新会员信息成功")
	return nil
}

// CancelMembership 取消会员
func (s *membershipService) CancelMembership(membershipID uint) error {
	log.Info("开始处理取消会员请求")
	log.WithField("membershipID", membershipID).Debug("取消会员请求参数")
	
	// 查找会员
	var membership models.Membership
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("会员不存在")
		return errors.New("会员不存在")
	}
	
	// 更新状态为已取消
	membership.Status = "cancelled"
	
	// 保存更新
	if err := database.DB.Save(&membership).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("取消会员失败")
		return errors.New("取消会员失败")
	}
	
	log.WithField("membershipID", membershipID).Info("取消会员成功")
	return nil
}
