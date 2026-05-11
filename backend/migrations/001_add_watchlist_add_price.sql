-- Migration: Add add_price column to watchlist_item table
-- Date: 2026-05-10
-- Description: 记录添加自选股时的价格，用于计算自选涨幅

ALTER TABLE t_watchlist_item
  ADD COLUMN add_price DECIMAL(10, 3) NULL COMMENT '自选价（添加时价格）'
  AFTER stock_name;
