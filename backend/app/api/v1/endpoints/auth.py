import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Response, Request, status, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.errors import AuthenticationError, GitVaneError
from app.core.security_utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_secure_token,
    create_password_reset_token,
    verify_password_reset_token,
)
from app.db.models import User, UserRefreshToken
from app.schemas.user import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserUpdate,
)

import smtplib
from email.message import EmailMessage
from typing import Any

def send_reset_email(to_email: str, reset_url: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Password Reset Request - GitVane"
    msg["From"] = settings.EMAILS_FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(
        f"Hello,\n\nYou requested a password reset for your GitVane account.\n"
        f"Please click the following link to reset your password:\n\n{reset_url}\n\n"
        f"If you did not request this, please ignore this email.\n"
    )

    if not settings.SMTP_HOST:
        return

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        try:
            server.starttls()
        except Exception:
            pass
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Check for unique email
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise GitVaneError("Email already registered")

    # Create user
    hashed = hash_password(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed,
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(db_user)
    await db.flush()  # Populates db_user.id

    # Generate tokens
    access_token = create_access_token(subject=db_user.id)
    refresh_token_val = generate_secure_token()

    # Store refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_refresh_token = UserRefreshToken(
        user_id=db_user.id,
        token=refresh_token_val,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(db_refresh_token)
    await db.commit()

    # Set cookies
    secure = settings.ENVIRONMENT != "local"
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_val,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        key="gitvane_logged_in",
        value="true",
        httponly=False,
        samesite="lax",
        secure=secure,
        path="/",
    )

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Verify credentials
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    if user and user.oauth_provider == "google" and not user.hashed_password:
        raise AuthenticationError(
            "This account was created using Google OAuth. Please sign in with Google or reset your password to use email and password login."
        )

    if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
        raise AuthenticationError("Invalid or expired credentials")

    if not user.is_active:
        raise AuthenticationError("User is inactive")

    # Generate tokens
    access_token = create_access_token(subject=user.id)
    refresh_token_val = generate_secure_token()

    # Store refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_refresh_token = UserRefreshToken(
        user_id=user.id,
        token=refresh_token_val,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(db_refresh_token)
    await db.commit()

    # Set cookies
    secure = settings.ENVIRONMENT != "local"
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_val,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        key="gitvane_logged_in",
        value="true",
        httponly=False,
        samesite="lax",
        secure=secure,
        path="/",
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    refresh_token_val = request.cookies.get("refresh_token")
    if not refresh_token_val:
        raise AuthenticationError("Refresh token missing")

    # Verify in DB
    result = await db.execute(
        select(UserRefreshToken).where(UserRefreshToken.token == refresh_token_val)
    )
    db_refresh_token = result.scalars().first()
    if not db_refresh_token:
        raise AuthenticationError("Invalid or expired credentials")
    now = datetime.now(timezone.utc)

    # Verify expiration
    if db_refresh_token.expires_at < now:
        raise AuthenticationError("Invalid or expired credentials")

    if db_refresh_token.is_revoked:
        # Grace period check (15 seconds) to accommodate in-flight concurrent requests / network jitter
        if (
            db_refresh_token.revoked_at
            and (now - db_refresh_token.revoked_at).total_seconds() <= 15
        ):
            # Concurrent request within grace period: allow and issue access token
            access_token = create_access_token(subject=db_refresh_token.user_id)
            return TokenResponse(access_token=access_token)

        # Genuine reuse / replay attack (>15s after revocation)
        from sqlalchemy import update
        await db.execute(
            update(UserRefreshToken)
            .where(
                UserRefreshToken.user_id == db_refresh_token.user_id,
                UserRefreshToken.is_revoked == False,
            )
            .values(is_revoked=True, revoked_at=now)
        )
        await db.commit()
        raise AuthenticationError("Invalid or expired credentials")

    # Perform RTR (Refresh Token Rotation)
    db_refresh_token.is_revoked = True
    db_refresh_token.revoked_at = now

    new_refresh_token_val = generate_secure_token()
    new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_db_refresh_token = UserRefreshToken(
        user_id=db_refresh_token.user_id,
        token=new_refresh_token_val,
        expires_at=new_expires_at,
        is_revoked=False,
    )
    db.add(new_db_refresh_token)
    await db.commit()

    # Set cookies
    secure = settings.ENVIRONMENT != "local"
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token_val,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        key="gitvane_logged_in",
        value="true",
        httponly=False,
        samesite="lax",
        secure=secure,
        path="/",
    )

    access_token = create_access_token(subject=db_refresh_token.user_id)
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    refresh_token_val = request.cookies.get("refresh_token")
    if refresh_token_val:
        result = await db.execute(
            select(UserRefreshToken).where(UserRefreshToken.token == refresh_token_val)
        )
        db_refresh_token = result.scalars().first()
        if db_refresh_token:
            db_refresh_token.is_revoked = True
            db_refresh_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    # Clear cookies
    secure = settings.ENVIRONMENT != "local"
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="lax",
        secure=secure,
    )
    response.delete_cookie(
        key="gitvane_logged_in",
        path="/",
        samesite="lax",
        secure=secure,
    )

    return {"status": "success", "message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.get("/csrf", status_code=status.HTTP_200_OK)
async def get_csrf() -> dict[str, str]:
    """Lightweight bootstrap probe for non-browser/CLI clients to initialize CSRF and session cookies."""
    return {"status": "success"}


@router.get("/oauth2/google")
async def oauth2_google() -> RedirectResponse:
    state = generate_secure_token()

    # Build auth parameters
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
    }
    
    redirect_url = f"{auth_url}?{urlencode(params)}"
    redirect_res = RedirectResponse(redirect_url)

    # Save state in HttpOnly cookie
    secure = settings.ENVIRONMENT != "local"
    redirect_res.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )

    return redirect_res


