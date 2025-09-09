import base64
import httpx
from fastapi import FastAPI, HTTPException, Depends, Response, Request, Cookie, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import bcrypt
import jwt
import secrets
import os
import io
from PIL import Image
import json

from backend.app.database import SessionLocal, engine, Base
from backend.app import models

app = FastAPI()

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

GITHUB_API_URL = "https://api.github.com"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: int
    exp: int

class GitHubConfigUpdate(BaseModel):
    github_username: Optional[str]
    github_repo: Optional[str]
    github_token: Optional[str]
    openai_token: Optional[str]

class GitHubConfig(BaseModel):
    username: str
    repo: str
    token: str

class FileContent(BaseModel):
    path: str
    content: str

class CommitRequest(BaseModel):
    message: str
    branch: Optional[str] = None
    files: List[FileContent]

class AskRequest(BaseModel):
    prompt: str

class DiffItem(BaseModel):
    path: str
    old: Optional[str]
    new: Optional[str]

class AskResponse(BaseModel):
    diffs: List[DiffItem]

# Utility functions

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token():
    # Generate a secure random string
    return secrets.token_urlsafe(32)

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Auth endpoints

@app.post("/signup", status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = hash_password(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"msg": "User created successfully"}

@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), response: Response = None, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token()

    # Save refresh token in DB
    user.refresh_token = refresh_token
    user.refresh_token_expiry = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout")
