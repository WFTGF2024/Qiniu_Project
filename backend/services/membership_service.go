package services

import (
	"errors"
	"time"

	"github.com/WFTGF2024/Qiniu_Project/backend/database"
	"github.com/WFTGF2024/Qiniu_Project/backend/models"

	log "github.com/sirupsen/logrus"
)

// MembershipService 会员服务接口
type MembershipService interface {
	GetMembershipInfo(userID uint) (*models.MembershipResponse, error)
	GetAllMemberships() ([]models.MembershipResponse, error)
	CreateMembership(req models.CreateMembershipRequest) (*models.MembershipResponse, error)
	UpdateMembership(membershipID uint, req models.UpdateMembershipRequest) error
	DeleteMembership(membershipID uint) error
	GetMembershipOrders(userID uint) ([]models.OrderResponse, error)
	CreateOrder(req models.CreateOrderRequest) (*models.OrderResponse, error)
	GetLatestOrder(userID uint) (*models.OrderResponse, error)
	GetRecentOrders(userID uint, n int) ([]models.OrderResponse, error)
}

// membershipService 会员服务实现
type membershipService struct{}

// NewMembershipService 创建会员服务实例
func NewMembershipService() MembershipService {
	return &membershipService{}
}

// GetMembershipInfo 获取会员信息
func (s *membershipService) GetMembershipInfo(userID uint) (*models.MembershipResponse, error) {
	log.Info("开始获取会员信息")
	log.WithField("userID", userID).Debug("获取会员信息请求参数")

	// 查找会员信息
	var membership models.MembershipInfo
	if err := database.DB.Where("user_id = ?", userID).First(&membership).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Warn("会员信息不存在")
		return nil, errors.New("会员信息不存在")
	}

	// 构建响应
	membershipResp := models.MembershipResponse{
		MembershipID: membership.MembershipID,
		UserID:       membership.UserID,
		StartDate:    membership.StartDate,
		ExpireDate:   membership.ExpireDate,
		Status:       membership.Status,
	}

	log.WithField("userID", userID).Info("获取会员信息成功")
	return &membershipResp, nil
}

// GetAllMemberships 获取所有会员信息
func (s *membershipService) GetAllMemberships() ([]models.MembershipResponse, error) {
	log.Info("开始获取所有会员信息")

	// 查询所有会员信息
	var memberships []models.MembershipInfo
	if err := database.DB.Find(&memberships).Error; err != nil {
		log.WithError(err).Error("查询会员信息失败")
		return nil, errors.New("查询会员信息失败")
	}

	// 构建响应
	var responses []models.MembershipResponse
	for _, membership := range memberships {
		resp := models.MembershipResponse{
			MembershipID: membership.MembershipID,
			UserID:       membership.UserID,
			StartDate:    membership.StartDate,
			ExpireDate:   membership.ExpireDate,
			Status:       membership.Status,
		}
		responses = append(responses, resp)
	}

	log.Info("获取所有会员信息成功")
	return responses, nil
}

// CreateMembership 创建会员信息
func (s *membershipService) CreateMembership(req models.CreateMembershipRequest) (*models.MembershipResponse, error) {
	log.Info("开始创建会员信息")
	log.WithFields(log.Fields{
		"userID":     req.UserID,
		"startDate":  req.StartDate,
		"expireDate": req.ExpireDate,
		"status":     req.Status,
	}).Debug("创建会员信息请求参数")

	// 检查用户是否存在
	var user models.User
	if err := database.DB.First(&user, req.UserID).Error; err != nil {
		log.WithError(err).WithField("userID", req.UserID).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 检查是否已有会员信息
	var existingMembership models.MembershipInfo
	if err := database.DB.Where("user_id = ?", req.UserID).First(&existingMembership).Error; err == nil {
		log.WithField("userID", req.UserID).Warn("用户已有会员信息")
		return nil, errors.New("用户已有会员信息")
	}

	// 创建新会员信息
	newMembership := models.MembershipInfo{
		UserID:     req.UserID,
		StartDate:  req.StartDate,
		ExpireDate: req.ExpireDate,
		Status:     req.Status,
	}

	// 保存到数据库
	if err := database.DB.Create(&newMembership).Error; err != nil {
		log.WithError(err).Error("创建会员信息失败")
		return nil, errors.New("创建会员信息失败")
	}

	// 构建响应
	membershipResp := models.MembershipResponse{
		MembershipID: newMembership.MembershipID,
		UserID:       newMembership.UserID,
		StartDate:    newMembership.StartDate,
		ExpireDate:   newMembership.ExpireDate,
		Status:       newMembership.Status,
	}

	log.WithField("membershipID", newMembership.MembershipID).Info("创建会员信息成功")
	return &membershipResp, nil
}

// UpdateMembership 更新会员信息
func (s *membershipService) UpdateMembership(membershipID uint, req models.UpdateMembershipRequest) error {
	log.Info("开始更新会员信息")
	log.WithFields(log.Fields{
		"membershipID": membershipID,
		"expireDate":   req.ExpireDate,
		"status":       req.Status,
	}).Debug("更新会员信息请求参数")

	// 查找会员信息
	var membership models.MembershipInfo
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Warn("会员信息不存在")
		return errors.New("会员信息不存在")
	}

	// 准备更新数据
	updateData := make(map[string]interface{})

	if req.ExpireDate != "" {
		updateData["expire_date"] = req.ExpireDate
	}

	if req.Status != "" {
		updateData["status"] = req.Status
	}

	if len(updateData) > 0 {
		if err := database.DB.Model(&membership).Updates(updateData).Error; err != nil {
			log.WithError(err).Error("更新会员信息失败")
			return errors.New("更新会员信息失败")
		}
	}

	log.WithField("membershipID", membershipID).Info("更新会员信息成功")
	return nil
}

