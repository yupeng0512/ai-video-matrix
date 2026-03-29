"""Content ledger management — query and update assignment records."""
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_platform_hashes(db: AsyncSession, platform: str, limit: int = 1000) -> list[str]:
    """Get all video hashes published on a platform (for similarity checking)."""
    result = await db.execute(text("""
        SELECT DISTINCT video_hash FROM content_ledger
        WHERE platform = :platform AND video_hash IS NOT NULL
        ORDER BY created_at DESC LIMIT :limit
    """), {"platform": platform, "limit": limit})
    return [row.video_hash for row in result.all()]


async def mark_published(
    db: AsyncSession,
    task_id: uuid.UUID,
    result_data: dict | None = None,
):
    """Mark a publish task as successful."""
    now = datetime.utcnow()
    await db.execute(text("""
        UPDATE publish_tasks SET status = 'success', completed_at = :now WHERE id = :id
    """), {"id": task_id, "now": now})

    await db.execute(text("""
        UPDATE content_ledger SET status = 'published', published_at = :now, result = :result
        WHERE id = (SELECT ledger_id FROM publish_tasks WHERE id = :id)
    """), {"id": task_id, "now": now, "result": str(result_data) if result_data else None})

    await db.execute(text("""
        UPDATE accounts SET last_publish = :now, updated_at = :now
        WHERE id = (SELECT account_id FROM publish_tasks WHERE id = :id)
    """), {"id": task_id, "now": now})

    await db.commit()


async def mark_failed(
    db: AsyncSession,
    task_id: uuid.UUID,
    error_message: str,
):
    """Mark a publish task as failed. Increment retry count if under limit."""
    await db.execute(text("""
        UPDATE publish_tasks
        SET status = CASE WHEN retry_count < max_retries THEN 'retrying' ELSE 'failed' END,
            retry_count = retry_count + 1,
            error_message = :error,
            completed_at = now()
        WHERE id = :id
    """), {"id": task_id, "error": error_message})

    await db.execute(text("""
        UPDATE content_ledger SET status = 'failed'
        WHERE id = (SELECT ledger_id FROM publish_tasks WHERE id = :id)
    """), {"id": task_id})

    await db.commit()


async def get_stats(db: AsyncSession) -> dict:
    """Get overall publishing statistics."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'published') as published,
            COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) as total
        FROM content_ledger
    """))
    row = result.first()
    return {
        "published": row.published,
        "assigned": row.assigned,
        "failed": row.failed,
        "total": row.total,
    }
