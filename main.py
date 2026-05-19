import logging
import textwrap
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import get_settings
from exceptions.exceptions import AppError
from migrate import migrate
from ps_client import PSClient
from routes.apis import router

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    startup: str = textwrap.dedent("""## Starting Bootstrap ##                                   
                                   Create PostgreSQL client
                                   Perform database migrations
                                   Get jwt secret                                   
                                   """)
    logger.info(f'{startup}')
    await migrate()
    app.state.db_client = await PSClient.create(settings.db_settings)
    app.state.jwt_secret = settings.jwt_secret

    yield

    # Shutdown
    shutdown: str = textwrap.dedent("""## Shutdown ##
                                    Close PostgresSQL client
                                    """)
    logger.info(f'{shutdown}')
    await app.state.db_client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.error_code,"detail": exc.detail,},
    )

@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request,exc: Exception,) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500,
                        content={"code": "INTERNAL_SERVER_ERROR", "detail": "Internal server error"})

if __name__ == '__main__':
    # Uvicorn expects "module_name:variable_name"; this "main:app" value means
    # "import main.py, then use its app = FastAPIBrushUp(...) instance". If this module
    # is renamed to notes_app.py, the import string should become "notes_app:app".
    # The remaining arguments bind the server to localhost on port 8000 and
    # enable auto-reload so code changes restart the development server.
    uvicorn.run(app="main:app", host=settings.server_host, port=settings.server_port)