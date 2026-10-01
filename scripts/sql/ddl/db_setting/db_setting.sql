-- 登陆 rooty用户
mysql -u root -p

-- 搭建专属数据库
CREATE DATABASE IF NOT EXISTS stock_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SHOW DATABASES;

-- 创建仅本机访问账号
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY 'MyPass123!';

-- 授予stock_db库下面所有表全部权限
GRANT ALL PRIVILEGES ON stock_db.* TO 'stock_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 更改密码，此处新密码自己记录，不体现在代码上
ALTER USER 'stock_user'@'localhost' IDENTIFIED BY '新密码';
FLUSH PRIVILEGES;

-- 退出root
exit;

-- 登陆数据库
mysql -u stock_user -p stock_db