"""Publisher API — manages publish workers and task queue consumption."""
import asyncio
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from workers.worker import PublishWorker
from account_manager import check_account_health, auto_cool_down

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

worker_pool: list[PublishWorker] = []
poll_task: asyncio.Task | None = None


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def _poll_tasks():
    """Background task polling for pending publish tasks."""
    while True:
        try:
            async with async_session() as db:
                result = await db.execute(text("""
                    SELECT pt.id as task_id, pt.video_id, pt.account_id, pt.platform,
                           pt.title, pt.description, pt.tags,
                           v.minio_key, a.proxy_url, a.cookie_data
                    FROM publish_tasks pt
                    JOIN videos v ON pt.video_id = v.id
                    JOIN accounts a ON pt.account_id = a.id
                    WHERE pt.status IN ('pending', 'retrying')
                      AND (pt.scheduled_at IS NULL OR pt.scheduled_at <= now())
                    ORDER BY pt.created_at ASC
                    LIMIT :limit
                """), {"limit": settings.max_workers})

                tasks = [dict(row._mapping) for row in result.all()]

                if tasks:
                    for task in tasks:
                        await db.execute(text(
                            "UPDATE publish_tasks SET status = 'running', started_at = now() WHERE id = :id"
                        ), {"id": task["task_id"]})
                    await db.commit()

                    async def _run_task(worker, task):
                        try:
                            await worker.process_task(task)
                        except Exception as e:
                            logger.error(f"Worker failed on task {task['task_id']}: {e}")

                    coros = []
                    for i, task in enumerate(tasks):
                        worker = worker_pool[i % len(worker_pool)]
                        coros.append(_run_task(worker, task))
                    await asyncio.gather(*coros)

                await auto_cool_down(db)

        except Exception as e:
            logger.error(f"Poll loop error: {e}")

        await asyncio.sleep(settings.publish_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global poll_task
    for i in range(settings.max_workers):
        w = PublishWorker(i)
        await w.start()
        worker_pool.append(w)

    poll_task = asyncio.create_task(_poll_tasks())
    logger.info(f"Started {len(worker_pool)} workers + poll task")

    yield

    if poll_task:
        poll_task.cancel()
    for w in worker_pool:
        await w.stop()
    await engine.dispose()


app = FastAPI(title="Publisher", lifespan=lifespan)


class ManualPublishRequest(BaseModel):
    task_id: uuid.UUID


@app.post("/publish")
async def manual_publish(body: ManualPublishRequest, db: AsyncSession = Depends(get_db)):
    """Manually trigger a specific publish task."""
    result = await db.execute(text("""
        SELECT pt.id as task_id, pt.video_id, pt.account_id, pt.platform,
               pt.title, pt.description, pt.tags,
               v.minio_key, a.proxy_url, a.cookie_data
        FROM publish_tasks pt
        JOIN videos v ON pt.video_id = v.id
        JOIN accounts a ON pt.account_id = a.id
        WHERE pt.id = :id
    """), {"id": body.task_id})
    task = result.first()
    if not task:
        raise HTTPException(404, "Task not found")

    task_dict = dict(task._mapping)
    worker = worker_pool[0] if worker_pool else None
    if not worker:
        raise HTTPException(503, "No workers available")

    result = await worker.process_task(task_dict)
    return result


@app.get("/tasks")
async def list_tasks(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT * FROM publish_tasks"
    params: dict = {"limit": limit}
    if status:
        query += " WHERE status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC LIMIT :limit"
    result = await db.execute(text(query), params)
    return [dict(row._mapping) for row in result.all()]


@app.get("/accounts/{account_id}/health")
async def account_health(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await check_account_health(db, str(account_id))


@app.get("/workers/status")
async def workers_status():
    return {
        "total_workers": len(worker_pool),
        "poll_task_running": poll_task is not None and not poll_task.done() if poll_task else False,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "publisher", "workers": len(worker_pool)}
