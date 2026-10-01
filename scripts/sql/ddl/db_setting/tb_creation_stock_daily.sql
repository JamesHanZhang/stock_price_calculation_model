CREATE TABLE IF NOT EXISTS `stock_daily` (
  `ts_code` varchar(32) NOT NULL COMMENT '股票代码',
  `trade_date` varchar(12) NOT NULL COMMENT '交易日期 YYYYMMDD',
  `open` decimal(12,4) DEFAULT NULL COMMENT '开盘价',
  `high` decimal(12,4) DEFAULT NULL COMMENT '最高价',
  `low` decimal(12,4) DEFAULT NULL COMMENT '最低价',
  `close` decimal(12,4) DEFAULT NULL COMMENT '收盘价',
  `pre_close` decimal(12,4) DEFAULT NULL COMMENT '前一日收盘价',
  `change` decimal(12,4) DEFAULT NULL COMMENT '涨跌额',
  `pct_chg` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
  `vol` decimal(16,2) DEFAULT NULL COMMENT '成交量 手',
  `amount` decimal(18,2) DEFAULT NULL COMMENT '成交额 元',
  PRIMARY KEY (`ts_code`,`trade_date`),
  KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日线行情表(来自tushare)';