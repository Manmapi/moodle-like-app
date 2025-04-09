from app import crud
from app.core.config import settings
from app.models.user import User, UserCreate
from app.models.thread import Thread
from sqlmodel import Session, create_engine, select
from app.core.security import get_password_hash
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)
    # Create admin user if not exists.
    admin_user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if admin_user is None:
        admin_user = User(email=settings.FIRST_SUPERUSER, hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD), user_name="Admin")
        session.add(admin_user)
        session.commit()
    # Create root thread if not exists
    root_thread = session.exec(
        select(Thread).where(Thread.level == 0)
    ).first()
    if root_thread is None:
        root_thread = Thread(level=0, title="Root", user_id=admin_user.id)
        session.add(root_thread)
        session.commit()
    
