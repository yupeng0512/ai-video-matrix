# AI Video Matrix 运营系统

AI 驱动的视频矩阵运营系统——批量生成差异化产品营销视频，通过 100-1000 个账号自动发布到抖音、快手、小红书、视频号。

## 架构概览

```
n8n (编排) → content-planner (LLM脚本) → 视频API (生成)
    ↓
MinIO (存储) → video-mutator (FFmpeg变体+videohash校验)
    ↓
content-router (平台隔离路由) → Redis Queue → publisher workers
    ↓                                           ↓
PostgreSQL (台账)                    Playwright + CloakBrowser
```

## 域名访问（Traefik 网关）

所有 Web UI 通过 Traefik 统一域名访问，无需记忆端口号：

| 域名 | 服务 | 用途 |
|------|------|------|
| `vm-n8n.dev.local` | n8n | 全链路编排面板 |
| `vm-mpt.dev.local` | MoneyPrinterTurbo | LLM+FFmpeg 视频生成 |
| `vm-minio.dev.local` | MinIO Console | 视频文件管理 |
| `vm-grafana.dev.local` | Grafana | 监控看板 |
| `vm-rabbitmq.dev.local` | RabbitMQ Management | 消息队列管理 |

**Mac 远程访问**：在 Mac 的 `/etc/hosts` 添加一行：

```bash
9.135.86.144 vm-n8n.dev.local vm-mpt.dev.local vm-minio.dev.local vm-grafana.dev.local vm-rabbitmq.dev.local
```

后端微服务（content-planner, video-mutator, content-router, publisher）只在内部网络运行，通过 `docker compose exec` 或 n8n 编排访问。

### 保留的本机端口（127.0.0.1，仅调试用）

| 端口 | 服务 | 协议 |
|------|------|------|
| 5434 | PostgreSQL | postgresql |
| 6381 | Redis | redis |
| 5673 | RabbitMQ | amqp |

## 快速开始

```bash
# 1. 复制并编辑环境变量
cp .env.example .env
vi .env   # 填入 DEEPSEEK_API_KEY 和 KLING_API_KEY

# 2. 一键部署
make setup

# 3. 查看可用域名
make domains

# 4. 健康检查
make health

# 5. 创建产品（通过 docker exec）
docker compose exec -T content-planner wget -qO- \
  --post-data='{"name":"智能手表","description":"高端智能手表","keywords":["智能","手表"]}' \
  --header='Content-Type: application/json' \
  http://localhost:8000/products

# 6. 导入 n8n 工作流
# 打开 http://vm-n8n.dev.local → Import → n8n-workflows/video-matrix-pipeline.json
```

## Test Harness（零成本端到端测试）

内置测试环境，用 Mock 服务替代真实 API，实现零成本全链路验证。

```bash
# 一键启动测试环境（包含 mock-kling-api + mock-platform + 种子数据）
make test-harness-up

# 运行全部 5 个 E2E 测试
make test-harness-run

# 清理测试环境
make test-harness-down
```

### 测试覆盖

| 测试 | 飞轮齿轮 | 验证内容 |
|------|---------|---------|
| test_01 | Gear 1: 脚本差异化 | LLM 生成多样化脚本 |
| test_02 | Gear 2: 视频变异 | FFmpeg 变异 + 哈希校验 |
| test_03 | Gear 4: 平台隔离 | 同平台去重 + 跨平台复用 |
| test_04 | Gear 5: 账号生命周期 | 健康检查 + 冷却/恢复 |
| test_05 | 跨齿轮 | Mock API + 上传流程 |

### 测试模式

- `TEST_MODE=mock`（默认）：使用 Mock 服务，零 API 调用成本
- `TEST_MODE=real`：调用真实 API（可灵 + DeepSeek），用于上线前验证

## 核心特性

### 视频去重（五维变异）

| 维度 | 手段 | 实现 |
|------|------|------|
| 像素级 | 分辨率/帧率/码率微调 | FFmpeg |
| 画面级 | 滤镜/色调/裁剪 | FFmpeg/OpenCV |
| 音频级 | 声线/语速/BGM | CosyVoice+FFmpeg |
| 结构级 | 片头片尾/过渡效果 | FFmpeg concat |
| 元数据级 | 标题/描述/标签 | LLM 生成 |

变体后通过 videohash 感知哈希校验，相似度 ≥70% 自动退回重新变异。

### 平台隔离路由

- **同平台隔离**：同一平台的不同账号绝不分配相同视频
- **跨平台复用**：允许不同平台间复用（经过重新变异）
- **内容台账**：全量记录分配历史，作为去重依据

### 账号生命周期

`warming_up → active → cooling_down → active / banned → retired`

自动健康检查 → 失败率 >50% 自动降温 → 24h 后自动恢复

## 常用命令

```bash
make start           # 启动所有服务
make stop            # 停止所有服务
make logs            # 查看日志
make domains         # 显示所有域名路由
make health          # 服务健康检查
make stats           # 查看发布统计
make accounts        # 查看账号列表
make db-shell        # 进入数据库
make stress-test     # 压力测试 (30min)
make test-harness-run # E2E 测试
make clean           # 清理所有数据（危险）
```

## 网络隔离

```
            ┌─── traefik-net ──────────────────────┐
            │                                      │
         Traefik    n8n   MoneyPrinter   MinIO   Grafana   RabbitMQ
            │       (桥接点)                                 (mgmt)
            └──────────────────────────────────────┘
                        │
            ┌─── internal ─────────────────────────┐
            │                                      │
     content-planner  video-mutator  content-router  publisher
            │
     ┌──────┼──────┐
  postgres  redis  rabbitmq  minio
```

- **traefik-net**：仅 Web UI 面向用户的服务
- **internal**：所有后端微服务 + 数据存储，出站 HTTPS 不被 Traefik 拦截

## 渐进式落地

| Phase | 目标 | 时间 |
|-------|------|------|
| 1 | MVP 验证（1 账号 1 平台） | 3 周 |
| 2 | 单平台自动化（5 账号） | 4 周 |
| 3 | 多平台 80 账号 | 8 周 |
| 4 | 千级规模化运营 | 12 周 |

## 技术栈

Python 3.12 / FastAPI / Playwright / FFmpeg / PostgreSQL / Redis / RabbitMQ / MinIO / n8n / Docker Compose / Traefik
