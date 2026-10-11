import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

app = FastAPI(
    title="Aven AI Secure Production Backend",
    version="1.0.0",
    description="Multi-user authentication, quota enforcement, and secure AI backend.",
)

# -------------------------------------------------------------------------
# Security Configurations
# -------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "aven_super_secret_jwt_key_2026_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token valid for 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
DB_FILE = "aven_secure.db"

# -------------------------------------------------------------------------
# Database Initialization (With Monetization & Quota Fields)
# -------------------------------------------------------------------------
def init_db():
    """Initializes multi-user database tables with subscription and usage tracking."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            subscription_tier TEXT DEFAULT 'free',
            daily_messages_used INTEGER DEFAULT 0,
            last_reset_date TEXT DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------------
# Security Helper Functions (Direct Bcrypt - Bug-Free)
# -------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token payload.",
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired.",
        )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return decode_jwt_token(token)

# -------------------------------------------------------------------------
# Monetization & Quota Guardrail Middleware
# -------------------------------------------------------------------------
def verify_and_increment_quota(username: str) -> bool:
    """
    Checks if the user has remaining daily messages.
    Free users: 20 messages/day. Pro users: Unlimited.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT subscription_tier, daily_messages_used, last_reset_date FROM users WHERE username = ?", 
        (username,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    tier, used, last_reset = row
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Reset daily quota on a new calendar day
    if last_reset != today:
        cursor.execute(
            "UPDATE users SET daily_messages_used = 0, last_reset_date = ? WHERE username = ?",
            (today, username)
        )
        conn.commit()
        used = 0

    if tier == "pro":
        conn.close()
        return True  # Unlimited access for Pro subscribers

    if used >= 20:   # Free tier daily message threshold
        conn.close()
        return False

    # Increment message count for the free user
    cursor.execute(
        "UPDATE users SET daily_messages_used = daily_messages_used + 1 WHERE username = ?",
        (username,)
    )
    conn.commit()
    conn.close()
    return True

# -------------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------------
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str

# -------------------------------------------------------------------------
# Authentication API Endpoints
# -------------------------------------------------------------------------
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, email FROM users WHERE username = ? OR email = ?",
        (user.username, user.email),
    )
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already registered.",
        )

    hashed_pw = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_pw),
    )
    conn.commit()
    conn.close()

    return {"message": f"User '{user.username}' successfully registered."}

@app.post("/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hashed_password FROM users WHERE username = ?", (form_data.username,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row or not verify_password(form_data.password, row[0]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": form_data.username,
    }

# -------------------------------------------------------------------------
# Protected Route Example
# -------------------------------------------------------------------------
@app.get("/users/me")
def read_current_user_profile(username: str = Depends(get_current_user)):
    return {"status": "authenticated", "authenticated_user": username}

# -------------------------------------------------------------------------
# Secure Multi-User WebSocket Endpoint (With Quota Protection)
# -------------------------------------------------------------------------
@app.websocket("/ws")
async def secure_websocket_endpoint(
    websocket: WebSocket, token: Optional[str] = Query(None)
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        username = decode_jwt_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    print(f"[WS AUTH SUCCESS] Connection accepted for user: {username}")

    try:
        while True:
            data = await websocket.receive_text()
            
            # Enforce Free Tier Message Quota
            if not verify_and_increment_quota(username):
                await websocket.send_text(
                    "⚠️ [Aven Quota Exceeded]: You have reached your free daily message limit (20/20). "
                    "Upgrade to Aven Pro for unlimited access!"
                )
                continue

            print(f"[{username}] Prompt: {data}")
            response = f"Aven [User: {username} - Free Tier]: Received '{data}'"
            await websocket.send_text(response)

    except WebSocketDisconnect:
        print(f"[WS DISCONNECT] User '{username}' disconnected.")
        
# -------------------------------------------------------------------------
# Server Entry Point (For Cloud Deployment)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)