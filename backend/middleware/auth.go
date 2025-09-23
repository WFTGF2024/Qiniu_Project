package middleware

import (
	"net/http"
	"strings"

	"qiniu_project/backend/utils"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// JWTAuthMiddleware JWT认证中间件
func JWTAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		log.Info("开始JWT认证中间件处理")

		// 从请求头获取Authorization字段
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			log.Warn("未提供认证令牌")
			c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "未提供认证令牌"})
			c.Abort()
			return
		}

		log.WithField("authHeader", authHeader).Debug("获取到认证令牌")

		// 检查Bearer格式
		parts := strings.SplitN(authHeader, " ", 2)
		if !(len(parts) == 2 && parts[0] == "Bearer") {
			log.Warn("令牌格式错误")
			c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "令牌格式错误"})
			c.Abort()
			return
		}

		// 解析JWT令牌
		tokenString := parts[1]
		userID, err := utils.ParseJWTToken(tokenString)
		if err != nil {
			log.WithError(err).WithField("tokenString", tokenString).Warn("令牌无效")
			c.JSON(http.StatusUnauthorized, gin.H{"success": false, "message": "令牌无效"})
			c.Abort()
			return
		}

		log.WithFields(log.Fields{
			"userID":    userID,
			"token":     tokenString,
			"method":   c.Request.Method,
			"path":     c.Request.URL.Path,
			"clientIP": c.ClientIP(),
		}).Info("JWT认证成功")

		// 将用户ID存储在上下文中
		c.Set("user_id", userID)
		c.Next()
	}
}