@router.get("/oauth2/callback/google")
async def oauth2_callback_google(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    # Verify state
    state_cookie = request.cookies.get("oauth_state")
    if not state_cookie or not state or state != state_cookie:
        raise AuthenticationError("OAuth state verification failed")

    if not code:
        raise AuthenticationError("OAuth authorization code missing")

    # Exchange code for user details
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()

            google_access_token = tokens.get("access_token")
            if not google_access_token:
                raise AuthenticationError("Failed to retrieve Google access token")

            profile_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {google_access_token}"}
            profile_response = await client.get(profile_url, headers=headers)
            profile_response.raise_for_status()
            profile = profile_response.json()
    except Exception as e:
        raise AuthenticationError(f"Google authentication failed: {str(e)}")

    email = profile.get("email")
    oauth_id = profile.get("sub")
    full_name = profile.get("name", email)
    picture = profile.get("picture")

    if not email or not oauth_id:
        raise AuthenticationError("Incomplete Google profile details received")

    # Upsert user record
    result = await db.execute(
        select(User).where(
            (User.oauth_provider == "google") & (User.oauth_id == oauth_id)
        )
    )
    user = result.scalars().first()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user:
            user.oauth_provider = "google"
            user.oauth_id = oauth_id
            if picture:
                user.picture = picture
        else:
            user = User(
                email=email,
                full_name=full_name,
                picture=picture,
                oauth_provider="google",
                oauth_id=oauth_id,
                is_active=True,
            )
            db.add(user)
            await db.flush()
    else:
        user.full_name = full_name
        user.email = email
        if picture:
            user.picture = picture

    # Generate tokens
    access_token = create_access_token(subject=user.id)
    refresh_token_val = generate_secure_token()

    # Store refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_refresh_token = UserRefreshToken(
        user_id=user.id,
        token=refresh_token_val,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(db_refresh_token)
    await db.commit()

    # Build response redirect
    frontend_url = settings.FRONTEND_URL
    redirect_res = RedirectResponse(f"{frontend_url}#access_token={access_token}")

    secure = settings.ENVIRONMENT != "local"
    redirect_res.set_cookie(
        key="refresh_token",
        value=refresh_token_val,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    redirect_res.set_cookie(
        key="gitvane_logged_in",
        value="true",
        httponly=False,
        samesite="lax",
        secure=secure,
        path="/",
    )
    redirect_res.delete_cookie(
        key="oauth_state",
        path="/",
        samesite="lax",
        secure=secure,
    )

    return redirect_res


@router.post("/forgot-password")
async def forgot_password(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalars().first()

    if not user:
        return {"message": "If your email is registered, you will receive a password reset link."}

    token = create_password_reset_token(user.email)
    reset_url = f"{settings.PASSWORD_RESET_URL}?token={token}"

    import logging
    logger = logging.getLogger("gitvane")

    if (settings.ENVIRONMENT in ("local", "development")) and settings.DEBUG:
        logger.info(f"[DEV MODE] Password reset URL for {user.email}: {reset_url}")
        return {
            "message": "Password reset email sent (dev mode)",
            "reset_url": reset_url,
        }

    try:
        await asyncio.to_thread(send_reset_email, user.email, reset_url)
        logger.info(f"Dispatched password reset email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to dispatch password reset email: {e}")

    return {"message": "If your email is registered, you will receive a password reset link."}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    email = verify_password_reset_token(reset_data.token)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError("User not found")

    if user.hashed_password and verify_password(reset_data.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as your old password",
        )

    user.hashed_password = hash_password(reset_data.new_password)

    # Revoke all active refresh tokens for user
    from sqlalchemy import update
    now = datetime.now(timezone.utc)
    await db.execute(
        update(UserRefreshToken)
        .where(
            UserRefreshToken.user_id == user.id,
            UserRefreshToken.is_revoked == False,
        )
        .values(is_revoked=True, revoked_at=now)
    )

    await db.commit()
    return {"status": "success", "message": "Password reset successfully"}


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        if not user_update.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change password",
            )
        if not current_user.hashed_password or not verify_password(
            user_update.current_password, current_user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )
        current_user.hashed_password = hash_password(user_update.password)

    await db.commit()
    await db.refresh(current_user)
    return current_user
