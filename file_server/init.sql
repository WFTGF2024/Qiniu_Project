CREATE TABLE IF NOT EXISTS user_permanent_files (
    file_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL, 
    filename VARCHAR(255) NOT NULL,
    filepath TEXT NOT NULL,
    size BIGINT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_time (uploaded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
