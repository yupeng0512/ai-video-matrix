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

| 服务 | 端口 | 职责 |
|------|------|------|
| n8n | 5678 | 全链路编排 |
| MoneyPrinterTurbo | 8501 | LLM+FFmpeg 视频生成 |
| content-planner | 8010 | LLM 脚本变体生成器 |
| video-mutator | 8011 | 五维视频变异 + 相似度校验 |
| content-router | 8012 | 平台隔离路由 + 账号管理 |
| publisher | 8013 | 多账号并发发布 |
| MinIO | 9000/9001 | 视频文件存储 |
| PostgreSQL | 5432 | 数据存储 |
| Redis | 6379 | 缓存/队列 |
| RabbitMQ | 5672/15672 | 消息队列 |
| Grafana | 3000 | 监控看板 |

## 快速开始

```bash
# 1. 复制并编辑环境变量
cp .env.example .env
vi .env

# 2. 一键部署
make setup

# 3. 健康检查
make health

# 4. 创建产品
curl -X POST http://localhost:8010/products \
  -H 'Content-Type: application/json' \
  -d '{"name":"智能手表", "description":"高端智能手表", "keywords":["智能","手表"]}'

# 5. 注册账号
python scripts/seed_accounts.py --all --count 5

# 6. 导入 n8n 工作流
# 打开 http://localhost:5678 → Import → n8n-workflows/video-matrix-pipeline.json
```

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
make stats           # 查看发布统计
make accounts        # 查看账号列表
make stress-test     # 运行压力测试 (30min)
make stress-test-full # 运行压力测试 (72h)
make db-shell        # 进入数据库
make clean           # 清理所有数据（危险）
```

## 渐进式落地

| Phase | 目标 | 时间 |
|-------|------|------|
| 1 | MVP 验证（1 账号 1 平台） | 3 周 |
| 2 | 单平台自动化（5 账号） | 4 周 |
| 3 | 多平台 80 账号 | 8 周 |
| 4 | 千级规模化运营 | 12 周 |

## 技术栈

Python 3.12 / FastAPI / Playwright / FFmpeg / PostgreSQL / Redis / RabbitMQ / MinIO / n8n / Docker Compose
