package handlers

import (
	"net/http"
	"qiniu_project/backend/services"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// 初始化会员服务
var membershipService = services.NewMembershipService()

// GetMembershipInfo 查询会员信息
func GetMembershipInfo(c *gin.Context) {
	log.Info("开始处理查询会员信息请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	log.WithField("userID", userID).Debug("查询会员信息请求参数")

	// 调用会员服务获取会员信息
	membershipInfo, err := membershipService.GetMembershipInfo(userID.(uint))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取会员信息失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("成功获取会员信息")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    membershipInfo,
	})
}
