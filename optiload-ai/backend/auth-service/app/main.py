"""
Auth Service — OptiLoad AI
JWT-based authentication with FastAPI
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import redis
import json
import uuid
import logging
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response


# ── Settings ──────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="OptiLoad AI — Auth Service",
    description="JWT Authentication Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security ──────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Metrics ───────────────────────────────────────────────────────────────────
login_counter = Counter("auth_logins_total", "Total login attempts", ["status"])
token_verify_counter = Counter("auth_token_verifications_total", "Token verifications", ["status"])


# ── DB Helper ─────────────────────────────────────────────────────────────────
def get_db_connection():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_port_db = rest.split("/")
    db = host_port_db[-1]
    host_port = host_port_db[0]
    if ":" in host_port:
        host, port = host_port.split(":")
    else:
        host, port = host_port, "5432"
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


# ── Redis client ──────────────────────────────────────────────────────────────
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


# ── Models ────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str = "operator"


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    is_active: bool


# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
        # Check if token is blacklisted
        if redis_client.get(f"blacklist:{token}"):
            raise credentials_exception
        token_verify_counter.labels(status="success").inc()
        return {"user_id": user_id, "username": payload.get("username"), "role": payload.get("role")}
    except JWTError:
        token_verify_counter.labels(status="failed").inc()
        raise credentials_exception


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    """Register a new user."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check existing
            cur.execute("SELECT user_id FROM users WHERE username=%s OR email=%s", (user.username, user.email))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username or email already exists")
            hashed = hash_password(user.password)
            user_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO users (user_id, username, email, hashed_password, role)
                   VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                (user_id, user.username, user.email, hashed, user.role),
            )
            new_user = cur.fetchone()
            conn.commit()
            logger.info(f"User registered: {user.username}")
            return UserResponse(
                user_id=str(new_user["user_id"]),
                username=new_user["username"],
                email=new_user["email"],
                role=new_user["role"],
                is_active=new_user["is_active"],
            )
    finally:
        conn.close()


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get JWT tokens."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (form_data.username,))
            user = cur.fetchone()
            if not user or not verify_password(form_data.password, user["hashed_password"]):
                login_counter.labels(status="failed").inc()
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if not user["is_active"]:
                raise HTTPException(status_code=403, detail="Account is inactive")
            token_data = {"sub": str(user["user_id"]), "username": user["username"], "role": user["role"]}
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
            login_counter.labels(status="success").inc()
            logger.info(f"User logged in: {user['username']}")
            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )
    finally:
        conn.close()


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_tok: str):
    """Refresh access token using refresh token."""
    try:
        payload = jwt.decode(refresh_tok, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        token_data = {"sub": payload["sub"], "username": payload["username"], "role": payload["role"]}
        new_access = create_access_token(token_data)
        new_refresh = create_refresh_token(token_data)
        return Token(access_token=new_access, refresh_token=new_refresh, expires_in=settings.access_token_expire_minutes * 60)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    """Logout: blacklist the current token."""
    redis_client.setex(f"blacklist:{token}", settings.access_token_expire_minutes * 60, "1")
    logger.info(f"User logged out: {current_user['username']}")
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (current_user["user_id"],))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse(
                user_id=str(user["user_id"]),
                username=user["username"],
                email=user["email"],
                role=user["role"],
                is_active=user["is_active"],
            )
    finally:
        conn.close()


@app.post("/auth/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify token validity — used by other services."""
    return {"valid": True, "user": current_user}
