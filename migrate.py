import logging
from pathlib import Path

from config import get_settings
from ps_client import PSClient

ROOT_DIR = Path(__file__).parent
MIGRATIONS_DIR = ROOT_DIR / "migrations"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ensure_migrations_table(client: PSClient):
    logger.info("Ensuring schema_migrations table exists...")

    query = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    try:
        async with client.connection() as conn:
            await conn.execute(query)
        logger.info("schema_migrations table is ready")
    except Exception:
        logger.exception("Failed to create or validate schema_migrations table", exc_info=True)
        raise


async def get_applied_migrations(client: PSClient) -> set[str]:
    logger.info("Loading applied migrations...")
    query = "SELECT version FROM schema_migrations"

    try:
        async with client.connection() as conn:
            rows = await conn.fetch(query)
        migrations = {row["version"] for row in rows}
        logger.info("Loaded %s applied migrations", len(migrations))
        return migrations
    except Exception:
        logger.exception("Failed to load applied migrations", exc_info=True)
        raise


async def apply_migration(client: PSClient, migration_path: Path):
    version = migration_path.name
    logger.info("Applying migration: %s", version)
    try:
        sql = migration_path.read_text()
    except Exception:
        logger.exception("Failed reading migration file: %s", version, exc_info=True)
        raise

    try:
        async with client.connection() as conn:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute("INSERT INTO schema_migrations(version)VALUES($1)", version)
        logger.info("Successfully applied migration: %s", version)
    except Exception:
        logger.exception("Migration failed and was rolled back: %s", version, exc_info=True)
        raise


async def migrate():
    logger.info("Starting database migration process...")

    try:
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migration_files:
            raise RuntimeError(f"No migration files found in: {MIGRATIONS_DIR}")
        logger.info("Found %s migration files", len(migration_files))
        settings = get_settings()
        logger.info("Creating PostgreSQL client...")
        client: PSClient = await PSClient.create(settings.db_settings)
        logger.info("PostgreSQL client created successfully")
    except Exception:
        logger.exception("Failed during migration initialization", exc_info=True)
        raise

    try:
        await ensure_migrations_table(client)
        applied_migrations = await get_applied_migrations(client)

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                logger.info("Skipping already applied migration: %s", migration_file.name)
                continue
            await apply_migration(client, migration_file)

        logger.info("Database migration process completed successfully")
    except Exception:
        logger.exception("Database migration process failed", exc_info=True)
        raise
    finally:
        try:
            logger.info("Closing database connection pool...")
            await client.close()
            logger.info("Database connection pool closed")

        except Exception:
            logger.exception("Failed closing database connection pool", exc_info=True)
