"""Content routing engine — platform isolation + cross-platform reuse.

Core rules:
  1. Same-platform isolation: No two accounts on the same platform get the same video.
  2. Cross-platform reuse: A video used on Douyin can be reused on Kuaishou
     (after re-mutation for fingerprint change).
  3. Content ledger: Every assignment is recorded for deduplication.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession


async def find_available_account(
    db: AsyncSession,
    platform: str,
    exclude_ids: list[uuid.UUID] | None = None,
) -> dict | None:
    """Find an active account on `platform` that hasn't hit its daily limit."""
    from sqlalchemy import text

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    query = text("""
        SELECT a.id, a.username, a.display_name, a.daily_limit,
               COALESCE(pub_count, 0) as today_published
        FROM accounts a
        LEFT JOIN (
            SELECT account_id, COUNT(*) as pub_count
            FROM content_ledger
            WHERE created_at >= :today_start AND status = 'published'
            GROUP BY account_id
        ) cl ON a.id = cl.account_id
        WHERE a.platform = :platform
          AND a.status = 'active'
          AND COALESCE(pub_count, 0) < a.daily_limit
        ORDER BY COALESCE(pub_count, 0) ASC, a.last_publish ASC NULLS FIRST
        LIMIT 1
    """)

    result = await db.execute(query, {
        "platform": platform,
        "today_start": today_start,
    })
    row = result.first()
    if not row:
        return None

    return {
        "id": row.id,
        "username": row.username,
        "display_name": row.display_name,
        "remaining_today": row.daily_limit - row.today_published,
    }


async def check_video_used_on_platform(
    db: AsyncSession,
    video_hash: str,
    platform: str,
) -> bool:
    """Check if a video hash has already been assigned to any account on this platform."""
    from sqlalchemy import text

    query = text("""
        SELECT 1 FROM content_ledger
        WHERE platform = :platform AND video_hash = :video_hash
        LIMIT 1
    """)
    result = await db.execute(query, {"platform": platform, "video_hash": video_hash})
    return result.first() is not None


async def assign_video_to_account(
    db: AsyncSession,
    video_id: uuid.UUID,
    video_hash: str,
    account_id: uuid.UUID,
    platform: str,
) -> uuid.UUID:
    """Create a content ledger entry and publish task."""
    from sqlalchemy import text

    ledger_id = uuid.uuid4()
    task_id = uuid.uuid4()

    result = await db.execute(text("""
        INSERT INTO content_ledger (id, video_id, account_id, platform, video_hash, status)
        VALUES (:id, :video_id, :account_id, :platform, :video_hash, 'assigned')
        ON CONFLICT (video_id, account_id) DO NOTHING
        RETURNING id
    """), {
        "id": ledger_id,
        "video_id": video_id,
        "account_id": account_id,
        "platform": platform,
        "video_hash": video_hash,
    })

    if result.first() is None:
        return None

    await db.execute(text("""
        INSERT INTO publish_tasks (id, ledger_id, video_id, account_id, platform, status)
        VALUES (:id, :ledger_id, :video_id, :account_id, :platform, 'pending')
    """), {
        "id": task_id,
        "ledger_id": ledger_id,
        "video_id": video_id,
        "account_id": account_id,
        "platform": platform,
    })

    await db.commit()
    return task_id


async def route_video(
    db: AsyncSession,
    video_id: uuid.UUID,
    video_hash: str,
    target_platforms: list[str] | None = None,
) -> list[dict]:
    """Route a video to available accounts across platforms.

    For each platform:
      1. Check if video_hash is already used on that platform
      2. Find an available account
      3. Create assignment
    """
    platforms = target_platforms or ["douyin", "kuaishou", "xiaohongshu", "weixin_channel"]
    assignments = []

    for platform in platforms:
        is_used = await check_video_used_on_platform(db, video_hash, platform)
        if is_used:
            assignments.append({
                "platform": platform,
                "status": "skipped",
                "reason": "video_hash_already_used_on_platform",
            })
            continue

        account = await find_available_account(db, platform)
        if not account:
            assignments.append({
                "platform": platform,
                "status": "skipped",
                "reason": "no_available_account",
            })
            continue

        task_id = await assign_video_to_account(
            db, video_id, video_hash, account["id"], platform,
        )
        if task_id is None:
            assignments.append({
                "platform": platform,
                "status": "skipped",
                "reason": "duplicate_assignment",
            })
            continue
        assignments.append({
            "platform": platform,
            "status": "assigned",
            "account_id": str(account["id"]),
            "account_name": account["username"],
            "task_id": str(task_id),
        })

    return assignments
