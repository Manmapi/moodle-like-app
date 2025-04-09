from collections.abc import Generator
from typing import Annotated, Tuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session
from neo4j import Session as Neo4jSession
from influxdb_client import InfluxDBClient

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.neo4j import neo4j_conn
from app.core.influxdb import influxdb_conn
from app.models.user import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

# Dependency to get a Neo4j session
async def get_neo4j_db():
    async with neo4j_conn.get_session() as session:
        yield session

# Dependency to get InfluxDB client and org context
async def get_influxdb() -> Generator[Tuple[InfluxDBClient, str], None, None]:
    async with influxdb_conn.get_session() as (client, org):
        yield client, org

SessionDep = Annotated[Session, Depends(get_db)]
Neo4jSessionDep = Annotated[Neo4jSession, Depends(get_neo4j_db)]
InfluxDBDep = Annotated[Tuple[InfluxDBClient, str], Depends(get_influxdb)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]

oauth2_scheme = OAuth2PasswordBearer("token")

def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user