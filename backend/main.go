package main

import (
	"flag"
	"fmt"
	"net/http"
	_ "net/http/pprof"
	"os"
	"path/filepath"

	"github.com/WFTGF2024/Qiniu_Project/backend/config"
	"github.com/WFTGF2024/Qiniu_Project/backend/database"
	"github.com/WFTGF2024/Qiniu_Project/backend/handlers"
	"github.com/WFTGF2024/Qiniu_Project/backend/middleware"

	"github.com/gin-gonic/gin"
	_ "github.com/go-sql-driver/mysql"
	log "github.com/sirupsen/logrus"
)

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

	// 会员管理路由
	membership := api.Group("/membership")
	{
		// 查询会员信息
		membership.GET("/:user_id", handlers.GetMembershipInfo)

		// 查询所有会员信息
		membership.GET("", handlers.GetAllMemberships)

		// 新增会员信息
		membership.POST("", handlers.CreateMembership)

		// 更新会员信息
		membership.PUT("/:membership_id", handlers.UpdateMembership)

		// 删除会员信息
		membership.DELETE("/:membership_id", handlers.DeleteMembership)
	}

	// 会员订单管理路由
	orders := api.Group("/membership/orders")
	{
		// 查询会员订单记录
		orders.GET("/:user_id", handlers.GetMembershipOrders)

		// 新增订单
		orders.POST("", handlers.CreateOrder)

		// 查询最近一条订单
		orders.GET("/:user_id/latest", handlers.GetLatestOrder)

		// 查询最近N条订单
		orders.GET("/:user_id/recent", handlers.GetRecentOrders)
	}

	return r
}

func main() {
	log.Info("应用程序启动...")

	// 解析命令行参数
	configPath := flag.String("r", "", "配置文件绝对路径 (必填)")
	flag.Parse()

	log.WithField("configPath", *configPath).Info("解析命令行参数")

	// 参数校验
	if *configPath == "" {
		log.Fatal("错误: 必须通过 -r 参数指定配置文件绝对路径")
	}

	// 初始化logrus
	log.Info("初始化日志系统...")
	log.SetFormatter(&log.JSONFormatter{})
	log.SetOutput(os.Stdout)
	log.SetLevel(log.InfoLevel)

	// 启动HTTP服务器以支持pprof性能分析
	go func() {
		log.Info("启动pprof性能分析服务器，监听地址: 127.0.0.1:6060")
		if err := http.ListenAndServe("127.0.0.1:6060", nil); err != nil {
			log.WithError(err).Fatal("启动pprof HTTP服务器失败")
		}
	}()

	// 1. 加载配置文件
	log.Info("开始加载配置文件...")
	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		log.WithError(err).Fatal("加载配置文件失败")
	}

	log.WithFields(log.Fields{
		"mysql_host":     cfg.MySQL.Host,
		"mysql_port":     cfg.MySQL.Port,
		"mysql_user":     cfg.MySQL.User,
		"mysql_database": cfg.MySQL.Database,
		"app_log_file":   cfg.AppLogFile,
		"server_port":    cfg.ServerPort,
	}).Info("配置文件加载成功")

	// 设置运行时日志输出到指定的日志文件
	log.Info("设置日志输出到文件...")
	if err := os.MkdirAll(filepath.Dir(cfg.AppLogFile), 0755); err != nil {
		log.WithError(err).Fatal("创建日志目录失败")
	}

	f, err := os.OpenFile(cfg.AppLogFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		log.WithError(err).Fatal("打开日志文件失败")
	}
	defer f.Close()

	log.SetOutput(f)
	log.Info("日志系统配置完成")

	// 2. 初始化数据库连接
	log.Info("初始化数据库连接...")
	database.InitDB()

	// 3. 设置路由
	log.Info("设置HTTP路由...")
	router := setupRouter()

	// 设置服务器端口，如果配置中没有设置则使用默认值8080
	serverPort := cfg.ServerPort
	if serverPort == 0 {
		serverPort = 8080
		log.Info("使用默认服务器端口: 8080")
	} else {
		log.WithField("serverPort", serverPort).Info("使用配置的服务器端口")
	}

	// 启动HTTP服务器
	serverAddr := fmt.Sprintf(":%d", serverPort)
	log.WithField("serverAddr", serverAddr).Info("启动HTTP服务器")

	if err := router.Run(serverAddr); err != nil {
		log.WithError(err).Fatal("启动服务器失败")
	}
}