// DeleteMembership 删除会员信息
func (s *membershipService) DeleteMembership(membershipID uint) error {
	log.Info("开始删除会员信息")
	log.WithField("membershipID", membershipID).Debug("删除会员信息请求参数")

	// 查找会员信息
	var membership models.MembershipInfo
	if err := database.DB.First(&membership, membershipID).Error; err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Warn("会员信息不存在")
		return errors.New("会员信息不存在")
	}

	// 删除会员信息
	if err := database.DB.Delete(&membership).Error; err != nil {
		log.WithError(err).Error("删除会员信息失败")
		return errors.New("删除会员信息失败")
	}

	log.WithField("membershipID", membershipID).Info("删除会员信息成功")
	return nil
}

// GetMembershipOrders 获取会员订单记录
func (s *membershipService) GetMembershipOrders(userID uint) ([]models.OrderResponse, error) {
	log.Info("开始获取会员订单记录")
	log.WithField("userID", userID).Debug("获取会员订单记录请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 查询会员订单
	var orders []models.MembershipOrder
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").Find(&orders).Error; err != nil {
		log.WithError(err).Error("查询会员订单失败")
		return nil, errors.New("查询会员订单失败")
	}

	// 构建响应
	var responses []models.OrderResponse
	for _, order := range orders {
		resp := models.OrderResponse{
			OrderID:        order.OrderID,
			UserID:         order.UserID,
			PurchaseDate:   order.PurchaseDate,
			DurationMonths: order.DurationMonths,
			Amount:         order.Amount,
			PaymentMethod:  order.PaymentMethod,
		}
		responses = append(responses, resp)
	}

	log.WithField("userID", userID).Info("获取会员订单记录成功")
	return responses, nil
}

// CreateOrder 创建订单
func (s *membershipService) CreateOrder(req models.CreateOrderRequest) (*models.OrderResponse, error) {
	log.Info("开始创建订单")
	log.WithFields(log.Fields{
		"userID":         req.UserID,
		"durationMonths": req.DurationMonths,
		"amount":         req.Amount,
		"paymentMethod":  req.PaymentMethod,
	}).Debug("创建订单请求参数")

	// 检查用户是否存在
	var user models.User
	if err := database.DB.First(&user, req.UserID).Error; err != nil {
		log.WithError(err).WithField("userID", req.UserID).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 创建新订单
	newOrder := models.MembershipOrder{
		UserID:         req.UserID,
		PurchaseDate:   time.Now(),
		DurationMonths: req.DurationMonths,
		Amount:         req.Amount,
		PaymentMethod:  req.PaymentMethod,
	}

	// 保存到数据库
	if err := database.DB.Create(&newOrder).Error; err != nil {
		log.WithError(err).Error("创建订单失败")
		return nil, errors.New("创建订单失败")
	}

	// 构建响应
	orderResp := models.OrderResponse{
		OrderID:        newOrder.OrderID,
		UserID:         newOrder.UserID,
		PurchaseDate:   newOrder.PurchaseDate,
		DurationMonths: newOrder.DurationMonths,
		Amount:         newOrder.Amount,
		PaymentMethod:  newOrder.PaymentMethod,
	}

	log.WithField("orderID", newOrder.OrderID).Info("创建订单成功")
	return &orderResp, nil
}

// GetLatestOrder 获取最近一条订单
func (s *membershipService) GetLatestOrder(userID uint) (*models.OrderResponse, error) {
	log.Info("开始获取最近一条订单")
	log.WithField("userID", userID).Debug("获取最近一条订单请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 查询最近一条订单
	var order models.MembershipOrder
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").First(&order).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Warn("用户没有订单记录")
		return nil, errors.New("用户没有订单记录")
	}

	// 构建响应
	orderResp := models.OrderResponse{
		OrderID:        order.OrderID,
		UserID:         order.UserID,
		PurchaseDate:   order.PurchaseDate,
		DurationMonths: order.DurationMonths,
		Amount:         order.Amount,
		PaymentMethod:  order.PaymentMethod,
	}

	log.WithField("userID", userID).Info("获取最近一条订单成功")
	return &orderResp, nil
}

// GetRecentOrders 获取最近N条订单
func (s *membershipService) GetRecentOrders(userID uint, n int) ([]models.OrderResponse, error) {
	log.Info("开始获取最近N条订单")
	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Debug("获取最近N条订单请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 查询最近N条订单
	var orders []models.MembershipOrder
	if err := database.DB.Where("user_id = ?", userID).Order("purchase_date DESC").Limit(n).Find(&orders).Error; err != nil {
		log.WithError(err).Error("查询订单失败")
		return nil, errors.New("查询订单失败")
	}

	// 构建响应
	var responses []models.OrderResponse
	for _, order := range orders {
		resp := models.OrderResponse{
			OrderID:        order.OrderID,
			UserID:         order.UserID,
			PurchaseDate:   order.PurchaseDate,
			DurationMonths: order.DurationMonths,
			Amount:         order.Amount,
			PaymentMethod:  order.PaymentMethod,
		}
		responses = append(responses, resp)
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Info("获取最近N条订单成功")
	return responses, nil
}
