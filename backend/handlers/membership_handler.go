package handlers

import (
	"net/http"
	"qiniu_project/backend/models"
	"qiniu_project/backend/services"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// 初始化会员服务
var membershipService = services.NewMembershipService()

// GetMembershipInfo 查询会员信息
func GetMembershipInfo(c *gin.Context) {
	log.Info("开始处理查询会员信息请求")

	// 从URL参数中获取用户ID
	userIDStr := c.Param("user_id")
	userID, err := strconv.ParseUint(userIDStr, 10, 32)
	if err != nil {
		log.WithError(err).Error("解析用户ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "用户ID参数格式错误"})
		return
	}

	log.WithField("userID", userID).Debug("查询会员信息请求参数")

	// 调用会员服务获取会员信息
	membershipInfo, err := membershipService.GetMembershipInfo(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员信息失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功获取会员信息")
	c.JSON(http.StatusOK, gin.H{
		"membership_id": membershipInfo.Membership.MembershipID,
		"user_id":       membershipInfo.Membership.UserID,
		"start_date":    membershipInfo.Membership.StartDate.Format("2006-01-02"),
		"expire_date":   membershipInfo.Membership.EndDate.Format("2006-01-02"),
		"status":        membershipInfo.Membership.Status,
	})
}

// CreateMembershipInfo 新增会员信息
func CreateMembershipInfo(c *gin.Context) {
	log.Info("开始处理新增会员信息请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	log.WithField("userID", userID).Debug("新增会员信息请求参数")

	// 绑定请求体
	var membership models.Membership
	if err := c.ShouldBindJSON(&membership); err != nil {
		log.WithError(err).Error("绑定请求体失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "请求参数格式错误"})
		return
	}

	// 设置用户ID
	membership.UserID = userID.(uint)

	// 设置默认会员类型
	if membership.MembershipType == "" {
		membership.MembershipType = "basic"
	}

	// 调用会员服务创建会员
	if err := membershipService.CreateMembershipInfo(membership); err != nil {
		log.WithError(err).WithField("userID", userID).Error("创建会员失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功创建会员")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"membership_id": membership.MembershipID,
		"message": "会员信息已创建",
	})
}

// GetAllMemberships 查询所有会员信息
func GetAllMemberships(c *gin.Context) {
	log.Info("开始处理查询所有会员信息请求")

	// 调用会员服务获取所有会员
	memberships, err := membershipService.GetAllMemberships()
	if err != nil {
		log.WithError(err).Error("获取所有会员失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.Info("成功获取所有会员信息")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": memberships,
	})
}

// UpdateMembership 更新会员信息
func UpdateMembership(c *gin.Context) {
	log.Info("开始处理更新会员信息请求")

	// 获取会员ID参数
	membershipID, err := strconv.ParseUint(c.Param("membership_id"), 10, 32)
	if err != nil {
		log.WithError(err).Error("解析会员ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "会员ID参数格式错误"})
		return
	}

	log.WithField("membershipID", membershipID).Debug("更新会员信息请求参数")

	// 绑定请求体
	var req models.UpdateMembershipRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("绑定请求体失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "请求参数格式错误"})
		return
	}

	// 调用会员服务更新会员
	if err := membershipService.UpdateMembershipWithParams(uint(membershipID), req); err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("更新会员失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("membershipID", membershipID).Info("成功更新会员")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "会员信息已更新",
	})
}

// DeleteMembership 删除会员信息
func DeleteMembership(c *gin.Context) {
	log.Info("开始处理删除会员信息请求")

	// 获取会员ID参数
	membershipID, err := strconv.ParseUint(c.Param("membership_id"), 10, 32)
	if err != nil {
		log.WithError(err).Error("解析会员ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "会员ID参数格式错误"})
		return
	}

	log.WithField("membershipID", membershipID).Debug("删除会员信息请求参数")

	// 调用会员服务删除会员
	if err := membershipService.DeleteMembership(uint(membershipID)); err != nil {
		log.WithError(err).WithField("membershipID", membershipID).Error("删除会员失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("membershipID", membershipID).Info("成功删除会员")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "会员信息已删除",
	})
}

// CreateOrder 新增订单
func CreateOrder(c *gin.Context) {
	log.Info("开始处理新增订单请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	log.WithField("userID", userID).Debug("新增订单请求参数")

	// 绑定请求体
	var req models.CreateOrderRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("绑定请求体失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "请求参数格式错误"})
		return
	}

	// 设置用户ID
	req.UserID = userID.(uint)

	// 调用会员服务创建订单
	response, err := membershipService.CreateOrder(req)
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("创建订单失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功创建订单")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"order_id": response.OrderID,
		"message": response.Message,
	})
}

// GetMembershipOrders 查询会员订单
func GetMembershipOrders(c *gin.Context) {
	log.Info("开始处理查询会员订单请求")

	// 获取用户ID参数
	userID, err := strconv.ParseUint(c.Param("user_id"), 10, 32)
	if err != nil {
		log.WithError(err).Error("解析用户ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "用户ID参数格式错误"})
		return
	}

	log.WithField("userID", userID).Debug("查询会员订单请求参数")

	// 调用会员服务获取会员订单
	orders, err := membershipService.GetMembershipOrders(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员订单失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功获取会员订单")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": orders,
	})
}

// GetLatestOrder 查询最近一条订单
func GetLatestOrder(c *gin.Context) {
	log.Info("开始处理查询最近一条订单请求")

	// 获取用户ID参数
	userID, err := strconv.ParseUint(c.Param("user_id"), 10, 32)
	if err != nil {
		log.WithError(err).Error("解析用户ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "用户ID参数格式错误"})
		return
	}

	log.WithField("userID", userID).Debug("查询最近一条订单请求参数")

	// 调用会员服务获取最近一条订单
	order, err := membershipService.GetLatestOrder(uint(userID))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取最近一条订单失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功获取最近一条订单")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": order,
	})
}

// GetRecentOrders 查询最近N条订单
func GetRecentOrders(c *gin.Context) {
	log.Info("开始处理查询最近N条订单请求")

	// 获取用户ID参数
	userID, err := strconv.ParseUint(c.Param("user_id"), 10, 32)
	if err != nil {
		log.WithError(err).Error("解析用户ID参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "用户ID参数格式错误"})
		return
	}

	// 获取n参数
	nStr := c.DefaultQuery("n", "5")
	n, err := strconv.Atoi(nStr)
	if err != nil || n < 1 || n > 100 {
		log.WithError(err).Error("解析n参数失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": "n参数格式错误，应为1-100之间的整数"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"userID": userID,
		"n":      n,
	}).Info("成功获取最近N条订单")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": orders,
	})
}
