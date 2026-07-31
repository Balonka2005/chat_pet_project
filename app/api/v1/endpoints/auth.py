from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RefreshRequest, TokenPair, UserCreate, UserLogin, UserRead
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    if await auth_service.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username уже занят")
    if await auth_service.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = await auth_service.create_user(db, user_in)
    return user


@router.post("/login", response_model=TokenPair)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный username или пароль",
        )

    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    db_token = await auth_service.get_valid_refresh_token(db, payload.refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh токен недействителен или истёк")

    user = await auth_service.get_user_by_id(db, db_token.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    await auth_service.revoke_refresh_token(db, payload.refresh_token)
    access_token, new_refresh_token = await auth_service.issue_tokens(db, user)

    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.revoke_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
