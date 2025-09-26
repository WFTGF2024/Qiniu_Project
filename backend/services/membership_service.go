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
	CreateMembershipInfo(req models.Membership) error
	GetAllMemberships() ([]models.Membership, error)
	UpdateMembership(membershipID uint) error
	DeleteMembership(membershipID uint) error
	CreateOrder(req models.CreateOrderRequest) (*models.CreateOrderResponse, error)
	GetMembershipOrders(userID uint) ([]models.Order, error)
	GetLatestOrder(userID uint) (*models.Order, error)
	GetRecentOrders(userID uint, n int) ([]models.Order, error)
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
		Membership: membership,
	}

	log.WithField("userID", userID).Info("成功获取会员信息")
	return response, nil
}

// CreateMembershipInfo 创建会员
func (s *membershipService) CreateMembershipInfo(req models.Membership) error {
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
		"userID":       req.UserID,
		"membershipID": req.MembershipID,
	}).Info("创建会员成功")
	return nil
}

// GetAllMemberships 获取所有会员信息
func (s *membershipService) GetAllMemberships() ([]models.Membership, error) {
	log.Info("开始处理获取所有会员信息请求")

	// 查询所有会员信息
	var memberships []models.Membership
	if err := database.DB.Find(&memberships).Error; err != nil {
		log.WithError(err).Error("获取所有会员信息失败")
		return nil, errors.New("获取所有会员信息失败")
	}

	log.WithField("count", len(memberships)).Info("成功获取所有会员信息")
	return memberships, nil
}

// UpdateMembership 更新会员信息
func (s *membershipService) UpdateMembership(membershipID uint) error {
	log.Info("开始处理更新会员信息请求")
	log.WithFields(log.Fields{
		"membershipID": membershipID,
	}).Debug("更新会员信息请求参数")

	// 查询会员信息
	var membership models.Membership
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("会员信息不存在")
		return errors.New("会员信息不存在")
	}

	// 更新LastUpdated字段
	membership.LastUpdated = time.Now()

	// 保存更新
	if err := database.DB.Save(&membership).Error; err != nil {
		log.WithError(err).Error("更新会员信息失败")
		return errors.New("更新会员信息失败")
	}

	log.WithField("membershipID", membershipID).Info("成功更新会员信息")
	return nil
}

// DeleteMembership 删除会员信息
func (s *membershipService) DeleteMembership(membershipID uint) error {
	log.Info("开始处理删除会员信息请求")
	log.WithField("membershipID", membershipID).Debug("删除会员信息请求参数")

	// 查询会员信息
	var membership models.Membership
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("会员信息不存在")
		return errors.New("会员信息不存在")
	}

	// 删除会员
	if err := database.DB.Delete(&membership).Error; err != nil {
		log.WithError(err).Error("删除会员信息失败")
		return errors.New("删除会员信息失败")
	}

	log.WithField("membershipID", membershipID).Info("成功删除会员信息")
	return nil
}

// CreateOrder 创建订单
func (s *membershipService) CreateOrder(req models.CreateOrderRequest) (*models.CreateOrderResponse, error) {
	log.Info("开始处理创建订单请求")
	log.WithFields(log.Fields{
		"userID":         req.UserID,
		"durationMonths": req.DurationMonths,
		"amount":         req.Amount,
		"paymentMethod":  req.PaymentMethod,
	}).Debug("创建订单请求参数")

	// 创建订单
	order := models.Order{
		UserID:         req.UserID,
		PurchaseDate:   time.Now(),
		DurationMonths: req.DurationMonths,
		Amount:         req.Amount,
		PaymentMethod:  req.PaymentMethod,
	}

	// 保存到数据库
	if err := database.DB.Create(&order).Error; err != nil {
		log.WithError(err).Error("创建订单失败")
		return nil, errors.New("创建订单失败")
	}

	log.WithFields(log.Fields{
		"orderID": order.OrderID,
		"userID":  req.UserID,
	}).Info("成功创建订单")

	response := &models.CreateOrderResponse{
		OrderID: order.OrderID,
		Message: "订单已创建",
	}
	return response, nil
}

// GetMembershipOrders 获取会员订单
func (s *membershipService) GetMembershipOrders(userID uint) ([]models.Order, error) {
	log.Info("开始处理获取会员订单请求")
	log.WithField("userID", userID).Debug("获取会员订单请求参数")

	// 查询会员订单
	var orders []models.Order
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").Find(&orders).Error; err != nil {
		log.WithError(err).Error("获取会员订单失败")
		return nil, errors.New("获取会员订单失败")
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"count":  len(orders),
	}).Info("成功获取会员订单")
	return orders, nil
}

// GetLatestOrder 获取最近一条订单
func (s *membershipService) GetLatestOrder(userID uint) (*models.Order, error) {
	log.Info("开始处理获取最近一条订单请求")
	log.WithField("userID", userID).Debug("获取最近一条订单请求参数")

	// 查询最近一条订单
	var order models.Order
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").First(&order).Error; err != nil {
		log.WithError(err).Error("获取最近一条订单失败")
		return nil, errors.New("未找到订单记录")
	}

	log.WithFields(log.Fields{
		"orderID": order.OrderID,
		"userID":  userID,
	}).Info("成功获取最近一条订单")
	return &order, nil
}

// GetRecentOrders 获取最近N条订单
func (s *membershipService) GetRecentOrders(userID uint, n int) ([]models.Order, error) {
	log.Info("开始处理获取最近N条订单请求")
	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Debug("获取最近N条订单请求参数")

	// 查询最近N条订单
	var orders []models.Order
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").Limit(n).Find(&orders).Error; err != nil {
		log.WithError(err).Error("获取最近N条订单失败")
		return nil, errors.New("获取最近N条订单失败")
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
		"count":  len(orders),
	}).Info("成功获取最近N条订单")
	return orders, nil
}
