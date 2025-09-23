package utils

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v4"
	"golang.org/x/crypto/bcrypt"
	log "github.com/sirupsen/logrus"
)

// JWTSecret JWT密钥
var JWTSecret = []byte("your-secret-key") // 在实际应用中应该从配置文件中读取

// HashPassword 使用bcrypt哈希密码
func HashPassword(password string) (string, error) {
	log.WithField("passwordLength", len(password)).Debug("开始密码哈希处理")

	bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		log.WithError(err).Error("密码哈希失败")
		return "", err
	}

	log.Debug("密码哈希成功")
	return string(bytes), nil
}

// CheckPassword 验证密码
func CheckPassword(password, hash string) bool {
	log.WithFields(log.Fields{
		"passwordLength": len(password),
		"hashLength":    len(hash),
	}).Debug("开始密码验证")

	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	if err != nil {
		log.WithError(err).Debug("密码验证失败")
		return false
	}

	log.Debug("密码验证成功")
	return true
}

// GenerateJWTToken 生成JWT令牌
func GenerateJWTToken(userID uint) (string, error) {
	log.WithField("userID", userID).Debug("开始生成JWT令牌")

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"user_id": userID,
		"exp":     time.Now().Add(time.Hour * 24).Unix(), // 24小时过期
	})

	tokenString, err := token.SignedString(JWTSecret)
	if err != nil {
		log.WithError(err).Error("JWT令牌签名失败")
		return "", err
	}

	log.WithFields(log.Fields{
		"userID":    userID,
		"token":     tokenString,
		"expiresAt": time.Now().Add(time.Hour * 24).Format(time.RFC3339),
	}).Debug("JWT令牌生成成功")

	return tokenString, nil
}

// ParseJWTToken 解析JWT令牌
func ParseJWTToken(tokenString string) (uint, error) {
	log.WithField("token", tokenString).Debug("开始解析JWT令牌")

	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// 验证签名方法
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			log.WithField("signingMethod", token.Method.Alg()).Warn("意外的签名方法")
			return nil, errors.New("unexpected signing method")
		}
		return JWTSecret, nil
	})

	if err != nil {
		log.WithError(err).Error("JWT令牌解析失败")
		return 0, err
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		userID := uint(claims["user_id"].(float64))
		expiresAt := time.Unix(int64(claims["exp"].(float64)), 0)

		log.WithFields(log.Fields{
			"userID":    userID,
			"token":     tokenString,
			"expiresAt": expiresAt.Format(time.RFC3339),
		}).Debug("JWT令牌解析成功")

		return userID, nil
	}

	log.Error("无效的JWT令牌")
	return 0, errors.New("invalid token")
}

// GenerateResetToken 生成重置密码令牌
func GenerateResetToken() string {
	bytes := make([]byte, 16)
	rand.Read(bytes)
	return hex.EncodeToString(bytes)
}
