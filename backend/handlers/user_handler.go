package handlers

import (
	"net/http"
	"time"

	"github.com/WFTGF2024/Qiniu_Project/backend/models"
	"github.com/WFTGF2024/Qiniu_Project/backend/services"
	"github.com/WFTGF2024/Qiniu_Project/backend/utils"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// 初始化用户服务
var userService = services.NewUserService()

// Register 用户注册
func Register(c *gin.Context) {
	log.Info("开始处理用户注册请求")

	var req models.UserRegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析注册请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"username":    req.Username,
		"email":       req.Email,
		"phoneNumber": req.PhoneNumber,
	}).Debug("用户注册请求参数")

	// 调用用户服务处理注册逻辑
	user, err := userService.RegisterUser(req)
	if err != nil {
		log.WithError(err).Error("用户注册失败")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", user.UserID).Info("用户注册成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"user_id": user.UserID,
		"message": "注册成功",
	})
}

// Login 用户登录
func Login(c *gin.Context) {
	log.Info("开始处理用户登录请求")

	var req models.UserLoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析登录请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("username", req.Username).Debug("用户登录请求参数")

	// 调用用户服务处理登录逻辑
	token, err := userService.LoginUser(req)
	if err != nil {
		log.WithError(err).Error("用户登录失败")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": err.Error()})
		return
	}

	// 计算令牌过期时间
	expireAt := time.Now().Add(time.Hour * 24).Format(time.RFC3339)

	log.WithField("username", req.Username).Info("用户登录成功")

	c.JSON(http.StatusOK, gin.H{
		"success":   true,
		"token":     token,
		"expire_at": expireAt,
	})
}

// GetProfile 获取用户信息
func GetProfile(c *gin.Context) {
	log.Info("开始处理获取用户信息请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	log.WithField("userID", userID).Debug("获取用户信息请求参数")

	// 调用用户服务获取用户信息
	userProfile, err := userService.GetUserProfile(userID.(uint))
	if err != nil {
		log.WithError(err).WithField("userID", userID).Error("获取用户信息失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "用户不存在"})
		return
	}

	log.WithField("userID", userID).Info("成功获取用户信息")
	c.JSON(http.StatusOK, userProfile)
}

// UpdateUser 更新用户信息
func UpdateUser(c *gin.Context) {
	log.Info("开始处理更新用户信息请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	var req models.UpdateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析更新用户信息请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithFields(log.Fields{
		"userID":      userID,
		"fullName":    req.FullName,
		"email":       req.Email,
		"phoneNumber": req.PhoneNumber,
	}).Debug("更新用户信息请求参数")

	// 调用用户服务更新用户信息
	if err := userService.UpdateUser(userID.(uint), req); err != nil {
		log.WithError(err).WithField("userID", userID).Error("更新用户信息失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("userID", userID).Info("用户信息更新成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "用户信息已更新",
	})
}

// DeleteUser 删除用户
func DeleteUser(c *gin.Context) {
	log.Info("开始处理删除用户请求")

	// 从JWT令牌中获取用户ID
	userID, exists := c.Get("user_id")
	if !exists {
		log.Warn("未授权访问，缺少user_id")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未授权访问"})
		return
	}

	log.WithField("userID", userID).Debug("删除用户请求参数")

	// 调用用户服务删除用户
	if err := userService.DeleteUser(userID.(uint)); err != nil {
		log.WithError(err).WithField("userID", userID).Error("删除用户失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "删除失败"})
		return
	}

	log.WithField("userID", userID).Info("用户删除成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "用户已删除",
	})
}

// VerifySecurity 验证密保问题
func VerifySecurity(c *gin.Context) {
	log.Info("开始处理验证密保问题请求")

	var req models.SecurityVerifyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析验证密保问题请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("username", req.Username).Debug("验证密保问题请求参数")

	// 调用用户服务验证密保问题
	valid, err := userService.VerifySecurity(req)
	if err != nil {
		log.WithError(err).Error("验证密保问题失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "验证失败"})
		return
	}

	if !valid {
		log.WithField("username", req.Username).Warn("密保答案验证失败")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "密保答案错误"})
		return
	}

	// 生成重置令牌
	resetToken := utils.GenerateResetToken()

	// 在实际应用中，应该将重置令牌存储到数据库中，并设置过期时间
	// 这里简化处理，直接返回令牌

	log.WithFields(log.Fields{
		"username":   req.Username,
		"resetToken": resetToken,
	}).Info("密保问题验证成功")

	c.JSON(http.StatusOK, gin.H{
		"success":     true,
		"reset_token": resetToken,
	})
}

// ResetPassword 重置密码
func ResetPassword(c *gin.Context) {
	log.Info("开始处理重置密码请求")

	var req models.ResetPasswordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.WithError(err).Error("解析重置密码请求失败")
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "message": err.Error()})
		return
	}

	log.WithField("resetToken", req.ResetToken).Debug("重置密码请求参数")

	// 在实际应用中，应该验证reset_token是否有效且未过期
	// 这里简化处理，假设令牌有效

	// 调用用户服务重置密码
	if err := userService.ResetPassword(req); err != nil {
		log.WithError(err).Error("密码重置失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "密码重置失败"})
		return
	}

	log.Info("密码重置成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "密码已更新",
	})
}