def logout(response: Response, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Remove refresh token from DB
    current_user.refresh_token = None
    current_user.refresh_token_expiry = None
    db.commit()

    # Remove cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    return {"msg": "Logged out successfully"}

@app.post("/refresh", response_model=TokenResponse)
def refresh_token(response: Response, refresh_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    user = db.query(models.User).filter(models.User.refresh_token == refresh_token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if user.refresh_token_expiry < datetime.utcnow():
        user.refresh_token = None
        user.refresh_token_expiry = None
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Rotate refresh token
    new_refresh_token = create_refresh_token()
    user.refresh_token = new_refresh_token
    user.refresh_token_expiry = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()

    access_token = create_access_token({"sub": user.id})

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )

    return {"access_token": access_token, "token_type": "bearer"}

# GitHub config endpoints

@app.get("/user/github-config")
def get_github_config(current_user: models.User = Depends(get_current_user)):
    return {
        "github_username": current_user.github_username,
        "github_repo": current_user.github_repo,
        "github_token": current_user.github_token,
        "openai_token": current_user.openai_token
    }

@app.post("/user/github-config")
def update_github_config(config: GitHubConfigUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if config.github_username is not None:
        current_user.github_username = config.github_username
    if config.github_repo is not None:
        current_user.github_repo = config.github_repo
    if config.github_token is not None:
        current_user.github_token = config.github_token
    if config.openai_token is not None:
        current_user.openai_token = config.openai_token
    db.commit()
    return {"msg": "GitHub and OpenAI tokens updated"}

# GitHub API endpoints (reuse existing code, but require auth and use stored tokens)

async def get_default_branch(config: GitHubConfig):
    headers = {"Authorization": f"token {config.token}"}
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Repo not found or unauthorized")
        data = resp.json()
        default_branch = data.get("default_branch")
        if not default_branch:
            # fallback to main or master
            # check if main exists
            for branch in ["main", "master"]:
                branch_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/branches/{branch}"
                branch_resp = await client.get(branch_url, headers=headers)
                if branch_resp.status_code == 200:
                    return branch
            raise HTTPException(status_code=404, detail="No default branch found")
        return default_branch

@app.post("/github/tree")
async def get_repo_tree(current_user: models.User = Depends(get_current_user)):
    if not current_user.github_username or not current_user.github_repo or not current_user.github_token:
        raise HTTPException(status_code=400, detail="GitHub configuration incomplete")
    config = GitHubConfig(username=current_user.github_username, repo=current_user.github_repo, token=current_user.github_token)
    headers = {"Authorization": f"token {config.token}"}
    default_branch = await get_default_branch(config)
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/trees/{default_branch}?recursive=1"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return {"files": []}
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch repo tree")
        data = resp.json()
        tree = data.get("tree", [])
        files = [item["path"] for item in tree if item["type"] == "blob"]
        return {"files": files}

@app.post("/github/file")
async def get_file_content(path: str, current_user: models.User = Depends(get_current_user)):
    if not current_user.github_username or not current_user.github_repo or not current_user.github_token:
        raise HTTPException(status_code=400, detail="GitHub configuration incomplete")
    config = GitHubConfig(username=current_user.github_username, repo=current_user.github_repo, token=current_user.github_token)
    headers = {"Authorization": f"token {config.token}"}
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="File not found")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch file content")
        data = resp.json()
        content_b64 = data.get("content", "")
        encoding = data.get("encoding", "")
        if encoding != "base64":
            raise HTTPException(status_code=500, detail="Unsupported encoding")
        content = base64.b64decode(content_b64).decode("utf-8")
        return {"path": path, "content": content}

@app.post("/github/commit")
async def commit_changes(commit_req: CommitRequest, current_user: models.User = Depends(get_current_user)):
    if not current_user.github_username or not current_user.github_repo or not current_user.github_token:
        raise HTTPException(status_code=400, detail="GitHub configuration incomplete")
    config = GitHubConfig(username=current_user.github_username, repo=current_user.github_repo, token=current_user.github_token)
    headers = {"Authorization": f"token {config.token}"}
    async with httpx.AsyncClient() as client:
        branch = commit_req.branch or await get_default_branch(config)
        ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/ref/heads/{branch}"
        ref_resp = await client.get(ref_url, headers=headers)
        if ref_resp.status_code == 404:
            ref = None
        elif ref_resp.status_code != 200:
            raise HTTPException(status_code=ref_resp.status_code, detail="Failed to get ref")
        else:
            ref = ref_resp.json()
        if ref:
            base_tree_sha = ref["object"]["sha"]
        else:
            base_tree_sha = None
        blobs = []
        for file in commit_req.files:
            blob_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/blobs"
            blob_data = {
                "content": file.content,
                "encoding": "utf-8"
            }
            blob_resp = await client.post(blob_url, headers=headers, json=blob_data)
            if blob_resp.status_code != 201:
                raise HTTPException(status_code=blob_resp.status_code, detail="Failed to create blob")
            blob_sha = blob_resp.json()["sha"]
            blobs.append({"path": file.path, "mode": "100644", "type": "blob", "sha": blob_sha})
        tree_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/trees"
        tree_data = {"tree": blobs}
        if base_tree_sha:
            tree_data["base_tree"] = base_tree_sha
        tree_resp = await client.post(tree_url, headers=headers, json=tree_data)
        if tree_resp.status_code != 201:
            raise HTTPException(status_code=tree_resp.status_code, detail="Failed to create tree")
        tree_sha = tree_resp.json()["sha"]
        commit_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/commits"
        parents = []
        if ref:
            parents.append(ref["object"]["sha"])
        commit_data = {
            "message": commit_req.message,
            "tree": tree_sha,
            "parents": parents
        }
        commit_resp = await client.post(commit_url, headers=headers, json=commit_data)
        if commit_resp.status_code != 201:
            raise HTTPException(status_code=commit_resp.status_code, detail="Failed to create commit")
        commit_sha = commit_resp.json()["sha"]
        if ref:
            update_ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/refs/heads/{branch}"
            update_data = {"sha": commit_sha}
            update_resp = await client.patch(update_ref_url, headers=headers, json=update_data)
            if update_resp.status_code != 200:
                raise HTTPException(status_code=update_resp.status_code, detail="Failed to update ref")
        else:
            create_ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/refs"
            create_data = {"ref": f"refs/heads/{branch}", "sha": commit_sha}
            create_resp = await client.post(create_ref_url, headers=headers, json=create_data)
            if create_resp.status_code != 201:
                raise HTTPException(status_code=create_resp.status_code, detail="Failed to create ref")
        return {"commit_sha": commit_sha}

# Helper to fetch repo files and contents
async def fetch_repo_files_contents(config: GitHubConfig):
    headers = {"Authorization": f"token {config.token}"}
    default_branch = await get_default_branch(config)
    tree_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/trees/{default_branch}?recursive=1"
    async with httpx.AsyncClient() as client:
        tree_resp = await client.get(tree_url, headers=headers)
        if tree_resp.status_code != 200:
            raise HTTPException(status_code=tree_resp.status_code, detail="Failed to fetch repo tree")
        tree_data = tree_resp.json()
        tree = tree_data.get("tree", [])
        files = [item["path"] for item in tree if item["type"] == "blob"]

        file_contents = {}
        for path in files:
            file_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/contents/{path}"
            file_resp = await client.get(file_url, headers=headers)
            if file_resp.status_code != 200:
                continue
            file_data = file_resp.json()
            content_b64 = file_data.get("content", "")
            encoding = file_data.get("encoding", "")
            if encoding != "base64":
                continue
            try:
                content = base64.b64decode(content_b64).decode("utf-8")
            except Exception:
                content = ""
            file_contents[path] = content
        return file_contents

# Helper to convert uploaded images to low-res base64 strings
async def process_uploaded_files(files: List[UploadFile]) -> List[str]:
    processed_files = []
    for file in files:
        try:
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            # Resize to max width or height 300px preserving aspect ratio
            max_size = (300, 300)
            image.thumbnail(max_size, Image.ANTIALIAS)
            # Save to bytes buffer with quality to keep size < 50KB
            buffer = io.BytesIO()
            quality = 85
            while True:
                buffer.seek(0)
                buffer.truncate(0)
                image.save(buffer, format='JPEG', quality=quality)
                size = buffer.tell()
                if size <= 50 * 1024 or quality <= 20:
                    break
                quality -= 5
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            processed_files.append(encoded)
        except Exception:
            # Skip non-image or error files
            continue
    return processed_files

@app.post("/ask", response_model=AskResponse)
async def ask_anything(
    ask_req: AskRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    uploaded_files: Optional[List[UploadFile]] = File(None)
):
    if not current_user.github_username or not current_user.github_repo or not current_user.github_token or not current_user.openai_token:
        raise HTTPException(status_code=400, detail="GitHub or OpenAI configuration incomplete")

    config = GitHubConfig(username=current_user.github_username, repo=current_user.github_repo, token=current_user.github_token)

    # Fetch repo files and contents
    repo_files = await fetch_repo_files_contents(config)

    # Process uploaded files if any
    encoded_files = []
    if uploaded_files:
        encoded_files = await process_uploaded_files(uploaded_files)

    # Prepare prompt for OpenAI
    prompt_parts = ["You are a helpful assistant. Here are the repository files and their contents:"]
    for path, content in repo_files.items():
        prompt_parts.append(f"File: {path}\nContent:\n{content}\n---")

    if encoded_files:
        prompt_parts.append("Here are some uploaded files encoded in base64 (JPEG, low-res):")
        for idx, ef in enumerate(encoded_files):
            prompt_parts.append(f"File {idx+1}: {ef}")

    prompt_parts.append(f"User prompt: {ask_req.prompt}")
    full_prompt = "\n".join(prompt_parts)

    # Call OpenAI API
    headers = {
        "Authorization": f"Bearer {current_user.openai_token}",
        "Content-Type": "application/json"
    }

    # We use chat completion with system and user messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant that returns JSON diffs of code changes."},
        {"role": "user", "content": full_prompt}
    ]

    payload = {
        "model": "gpt-4",
        "messages": messages,
        "temperature": 0
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(OPENAI_API_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="OpenAI API request failed")
        data = resp.json()

    # Extract content
    try:
        content = data["choices"][0]["message"]["content"]
        # Expecting JSON array of diffs [{path, old, new}]
        diffs_json = json.loads(content)
        diffs = [DiffItem(**item) for item in diffs_json]
    except Exception:
        # If parsing fails, return empty list
        diffs = []

    return AskResponse(diffs=diffs)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
