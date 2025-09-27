package handlers

import (
	"net/http"
	"strconv"
	"qiniu_project/backend/models"
	"qiniu_project/backend/services"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// 初始化会员服务
var membershipService = services.NewMembershipService()

// GetMembershipInfo 查询会员信息
func GetMembershipInfo(c *gin.Context) {
	log.Info("开始处理查询会员信息请求")

	// 从URL参数中获取user_id
	userIDStr := c.Param("user_id")
	userID, err := strconv.ParseUint(userIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析user_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的用户ID"})
		return
	}

	log.WithField("userID", userID).Debug("查询会员信息请求参数")

	// 调用会员服务获取会员信息
	membership, err := membershipService.GetMembershipInfo(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员信息失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "会员信息不存在"})
		return
	}

	log.WithField("userID", userID).Info("成功获取会员信息")
	c.JSON(http.StatusOK, membership)
}

// GetAllMemberships 查询所有会员信息
func GetAllMemberships(c *gin.Context) {
	log.Info("开始处理查询所有会员信息请求")

	// 调用会员服务获取所有会员信息
	memberships, err := membershipService.GetAllMemberships()
	if err != nil {
		log.WithError(err).Error("获取所有会员信息失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "查询失败"})
		return
	}

	log.Info("成功获取所有会员信息")
	c.JSON(http.StatusOK, memberships)
}

// CreateMembership 新增会员信息
func CreateMembership(c *gin.Context) {
	log.Info("开始处理新增会员信息请求")

	var req models.CreateMembershipRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析新增会员信息请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"userID":     req.UserID,
		"startDate":  req.StartDate,
		"expireDate": req.ExpireDate,
		"status":     req.Status,
	}).Debug("新增会员信息请求参数")

	// 调用会员服务创建会员信息
	membership, err := membershipService.CreateMembership(req)
	if err != nil {
		log.WithError(err).Error("创建会员信息失败")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("membershipID", membership.MembershipID).Info("创建会员信息成功")
	c.JSON(http.StatusOK, gin.H{
		"success":      true,
		"membership_id": membership.MembershipID,
		"message":      "会员信息已创建",
	})
}

// UpdateMembership 更新会员信息
func UpdateMembership(c *gin.Context) {
	log.Info("开始处理更新会员信息请求")

	// 从URL参数中获取membership_id
	membershipIDStr := c.Param("membership_id")
	membershipID, err := strconv.ParseUint(membershipIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析membership_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的会员ID"})
		return
	}

	var req models.UpdateMembershipRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析更新会员信息请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"membershipID": membershipID,
		"expireDate":   req.ExpireDate,
		"status":       req.Status,
	}).Debug("更新会员信息请求参数")

	// 调用会员服务更新会员信息
	if err := membershipService.UpdateMembership(uint(membershipID), req); err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("更新会员信息失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("membershipID", membershipID).Info("更新会员信息成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "会员信息已更新",
	})
}

// DeleteMembership 删除会员信息
func DeleteMembership(c *gin.Context) {
	log.Info("开始处理删除会员信息请求")

	// 从URL参数中获取membership_id
	membershipIDStr := c.Param("membership_id")
	membershipID, err := strconv.ParseUint(membershipIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析membership_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的会员ID"})
		return
	}

	log.WithField("membershipID", membershipID).Debug("删除会员信息请求参数")

	// 调用会员服务删除会员信息
	if err := membershipService.DeleteMembership(uint(membershipID)); err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("删除会员信息失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("membershipID", membershipID).Info("删除会员信息成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "会员信息已删除",
	})
}

// GetMembershipOrders 查询会员订单记录
func GetMembershipOrders(c *gin.Context) {
	log.Info("开始处理查询会员订单记录请求")

	// 从URL参数中获取user_id
	userIDStr := c.Param("user_id")
	userID, err := strconv.ParseUint(userIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析user_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的用户ID"})
		return
	}

	log.WithField("userID", userID).Debug("查询会员订单记录请求参数")

	// 调用会员服务获取会员订单记录
	orders, err := membershipService.GetMembershipOrders(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员订单记录失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "订单记录不存在"})
		return
	}

	log.WithField("userID", userID).Info("成功获取会员订单记录")
	c.JSON(http.StatusOK, orders)
}

// CreateOrder 新增订单
func CreateOrder(c *gin.Context) {
	log.Info("开始处理新增订单请求")

	var req models.CreateOrderRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析新增订单请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"userID":         req.UserID,
		"durationMonths": req.DurationMonths,
		"amount":         req.Amount,
		"paymentMethod":  req.PaymentMethod,
	}).Debug("新增订单请求参数")

	// 调用会员服务创建订单
	order, err := membershipService.CreateOrder(req)
	if err != nil {
		log.WithError(err).Error("创建订单失败")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("orderID", order.OrderID).Info("创建订单成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"order_id": order.OrderID,
		"message": "订单已创建",
	})
}

// GetLatestOrder 查询最近一条订单
func GetLatestOrder(c *gin.Context) {
	log.Info("开始处理查询最近一条订单请求")

	// 从URL参数中获取user_id
	userIDStr := c.Param("user_id")
	userID, err := strconv.ParseUint(userIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析user_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的用户ID"})
		return
	}

	log.WithField("userID", userID).Debug("查询最近一条订单请求参数")

	// 调用会员服务获取最近一条订单
	order, err := membershipService.GetLatestOrder(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取最近一条订单失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "订单记录不存在"})
		return
	}

	log.WithField("userID", userID).Info("成功获取最近一条订单")
	c.JSON(http.StatusOK, order)
}

// GetRecentOrders 查询最近N条订单
func GetRecentOrders(c *gin.Context) {
	log.Info("开始处理查询最近N条订单请求")

	// 从URL参数中获取user_id
	userIDStr := c.Param("user_id")
	userID, err := strconv.ParseUint(userIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析user_id失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的用户ID"})
		return
	}

	// 从查询参数中获取n
	nStr := c.DefaultQuery("n", "5")
	n, err := strconv.Atoi(nStr)
	if err != nil || n <= 0 {
		log.WithError(err).Error("解析n参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "无效的数量参数"})
		return
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Debug("查询最近N条订单请求参数")

	// 调用会员服务获取最近N条订单
	orders, err := membershipService.GetRecentOrders(uint(userID), n)
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取最近N条订单失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "查询失败"})
		return
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Info("成功获取最近N条订单")
	c.JSON(http.StatusOK, orders)
}