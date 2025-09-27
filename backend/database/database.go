package database

import (
	"fmt"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"github.com/WFTGF2024/Qiniu_Project/backend/config"
	"github.com/WFTGF2024/Qiniu_Project/backend/models"

	log "github.com/sirupsen/logrus"
)

// DB 全局数据库连接对象
var DB *gorm.DB

// InitDB 初始化数据库连接
func InitDB() {
	log.Info("开始初始化数据库连接...")

	// 检查配置是否已加载
	if config.GlobalConfig == nil {
		log.Fatal("配置未初始化，请先调用 config.LoadConfig 加载配置")
	}

	log.WithFields(log.Fields{
		"host":     config.GlobalConfig.MySQL.Host,
		"port":     config.GlobalConfig.MySQL.Port,
		"user":     config.GlobalConfig.MySQL.User,
		"database": config.GlobalConfig.MySQL.Database,
	}).Info("准备连接MySQL数据库")

	// 连接MySQL数据库
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		config.GlobalConfig.MySQL.User, config.GlobalConfig.MySQL.Password,
		config.GlobalConfig.MySQL.Host, config.GlobalConfig.MySQL.Port,
		config.GlobalConfig.MySQL.Database)

	log.WithField("dsn", dsn).Debug("数据库连接字符串")

	// 配置GORM日志
	newLogger := logger.Default.LogMode(logger.Info)

	// 连接数据库
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		log.WithError(err).Fatal("连接MySQL失败")
	}

	// 设置全局数据库连接
	DB = db
	log.Info("数据库连接对象已创建")

	// 自动迁移数据库表
	log.Info("开始数据库表迁移...")
	err = autoMigrate(db)
	if err != nil {
		log.WithError(err).Fatal("数据库迁移失败")
	}

	log.Info("数据库连接和初始化成功")
}

// autoMigrate 自动迁移数据库表
func autoMigrate(db *gorm.DB) error {
	log.Info("开始数据库表迁移...")

	// 迁移表
	log.Info("正在迁移表...")
	err := db.AutoMigrate(
		&models.User{},
		&models.MembershipInfo{},
		&models.MembershipOrder{},
	)
	if err != nil {
		log.WithError(err).Error("数据库表迁移失败")
		return err
	}

	log.Info("数据库表迁移成功")
	return nil
}
