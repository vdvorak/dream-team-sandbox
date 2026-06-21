from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .example.router import router as example_router
from .shared.errors import ApiError, api_error_handler
from .shared.health import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="App API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ApiError, api_error_handler)

    app.include_router(health_router)
    app.include_router(example_router)

    return app


app = create_app()
