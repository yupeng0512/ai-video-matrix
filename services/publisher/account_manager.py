"""Account lifecycle management — health checks, cooling, banning."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def check_account_health(db: AsyncSession, account_id: str) -> dict:
    """Check account health based on recent publish results."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'published') as success_count,
            COUNT(*) FILTER (WHERE status = 'failed') as fail_count,
            COUNT(*) as total_count,
            MAX(published_at) as last_success
        FROM content_ledger
        WHERE account_id = :account_id
          AND created_at >= now() - interval '7 days'
    """), {"account_id": account_id})
    row = result.first()

    total = row.total_count or 0
    fails = row.fail_count or 0
    success_rate = (row.success_count / total * 100) if total > 0 else 100

    health = "healthy"
    if success_rate < 50:
        health = "critical"
    elif success_rate < 80:
        health = "degraded"

    return {
        "account_id": account_id,
        "health": health,
        "success_rate": round(success_rate, 1),
        "total_7d": total,
        "fails_7d": fails,
        "last_success": str(row.last_success) if row.last_success else None,
    }


async def auto_cool_down(db: AsyncSession):
    """Automatically cool down accounts with high failure rates."""
    await db.execute(text("""
        UPDATE accounts SET status = 'cooling_down', updated_at = now()
        WHERE id IN (
            SELECT a.id FROM accounts a
            JOIN (
                SELECT account_id,
                    COUNT(*) FILTER (WHERE status = 'failed') as fails,
                    COUNT(*) as total
                FROM content_ledger
                WHERE created_at >= now() - interval '24 hours'
                GROUP BY account_id
                HAVING COUNT(*) >= 3
                   AND COUNT(*) FILTER (WHERE status = 'failed')::float / COUNT(*) > 0.5
            ) stats ON a.id = stats.account_id
            WHERE a.status = 'active'
        )
    """))
    await db.commit()


async def recover_cooled_accounts(db: AsyncSession, cool_down_hours: int = 24):
    """Re-activate accounts that have been cooling down long enough."""
    await db.execute(text("""
        UPDATE accounts SET status = 'active', updated_at = now()
        WHERE status = 'cooling_down'
          AND updated_at < now() - interval '1 hour' * :hours
    """), {"hours": cool_down_hours})
    await db.commit()
