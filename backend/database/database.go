package database

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"qiniu_project/backend/models"
)

// DB 全局数据库连接对象
var DB *gorm.DB

// Config 配置结构体
type Config struct {
	MySQL struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
		Database string `yaml:"database"`
	} `yaml:"mysql"`

	AppLogFile string `yaml:"app_log_file"`
}

// InitDB 初始化数据库连接
func InitDB() {
	// 获取配置文件路径
	configPath := filepath.Join("..", "..", "config.yaml")

	// 加载配置
	config, err := loadConfig(configPath)
	if err != nil {
		log.Fatalf("加载配置文件失败: %v", err)
	}

	// 连接MySQL数据库
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		config.MySQL.User, config.MySQL.Password, config.MySQL.Host, config.MySQL.Port, config.MySQL.Database)

	// 配置GORM日志
	newLogger := logger.Default.LogMode(logger.Info)

	// 连接数据库
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		log.Fatalf("连接MySQL失败: %v", err)
	}

	// 设置全局数据库连接
	DB = db

	// 自动迁移数据库表
	err = autoMigrate(db)
	if err != nil {
		log.Fatalf("数据库迁移失败: %v", err)
	}

	log.Println("数据库连接和初始化成功")
}

// loadConfig 加载配置文件
func loadConfig(filePath string) (*Config, error) {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, err
	}

	configData, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var config Config
	err = yaml.Unmarshal(configData, &config)
	if err != nil {
		return nil, err
	}

	return &config, nil
}

// autoMigrate 自动迁移数据库表
func autoMigrate(db *gorm.DB) error {
	err := db.AutoMigrate(
		&models.User{},
	)
	if err != nil {
		return err
	}

	log.Println("数据库表迁移成功")
	return nil
}
