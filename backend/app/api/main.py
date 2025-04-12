from fastapi import APIRouter

from app.api.routes import (
    login,
    users,
    utils,
    items,
    thread,
    tag,
    post,
    private,
    neo4j_test,
    influxdb_test,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(thread.router)
api_router.include_router(tag.router)
api_router.include_router(post.router)  

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
