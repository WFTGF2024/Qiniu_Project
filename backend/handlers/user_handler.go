package handlers

import (
	"net/http"
	"qiniu_project/backend/database"
	"qiniu_project/backend/models"
	"qiniu_project/backend/utils"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	log "github.com/sirupsen/logrus"
)

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

	// 检查用户名是否已存在
	var existingUser models.User
	if err := database.DB.Where("username = ?", req.Username).First(&existingUser).Error; err == nil {
		log.WithField("username", req.Username).Warn("用户名已存在")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": "用户名已存在"})
		return
	}

	// 检查邮箱是否已存在
	if err := database.DB.Where("email = ?", req.Email).First(&existingUser).Error; err == nil {
		log.WithField("email", req.Email).Warn("邮箱已被使用")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": "邮箱已被使用"})
		return
	}

	// 检查手机号是否已存在
	if err := database.DB.Where("phone_number = ?", req.PhoneNumber).First(&existingUser).Error; err == nil {
		log.WithField("phoneNumber", req.PhoneNumber).Warn("手机号已被使用")
		c.JSON(http.StatusConflict, gin.H{"success": false, "message": "手机号已被使用"})
		return
	}

	// 哈希密码
	passwordHash, err := utils.HashPassword(req.Password)
	if err != nil {
		log.WithError(err).Error("密码加密失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "密码加密失败"})
		return
	}

	// 哈希安全问题答案
	answer1Hash, err := utils.HashPassword(req.SecurityAnswer1)
	if err != nil {
		log.WithError(err).Error("答案加密失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "答案加密失败"})
		return
	}

	answer2Hash, err := utils.HashPassword(req.SecurityAnswer2)
	if err != nil {
		log.WithError(err).Error("答案加密失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "答案加密失败"})
		return
	}

	// 创建新用户
	newUser := models.User{
		Username:            req.Username,
		PasswordHash:        passwordHash,
		FullName:            req.FullName,
		Email:               req.Email,
		PhoneNumber:         req.PhoneNumber,
		SecurityQuestion1:   req.SecurityQuestion1,
		SecurityAnswer1Hash: answer1Hash,
		SecurityQuestion2:   req.SecurityQuestion2,
		SecurityAnswer2Hash: answer2Hash,
	}

	if err := database.DB.Create(&newUser).Error; err != nil {
		log.WithError(err).Error("用户创建失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "用户创建失败"})
		return
	}

	log.WithField("userID", newUser.UserID).Info("用户注册成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"user_id": newUser.UserID,
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

	// 查找用户
	var user models.User
	if err := database.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			log.WithField("username", req.Username).Warn("用户不存在")
			c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "用户不存在"})
		} else {
			log.WithError(err).Error("查询用户失败")
			c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "查询用户失败"})
		}
		return
	}

	// 验证密码
	if !utils.CheckPassword(req.Password, user.PasswordHash) {
		log.WithFields(log.Fields{
			"username": req.Username,
			"userID":   user.UserID,
		}).Warn("密码错误")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "密码错误"})
		return
	}

	// 生成JWT令牌
	token, err := utils.GenerateJWTToken(user.UserID)
	if err != nil {
		log.WithError(err).Error("生成令牌失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "生成令牌失败"})
		return
	}

	// 计算令牌过期时间
	expireAt := time.Now().Add(time.Hour * 24).Format(time.RFC3339)

	log.WithFields(log.Fields{
		"username": req.Username,
		"userID":   user.UserID,
		"expireAt": expireAt,
	}).Info("用户登录成功")

	c.JSON(http.StatusOK, gin.H{
		"success":   true,
		"token":     token,
		"user_id":   user.UserID,
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

	// 查询用户信息
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Error("查询用户信息失败")
		c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "用户不存在"})
		return
	}

	// 返回用户信息（不包含密码和密保答案）
	response := models.UserProfileResponse{
		UserID:      user.UserID,
		Username:    user.Username,
		FullName:    user.FullName,
		Email:       user.Email,
		PhoneNumber: user.PhoneNumber,
		CreatedAt:   user.CreatedAt,
		UpdatedAt:   user.UpdatedAt,
	}

	log.WithField("userID", userID).Info("成功获取用户信息")
	c.JSON(http.StatusOK, response)
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

	// 检查邮箱是否已被其他用户使用
	if req.Email != "" {
		var existingUser models.User
		if err := database.DB.Where("email = ? AND user_id != ?", req.Email, userID).First(&existingUser).Error; err == nil {
			log.WithFields(log.Fields{
				"email":  req.Email,
				"userID": userID,
			}).Warn("邮箱已被其他用户使用")
			c.JSON(http.StatusConflict, gin.H{"success": false, "message": "邮箱已被使用"})
			return
		}
	}

	// 检查手机号是否已被其他用户使用
	if req.PhoneNumber != "" {
		var existingUser models.User
		if err := database.DB.Where("phone_number = ? AND user_id != ?", req.PhoneNumber, userID).First(&existingUser).Error; err == nil {
			log.WithFields(log.Fields{
				"phoneNumber": req.PhoneNumber,
				"userID":     userID,
			}).Warn("手机号已被其他用户使用")
			c.JSON(http.StatusConflict, gin.H{"success": false, "message": "手机号已被使用"})
			return
		}
	}

	// 更新用户信息
	updateData := make(map[string]interface{})
	if req.FullName != "" {
		updateData["full_name"] = req.FullName
	}
	if req.Email != "" {
		updateData["email"] = req.Email
	}
	if req.PhoneNumber != "" {
		updateData["phone_number"] = req.PhoneNumber
	}

	if len(updateData) > 0 {
		log.WithFields(log.Fields{
			"userID":     userID,
			"updateData": updateData,
		}).Debug("准备更新用户信息")

		if err := database.DB.Model(&models.User{}).Where("user_id = ?", userID).Updates(updateData).Error; err != nil {
			log.WithError(err).WithField("userID", userID).Error("更新用户信息失败")
			c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "更新失败"})
			return
		}

		log.WithField("userID", userID).Info("用户信息更新成功")
	} else {
		log.WithField("userID", userID).Info("没有需要更新的用户信息")
	}

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

	// 删除用户
	if err := database.DB.Delete(&models.User{}, userID).Error; err != nil {
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

	// 查找用户
	var user models.User
	if err := database.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			log.WithField("username", req.Username).Warn("用户不存在")
			c.JSON(http.StatusNotFound, gin.H{"success": false, "message": "用户不存在"})
		} else {
			log.WithError(err).Error("查询用户失败")
			c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "查询用户失败"})
		}
		return
	}

	// 验证密保答案
	answer1Valid := utils.CheckPassword(req.SecurityAnswer1, user.SecurityAnswer1Hash)
	answer2Valid := utils.CheckPassword(req.SecurityAnswer2, user.SecurityAnswer2Hash)

	if !answer1Valid || !answer2Valid {
		log.WithFields(log.Fields{
			"username":       req.Username,
			"userID":        user.UserID,
			"answer1Valid": answer1Valid,
			"answer2Valid": answer2Valid,
		}).Warn("密保答案验证失败")
		c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "密保答案错误"})
		return
	}

	// 生成重置令牌
	resetToken := utils.GenerateResetToken()

	// 在实际应用中，应该将重置令牌存储到数据库中，并设置过期时间
	// 这里简化处理，直接返回令牌

	log.WithFields(log.Fields{
		"username":   req.Username,
		"userID":    user.UserID,
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

	// 哈希新密码
	passwordHash, err := utils.HashPassword(req.NewPassword)
	if err != nil {
		log.WithError(err).Error("密码加密失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "密码加密失败"})
		return
	}

	// 更新用户密码
	// 注意：实际应用中，应该通过reset_token找到对应的用户
	// 这里简化处理，假设通过其他方式获取了用户ID
	// 在实际应用中，应该通过中间件或其他方式获取用户ID

	// 假设我们通过某种方式获取了用户ID，这里使用示例值
	userID := uint(1) // 实际应用中应该从令牌或其他地方获取

	log.WithFields(log.Fields{
		"resetToken":    req.ResetToken,
		"userID":        userID,
		"newPasswordSet": true, // 不记录实际密码
	}).Debug("准备重置用户密码")

	if err := database.DB.Model(&models.User{}).Where("user_id = ?", userID).Update("password_hash", passwordHash).Error; err != nil {
		log.WithError(err).WithField("userID", userID).Error("密码更新失败")
		c.JSON(http.StatusInternalServerError, gin.H{"success": false, "message": "密码更新失败"})
		return
	}

	log.WithField("userID", userID).Info("密码重置成功")
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "密码已更新",
	})
}
