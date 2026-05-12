-- Migration: Add event radar tables (Module 4)
-- Date: 2026-05-12
-- Description: 新增 6 张表，支撑投资事件影响雷达功能

-- 1. 影响事件表（全局共享，不按用户区分）
CREATE TABLE IF NOT EXISTS t_impact_event (
    event_id       BIGINT        NOT NULL AUTO_INCREMENT,
    title          VARCHAR(200)  NOT NULL                          COMMENT '事件标题',
    summary        VARCHAR(500)  NULL                              COMMENT 'AI 生成摘要',
    event_type     VARCHAR(20)   NULL                              COMMENT 'geopolitical/policy/earnings/industry/macro/other',
    sentiment      VARCHAR(10)   NULL                              COMMENT 'positive/negative/neutral',
    importance     VARCHAR(10)   NULL                              COMMENT 'high/medium/low',
    affected_industries JSON     NULL                              COMMENT '关联行业列表 [{name, direction}]',
    affected_stocks JSON         NULL                              COMMENT '关联股票列表 [{code, name, direction, confidence, reason}]',
    source_count   INT           NOT NULL DEFAULT 1                COMMENT '来源数量（≥3 标记为热点）',
    first_seen_at  DATETIME      NOT NULL                          COMMENT '首次发现时间',
    last_seen_at   DATETIME      NOT NULL                          COMMENT '最后更新时间',
    is_active      TINYINT       NOT NULL DEFAULT 1                COMMENT '是否仍在活跃影响中（1=活跃, 0=归档）',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    INDEX idx_first_seen (first_seen_at),
    INDEX idx_event_type (event_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='影响事件表';

-- 2. 事件原始报道表（多对一关联 t_impact_event）
CREATE TABLE IF NOT EXISTS t_impact_article (
    article_id   BIGINT        NOT NULL AUTO_INCREMENT,
    event_id     BIGINT        NOT NULL                          COMMENT '关联事件 ID',
    title        VARCHAR(200)  NOT NULL                          COMMENT '报道标题',
    content      VARCHAR(500)  NULL                              COMMENT '摘要（≤500字）',
    source       VARCHAR(50)   NOT NULL                          COMMENT '来源网站（cls/tavily/anspire/bocha）',
    url          VARCHAR(500)  NOT NULL                          COMMENT '原始 URL',
    url_hash     VARCHAR(32)   NOT NULL                          COMMENT 'URL MD5（去重用）',
    published_at DATETIME      NULL                              COMMENT '原文发布时间',
    crawled_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    PRIMARY KEY (article_id),
    UNIQUE INDEX idx_url_hash (url_hash),
    INDEX idx_event_id (event_id),
    CONSTRAINT fk_article_event FOREIGN KEY (event_id) REFERENCES t_impact_event (event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件原始报道表';

-- 3. 用户影响关联表（每用户独立计算）
CREATE TABLE IF NOT EXISTS t_user_impact (
    id                 BIGINT  NOT NULL AUTO_INCREMENT,
    user_id            VARCHAR(32) NOT NULL                      COMMENT '用户 ID',
    event_id           BIGINT  NOT NULL                          COMMENT '事件 ID',
    matched_stocks     JSON    NULL                              COMMENT '匹配到的自选股 [{code, name, direction, confidence}]',
    matched_industries JSON    NULL                              COMMENT '匹配到的关注行业 [{name, direction}]',
    priority           VARCHAR(5) NOT NULL                       COMMENT 'P0/P1/P2',
    is_read            TINYINT NOT NULL DEFAULT 0                COMMENT '是否已读',
    is_alert_sent      TINYINT NOT NULL DEFAULT 0                COMMENT '是否已推送预警',
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_priority (user_id, priority),
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_event_id (event_id),
    CONSTRAINT fk_impact_event FOREIGN KEY (event_id) REFERENCES t_impact_event (event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户影响关联表';

-- 4. 预警记录表（仅 P0/P1 级别）
CREATE TABLE IF NOT EXISTS t_user_alert (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    user_id         VARCHAR(32)  NOT NULL                        COMMENT '用户 ID',
    user_impact_id  BIGINT       NOT NULL                        COMMENT '关联用户影响记录',
    priority        VARCHAR(5)   NOT NULL                        COMMENT 'P0/P1',
    title           VARCHAR(200) NOT NULL                        COMMENT '预警标题',
    summary         VARCHAR(500) NULL                            COMMENT '预警摘要',
    is_read         TINYINT      NOT NULL DEFAULT 0              COMMENT '是否已读',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_created (created_at),
    CONSTRAINT fk_alert_impact FOREIGN KEY (user_impact_id) REFERENCES t_user_impact (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警记录表';

-- 5. 影响晨报表（每用户每天一份）
CREATE TABLE IF NOT EXISTS t_morning_briefing (
    id             BIGINT       NOT NULL AUTO_INCREMENT,
    user_id        VARCHAR(32)  NOT NULL                         COMMENT '用户 ID',
    briefing_date  DATE         NOT NULL                         COMMENT '晨报日期',
    ai_summary     VARCHAR(200) NULL                             COMMENT 'AI 一句话总结',
    content        JSON         NOT NULL                         COMMENT '结构化内容（impact_events, portfolio_overview, today_focus）',
    is_read        TINYINT      NOT NULL DEFAULT 0               COMMENT '是否已读',
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE INDEX uq_user_briefing_date (user_id, briefing_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='影响晨报表';

-- 6. 用户雷达配置表
CREATE TABLE IF NOT EXISTS t_radar_config (
    id                  BIGINT      NOT NULL AUTO_INCREMENT,
    user_id             VARCHAR(32) NOT NULL UNIQUE              COMMENT '用户 ID',
    focused_industries  JSON        NULL                         COMMENT '关注行业列表 ["电力设备", "石油石化"]',
    event_types         JSON        NULL                         COMMENT '关注事件类型 ["policy", "earnings"]',
    alert_sensitivity   VARCHAR(10) NOT NULL DEFAULT 'medium'    COMMENT 'high/medium/low',
    quiet_hours_start   TIME        NULL                         COMMENT '免打扰开始时间',
    quiet_hours_end     TIME        NULL                         COMMENT '免打扰结束时间',
    updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户雷达配置表';
