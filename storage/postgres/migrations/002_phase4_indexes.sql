-- Phase 4 performance optimizations for 200-1000 account scale.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ledger_created_status
    ON content_ledger(created_at DESC, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_pending_scheduled
    ON publish_tasks(scheduled_at, created_at)
    WHERE status IN ('pending', 'retrying');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_active_platform
    ON accounts(platform, last_publish)
    WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_ready
    ON videos(created_at DESC)
    WHERE status = 'ready';

-- Partitioned metrics table for Grafana queries at scale
CREATE TABLE IF NOT EXISTS metrics_hourly (
    hour        TIMESTAMPTZ NOT NULL,
    platform    VARCHAR(32) NOT NULL,
    metric      VARCHAR(64) NOT NULL,
    value       FLOAT       NOT NULL DEFAULT 0,
    PRIMARY KEY (hour, platform, metric)
);

-- Materialized view for dashboard queries
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_stats AS
SELECT
    date_trunc('day', cl.created_at) as day,
    cl.platform,
    COUNT(*) FILTER (WHERE cl.status = 'published') as published,
    COUNT(*) FILTER (WHERE cl.status = 'failed') as failed,
    COUNT(DISTINCT cl.account_id) as active_accounts,
    COUNT(DISTINCT cl.video_id) as unique_videos
FROM content_ledger cl
WHERE cl.created_at >= now() - interval '90 days'
GROUP BY 1, 2;

CREATE UNIQUE INDEX ON mv_daily_stats(day, platform);
