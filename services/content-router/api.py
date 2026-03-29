"""Content Router API — platform isolation routing and ledger management."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from router import route_video, find_available_account
from ledger import get_platform_hashes, mark_published, mark_failed, get_stats

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Content Router", lifespan=lifespan)


# ── Schemas ──────────────────────────────────────────────────

class RouteRequest(BaseModel):
    video_id: uuid.UUID
    video_hash: str
    target_platforms: list[str] | None = None


class RouteResult(BaseModel):
    assignments: list[dict]


class AccountCreate(BaseModel):
    platform: str
    username: str
    display_name: str = ""
    proxy_url: str = ""
    profile_id: str = ""
    daily_limit: int = 3


class PublishCallback(BaseModel):
    task_id: uuid.UUID
    success: bool
    error_message: str = ""
    result_data: dict | None = None


# ── Routing ──────────────────────────────────────────────────

@app.post("/route", response_model=RouteResult)
async def route_endpoint(body: RouteRequest, db: AsyncSession = Depends(get_db)):
    assignments = await route_video(
        db, body.video_id, body.video_hash, body.target_platforms,
    )
    return RouteResult(assignments=assignments)


@app.get("/hashes/{platform}")
async def get_hashes(platform: str, limit: int = 1000, db: AsyncSession = Depends(get_db)):
    hashes = await get_platform_hashes(db, platform, limit)
    return {"platform": platform, "count": len(hashes), "hashes": hashes}


# ── Accounts ─────────────────────────────────────────────────

@app.post("/accounts")
async def create_account(body: AccountCreate, db: AsyncSession = Depends(get_db)):
    account_id = uuid.uuid4()
    await db.execute(text("""
        INSERT INTO accounts (id, platform, username, display_name, proxy_url, profile_id, daily_limit, status)
        VALUES (:id, :platform, :username, :display_name, :proxy_url, :profile_id, :daily_limit, 'active')
    """), {
        "id": account_id,
        "platform": body.platform,
        "username": body.username,
        "display_name": body.display_name,
        "proxy_url": body.proxy_url,
        "profile_id": body.profile_id,
        "daily_limit": body.daily_limit,
    })
    await db.commit()
    return {"id": str(account_id), "status": "created"}


@app.get("/accounts")
async def list_accounts(platform: str | None = None, db: AsyncSession = Depends(get_db)):
    query = "SELECT id, platform, username, display_name, status, daily_limit, last_publish FROM accounts"
    params = {}
    if platform:
        query += " WHERE platform = :platform"
        params["platform"] = platform
    query += " ORDER BY platform, username"
    result = await db.execute(text(query), params)
    return [dict(row._mapping) for row in result.all()]


@app.patch("/accounts/{account_id}/status")
async def update_account_status(
    account_id: uuid.UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(text("""
        UPDATE accounts SET status = :status, updated_at = now() WHERE id = :id
    """), {"id": account_id, "status": status})
    await db.commit()
    return {"id": str(account_id), "status": status}


# ── Publish Callbacks ────────────────────────────────────────

@app.post("/callback")
async def publish_callback(body: PublishCallback, db: AsyncSession = Depends(get_db)):
    if body.success:
        await mark_published(db, body.task_id, body.result_data)
    else:
        await mark_failed(db, body.task_id, body.error_message)
    return {"status": "recorded"}


# ── Stats ────────────────────────────────────────────────────

@app.get("/stats")
async def stats_endpoint(db: AsyncSession = Depends(get_db)):
    return await get_stats(db)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "content-router"}
