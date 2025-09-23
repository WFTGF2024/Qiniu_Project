package main

import (
	"flag"
	"fmt"
	"net/http"
	_ "net/http/pprof"
	"os"
	"path/filepath"

	"qiniu_project/backend/database"
	"qiniu_project/backend/handlers"
	"qiniu_project/backend/middleware"

	"github.com/gin-gonic/gin"
	_ "github.com/go-sql-driver/mysql"
	log "github.com/sirupsen/logrus"
	"gopkg.in/yaml.v3"
)

type Config struct {
	MySQL struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
		Database string `yaml:"database"`
	} `yaml:"mysql"`

	AppLogFile string `yaml:"app_log_file"`
	ServerPort int    `yaml:"server_port"`
}

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

func setupRouter() *gin.Engine {
	// 设置Gin模式
	gin.SetMode(gin.ReleaseMode)

	// 创建路由
	r := gin.New()

	// 添加中间件
	r.Use(gin.Logger())
	r.Use(gin.Recovery())

	// 设置CORS中间件
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// 创建API路由组
	api := r.Group("/api")

	// 认证相关路由
	auth := api.Group("/auth")
	{
		// 用户注册
		auth.POST("/register", handlers.Register)

		// 用户登录
		auth.POST("/login", handlers.Login)

		// 验证密保问题
		auth.POST("/verify-security", handlers.VerifySecurity)

		// 重置密码
		auth.POST("/reset-password", handlers.ResetPassword)

		// 获取用户信息（需要认证）
		auth.GET("/me", middleware.JWTAuthMiddleware(), handlers.GetProfile)
	}

	// 用户管理路由（需要认证）
	users := api.Group("/users")
	users.Use(middleware.JWTAuthMiddleware())
	{
		// 更新用户信息
		users.PUT("/:user_id", handlers.UpdateUser)

		// 删除用户
		users.DELETE("/:user_id", handlers.DeleteUser)
	}

	return r
}

func main() {
	// 解析命令行参数
	configPath := flag.String("r", "", "配置文件绝对路径 (必填)")
	flag.Parse()

	// 参数校验
	if *configPath == "" {
		log.Fatal("错误: 必须通过 -r 参数指定配置文件绝对路径")
	}

	// 初始化logrus
	log.SetFormatter(&log.JSONFormatter{})
	log.SetOutput(os.Stdout)
	log.SetLevel(log.InfoLevel)

	// 启动HTTP服务器以支持pprof性能分析
	go func() {
		if err := http.ListenAndServe("127.0.0.1:6060", nil); err != nil {
			log.Fatalf("启动pprof HTTP服务器失败: %v", err)
		}
	}()

	// 1. 加载配置文件
	config, err := loadConfig(*configPath)
	if err != nil {
		log.Fatalf("加载配置文件失败: %v", err)
	}

	// 设置运行时日志输出到指定的日志文件
	if err := os.MkdirAll(filepath.Dir(config.AppLogFile), 0755); err != nil {
		log.Fatalf("创建日志目录失败: %v", err)
	}

	f, err := os.OpenFile(config.AppLogFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		log.Fatalf("打开日志文件失败: %v", err)
	}
	defer f.Close()

	log.SetOutput(f)

	// 2. 初始化数据库连接
	database.InitDB()

	// 3. 设置路由
	router := setupRouter()

	// 设置服务器端口，如果配置中没有设置则使用默认值8080
	serverPort := config.ServerPort
	if serverPort == 0 {
		serverPort = 8080
	}

	// 启动HTTP服务器
	serverAddr := fmt.Sprintf(":%d", serverPort)
	log.Infof("服务器启动，监听地址: %s", serverAddr)

	if err := router.Run(serverAddr); err != nil {
		log.Fatalf("启动服务器失败: %v", err)
	}
}
