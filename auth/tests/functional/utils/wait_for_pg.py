"""Script that waits for PostgreSQL service to start."""

import asyncio
import logging

import asyncpg
from functional.settings import test_settings


async def wait_for_postgres() -> None:
    """Connect to PostgreSQL until responds or raise RuntimeError after max_attempts."""
    host = test_settings.postgres_host
    port = test_settings.postgres_port
    user = test_settings.postgres_user
    password = test_settings.postgres_password
    database = test_settings.postgres_db
    
    max_attempts = test_settings.service_wait_max_attempts
    delay = test_settings.service_wait_delay
    
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    for attempt in range(1, max_attempts + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            logging.info("PostgreSQL is ready")
            return
        except (asyncpg.CannotConnectNowError, asyncpg.ConnectionFailureError) as e:
            logging.warning(
                "PostgreSQL not ready, attempt %d/%d: %s", 
                attempt, max_attempts, str(e)
            )
            await asyncio.sleep(delay)
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            await asyncio.sleep(delay)
    
    raise RuntimeError(
        f"PostgreSQL at {host}:{port} not available after {max_attempts} attempts"
    )


if __name__ == "__main__":
    asyncio.run(wait_for_postgres())
