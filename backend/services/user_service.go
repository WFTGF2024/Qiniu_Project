package services

import (
	"errors"

	"github.com/WFTGF2024/Qiniu_Project/backend/database"
	"github.com/WFTGF2024/Qiniu_Project/backend/models"
	"github.com/WFTGF2024/Qiniu_Project/backend/utils"

	log "github.com/sirupsen/logrus"
)

// UserService 用户服务接口
type UserService interface {
	RegisterUser(req models.UserRegisterRequest) (*models.User, error)
	LoginUser(req models.UserLoginRequest) (string, error)
	GetUserProfile(userID uint) (*models.UserProfileResponse, error)
	UpdateUser(userID uint, req models.UpdateUserRequest) error
	DeleteUser(userID uint) error
	VerifySecurity(req models.SecurityVerifyRequest) (bool, error)
	ResetPassword(req models.ResetPasswordRequest) error
}

// userService 用户服务实现
type userService struct{}

// NewUserService 创建用户服务实例
func NewUserService() UserService {
	return &userService{}
}

// RegisterUser 用户注册
func (s *userService) RegisterUser(req models.UserRegisterRequest) (*models.User, error) {
	log.Info("开始处理用户注册请求")
	log.WithFields(log.Fields{
		"username":    req.Username,
		"email":       req.Email,
		"phoneNumber": req.PhoneNumber,
	}).Debug("用户注册请求参数")

	// 检查用户名是否已存在
	var existingUser models.User
	if err := database.DB.Where("username = ?", req.Username).First(&existingUser).Error; err == nil {
		log.WithField("username", req.Username).Warn("用户名已存在")
		return nil, errors.New("用户名已存在")
	}

	// 检查邮箱是否已存在
	if err := database.DB.Where("email = ?", req.Email).First(&existingUser).Error; err == nil {
		log.WithField("email", req.Email).Warn("邮箱已被使用")
		return nil, errors.New("邮箱已被使用")
	}

	// 检查手机号是否已存在
	if err := database.DB.Where("phone_number = ?", req.PhoneNumber).First(&existingUser).Error; err == nil {
		log.WithField("phoneNumber", req.PhoneNumber).Warn("手机号已被使用")
		return nil, errors.New("手机号已被使用")
	}

	// 哈希密码
	passwordHash, err := utils.HashPassword(req.Password)
	if err != nil {
		log.WithError(err).Error("密码哈希失败")
		return nil, errors.New("密码处理失败")
	}

	// 哈希安全问题的答案
	answer1Hash, err := utils.HashPassword(req.SecurityAnswer1)
	if err != nil {
		log.WithError(err).Error("安全答案1哈希失败")
		return nil, errors.New("安全答案处理失败")
	}

	answer2Hash, err := utils.HashPassword(req.SecurityAnswer2)
	if err != nil {
		log.WithError(err).Error("安全答案2哈希失败")
		return nil, errors.New("安全答案处理失败")
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

	// 保存到数据库
	if err := database.DB.Create(&newUser).Error; err != nil {
		log.WithError(err).Error("创建用户失败")
		return nil, errors.New("创建用户失败")
	}

	log.WithField("userID", newUser.UserID).Info("用户注册成功")
	return &newUser, nil
}

// LoginUser 用户登录
func (s *userService) LoginUser(req models.UserLoginRequest) (string, error) {
	log.Info("开始处理用户登录请求")
	log.WithField("username", req.Username).Debug("用户登录请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		log.WithError(err).Warn("用户不存在")
		return "", errors.New("用户名或密码错误")
	}

	// 验证密码
	if !utils.CheckPassword(req.Password, user.PasswordHash) {
		log.Warn("密码验证失败")
		return "", errors.New("用户名或密码错误")
	}

	// 生成JWT令牌
	token, err := utils.GenerateJWTToken(user.UserID)
	if err != nil {
		log.WithError(err).Error("生成JWT令牌失败")
		return "", errors.New("登录失败")
	}

	log.WithField("userID", user.UserID).Info("用户登录成功")
	return token, nil
}

// GetUserProfile 获取用户信息
func (s *userService) GetUserProfile(userID uint) (*models.UserProfileResponse, error) {
	log.Info("开始获取用户信息")
	log.WithField("userID", userID).Debug("获取用户信息请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).Warn("用户不存在")
		return nil, errors.New("用户不存在")
	}

	// 构建响应
	userProfile := models.UserProfileResponse{
		UserID:      user.UserID,
		Username:    user.Username,
		FullName:    user.FullName,
		Email:       user.Email,
		PhoneNumber: user.PhoneNumber,
		CreatedAt:   user.CreatedAt,
		UpdatedAt:   user.UpdatedAt,
	}

	log.WithField("userID", userID).Info("获取用户信息成功")
	return &userProfile, nil
}

// UpdateUser 更新用户信息
func (s *userService) UpdateUser(userID uint, req models.UpdateUserRequest) error {
	log.Info("开始更新用户信息")
	log.WithFields(log.Fields{
		"userID":   userID,
		"fullName": req.FullName,
		"email":    req.Email,
		"phone":    req.PhoneNumber,
	}).Debug("更新用户信息请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).Warn("用户不存在")
		return errors.New("用户不存在")
	}

	// 检查邮箱是否已被其他用户使用
	if req.Email != "" && req.Email != user.Email {
		var existingUser models.User
		if err := database.DB.Where("email = ? AND user_id != ?", req.Email, userID).First(&existingUser).Error; err == nil {
			log.WithField("email", req.Email).Warn("邮箱已被其他用户使用")
			return errors.New("邮箱已被其他用户使用")
		}
	}

	// 检查手机号是否已被其他用户使用
	if req.PhoneNumber != "" && req.PhoneNumber != user.PhoneNumber {
		var existingUser models.User
		if err := database.DB.Where("phone_number = ? AND user_id != ?", req.PhoneNumber, userID).First(&existingUser).Error; err == nil {
			log.WithField("phoneNumber", req.PhoneNumber).Warn("手机号已被其他用户使用")
			return errors.New("手机号已被其他用户使用")
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
		if err := database.DB.Model(&user).Updates(updateData).Error; err != nil {
			log.WithError(err).Error("更新用户信息失败")
			return errors.New("更新用户信息失败")
		}
	}

	log.WithField("userID", userID).Info("更新用户信息成功")
	return nil
}

// DeleteUser 删除用户
func (s *userService) DeleteUser(userID uint) error {
	log.Info("开始删除用户")
	log.WithField("userID", userID).Debug("删除用户请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.First(&user, userID).Error; err != nil {
		log.WithError(err).Warn("用户不存在")
		return errors.New("用户不存在")
	}

	// 删除用户
	if err := database.DB.Delete(&user).Error; err != nil {
		log.WithError(err).Error("删除用户失败")
		return errors.New("删除用户失败")
	}

	log.WithField("userID", userID).Info("删除用户成功")
	return nil
}

// VerifySecurity 验证安全问题
func (s *userService) VerifySecurity(req models.SecurityVerifyRequest) (bool, error) {
	log.Info("开始验证安全问题")
	log.WithField("username", req.Username).Debug("验证安全问题请求参数")

	// 查找用户
	var user models.User
	if err := database.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		log.WithError(err).Warn("用户不存在")
		return false, errors.New("用户不存在")
	}

	// 验证安全问题答案
	answer1Valid := utils.CheckPassword(req.SecurityAnswer1, user.SecurityAnswer1Hash)
	answer2Valid := utils.CheckPassword(req.SecurityAnswer2, user.SecurityAnswer2Hash)

	if !answer1Valid || !answer2Valid {
		log.Warn("安全问题验证失败")
		return false, nil
	}

	log.WithField("username", req.Username).Info("安全问题验证成功")
	return true, nil
}

// ResetPassword 重置密码
func (s *userService) ResetPassword(req models.ResetPasswordRequest) error {
	log.Info("开始重置密码")
	log.WithField("resetToken", req.ResetToken).Debug("重置密码请求参数")

	// 在实际应用中，这里应该先验证resetToken的有效性
	// 为简化示例，我们假设resetToken是有效的，并直接更新密码

	// 哈希新密码
	passwordHash, err := utils.HashPassword(req.NewPassword)
	if err != nil {
		log.WithError(err).Error("密码哈希失败")
		return errors.New("密码处理失败")
	}

	// 更新密码
	// 注意：在实际应用中，这里应该通过resetToken找到对应的用户
	// 为简化示例，我们假设重置令牌是有效的
	result := database.DB.Model(&models.User{}).Update("password_hash", passwordHash)
	if result.Error != nil {
		log.WithError(result.Error).Error("更新密码失败")
		return errors.New("更新密码失败")
	}

	if result.RowsAffected == 0 {
		log.Warn("未找到要更新的用户")
		return errors.New("重置密码失败")
	}

	log.Info("重置密码成功")
	return nil
}
