import traceback
from pathlib import Path
from os import environ
from ps_client import PSClient
from domains.models import DBConnectionSettings
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
DOT_ENV_FILE_PATH = ROOT_DIR / ".env"
MIGRATIONS_DIR = ROOT_DIR / "migrations"
load_dotenv(dotenv_path=DOT_ENV_FILE_PATH, )


async def ensure_migrations_table(client: PSClient):
    print("Ensuring schema_migrations table exists...")

    query = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    try:
        async with client.connection() as conn:
            await conn.execute(query)
        print("schema_migrations table is ready")
    except Exception as ex:
        print("Failed to create or validate schema_migrations table")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise


async def get_applied_migrations(client: PSClient) -> set[str]:
    print("Loading applied migrations...")
    query = "SELECT version FROM schema_migrations"

    try:
        async with client.connection() as conn:
            rows = await conn.fetch(query)
        migrations = {row["version"] for row in rows}
        print(
            f"Loaded {len(migrations)} applied migrations"
        )
        return migrations
    except Exception as ex:
        print("Failed to load applied migrations")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise


async def apply_migration(client: PSClient,migration_path: Path):
    version = migration_path.name
    print(f"Applying migration: {version}")
    try:
        sql = migration_path.read_text()
    except Exception as ex:
        print(f"Failed reading migration file: {version}")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise

    try:
        async with client.connection() as conn:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute("INSERT INTO schema_migrations(version)VALUES($1)",version)
        print(f"Successfully applied migration: {version}")
    except Exception as ex:
        print(f"Migration failed and was rolled back: {version}")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise


async def migrate():
    print("Starting database migration process...")

    try:
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migration_files:
            raise RuntimeError(f"No migration files found in: {MIGRATIONS_DIR}")
        print(f"Found {len(migration_files)} migration files")
        db_settings = DBConnectionSettings(db_name=environ['DB_NAME'], db_port=int(environ['DB_PORT']),
                                           db_url=environ['DB_HOST'],
                                           db_password=environ['DB_PASSWORD'], db_username=environ['DB_USERNAME'])
        print("Creating PostgreSQL client...")
        client: PSClient = await PSClient.create(db_settings)
        print("PostgreSQL client created successfully")
    except Exception as ex:
        print("Failed during migration initialization")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise

    try:
        await ensure_migrations_table(client)
        applied_migrations = await get_applied_migrations(client)

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                print(f"Skipping already applied migration: {migration_file.name}")
                continue
            await apply_migration(client,migration_file)

        print("Database migration process completed successfully")
    except Exception as ex:
        print("Database migration process failed")
        print(f"Error: {str(ex)}")
        print(traceback.format_exc())
        raise
    finally:
        try:
            print("Closing database connection pool...")
            await client.close()
            print("Database connection pool closed")

        except Exception as ex:
            print("Failed closing database connection pool")
            print(f"Error: {str(ex)}")
            print(traceback.format_exc())