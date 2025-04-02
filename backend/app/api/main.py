from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, neo4j_test, influxdb_test
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(neo4j_test.router)
api_router.include_router(influxdb_test.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
