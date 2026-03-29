-- AI Video Matrix - Initial Schema
-- Covers: products, script variants, videos, accounts, content ledger, publish tasks

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Products
-- ============================================================
CREATE TABLE products (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    keywords    TEXT[],
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ============================================================
-- Script Variants (LLM-generated)
-- ============================================================
CREATE TYPE hook_type AS ENUM ('question', 'suspense', 'data', 'empathy');
CREATE TYPE style_type AS ENUM ('recommend', 'review', 'tutorial', 'story');
CREATE TYPE duration_type AS ENUM ('15s', '30s', '60s');
CREATE TYPE script_status AS ENUM (
    'pending', 'generating', 'ready', 'assigned', 'published', 'failed'
);

CREATE TABLE script_variants (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id        UUID         NOT NULL REFERENCES products(id),
    hook              hook_type    NOT NULL,
    style             style_type   NOT NULL,
    duration          duration_type NOT NULL,
    prompt_text       TEXT         NOT NULL,
    visual_desc       TEXT,
    tts_text          TEXT,
    fingerprint_hash  VARCHAR(64),
    status            script_status NOT NULL DEFAULT 'pending',
    assigned_account  UUID,
    assigned_platform VARCHAR(32),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_script_variants_product ON script_variants(product_id);
CREATE INDEX idx_script_variants_status  ON script_variants(status);

-- ============================================================
-- Videos (generated + mutated)
-- ============================================================
CREATE TYPE video_status AS ENUM (
    'generating', 'generated', 'mutating', 'ready',
    'queued', 'publishing', 'published', 'failed'
);

CREATE TABLE videos (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id        UUID          NOT NULL REFERENCES script_variants(id),
    source_video_id  UUID          REFERENCES videos(id),
    minio_key        VARCHAR(512)  NOT NULL,
    video_hash       VARCHAR(128),
    duration_seconds FLOAT,
    file_size_bytes  BIGINT,
    mutation_params  JSONB,
    status           video_status  NOT NULL DEFAULT 'generating',
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_videos_script  ON videos(script_id);
CREATE INDEX idx_videos_status  ON videos(status);
CREATE INDEX idx_videos_hash    ON videos(video_hash);

-- ============================================================
-- Accounts
-- ============================================================
CREATE TYPE platform_type AS ENUM ('douyin', 'kuaishou', 'xiaohongshu', 'weixin_channel');
CREATE TYPE account_status AS ENUM (
    'warming_up', 'active', 'cooling_down', 'banned', 'retired'
);

CREATE TABLE accounts (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform       platform_type   NOT NULL,
    username       VARCHAR(255)    NOT NULL,
    display_name   VARCHAR(255),
    status         account_status  NOT NULL DEFAULT 'warming_up',
    proxy_url      VARCHAR(512),
    profile_id     VARCHAR(255),
    cookie_data    TEXT,
    daily_limit    INT             NOT NULL DEFAULT 3,
    last_publish   TIMESTAMPTZ,
    banned_at      TIMESTAMPTZ,
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    UNIQUE (platform, username)
);

CREATE INDEX idx_accounts_platform_status ON accounts(platform, status);

-- ============================================================
-- Content Ledger (tracks which video went to which account)
-- ============================================================
CREATE TABLE content_ledger (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id     UUID          NOT NULL REFERENCES videos(id),
    account_id   UUID          NOT NULL REFERENCES accounts(id),
    platform     platform_type NOT NULL,
    video_hash   VARCHAR(128),
    published_at TIMESTAMPTZ,
    status       VARCHAR(32)   NOT NULL DEFAULT 'assigned',
    result       JSONB,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (video_id, account_id)
);

CREATE INDEX idx_ledger_platform_hash ON content_ledger(platform, video_hash);
CREATE INDEX idx_ledger_account       ON content_ledger(account_id);

-- ============================================================
-- Publish Tasks (queue items)
-- ============================================================
CREATE TYPE task_status AS ENUM (
    'pending', 'running', 'success', 'failed', 'retrying'
);

CREATE TABLE publish_tasks (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ledger_id     UUID        NOT NULL REFERENCES content_ledger(id),
    video_id      UUID        NOT NULL REFERENCES videos(id),
    account_id    UUID        NOT NULL REFERENCES accounts(id),
    platform      platform_type NOT NULL,
    title         VARCHAR(255),
    description   TEXT,
    tags          TEXT[],
    cover_key     VARCHAR(512),
    status        task_status NOT NULL DEFAULT 'pending',
    retry_count   INT         NOT NULL DEFAULT 0,
    max_retries   INT         NOT NULL DEFAULT 3,
    scheduled_at  TIMESTAMPTZ,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_status   ON publish_tasks(status);
CREATE INDEX idx_tasks_account  ON publish_tasks(account_id);
CREATE INDEX idx_tasks_schedule ON publish_tasks(scheduled_at) WHERE status = 'pending';

-- ============================================================
-- Metrics (for Grafana dashboards)
-- ============================================================
CREATE TABLE metrics (
    id         BIGSERIAL PRIMARY KEY,
    metric     VARCHAR(128) NOT NULL,
    value      FLOAT        NOT NULL,
    labels     JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metrics_name_time ON metrics(metric, recorded_at DESC);
