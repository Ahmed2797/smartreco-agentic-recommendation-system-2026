from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import Cookie

from src.database.db import get_db
from src.database import models

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Fix 1: Verify directory path relative to project root
templates = Jinja2Templates(directory="frontend/templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Password Helpers ---
import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     if not plain_password or not hashed_password:
#         return False
#     pwd_bytes = plain_password.encode("utf-8")[:72]
#     hashed_bytes = hashed_password.encode("utf-8")
#     return bcrypt.checkpw(pwd_bytes, hashed_bytes)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    
    # Ensure byte encoding
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


# =====================================
# 1. Register Routes (GET & POST)
# =====================================
@router.get("/register", response_class=HTMLResponse)
def get_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "An account with this email already exists."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Fix 2: Match exact DB Model field names (fallback checks included)
    user_kwargs = {"email": email}
    
    if hasattr(models.User, "full_name"):
        user_kwargs["full_name"] = full_name
    elif hasattr(models.User, "username"):
        user_kwargs["username"] = full_name

    if hasattr(models.User, "hashed_password"):
        user_kwargs["hashed_password"] = hash_password(password)
    else:
        user_kwargs["password_hash"] = hash_password(password)

    new_user = models.User(**user_kwargs)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


# =====================================
# 2. Login Routes (GET & POST)
# =====================================
@router.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    # Verify user and password field safely
    hashed_pwd = getattr(user, "hashed_password", None) or getattr(user, "password_hash", "")
    
    if not user or not verify_password(password, hashed_pwd):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password."}
        )

    # Save session in HTTP-Only Cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return response

@router.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        # raise HTTPException(status_code=400, detail="Invalid email or password")
        return templates.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Invalid email or password."}
                )


    # Save session in HTTP-Only Cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True, path="/")
    return response

    # # Set user_id cookie for isolated tracking per email
    # request.set_cookie(key="user_id", value=str(user.id), httponly=True)
    # return {"message": "Success", "user_id": user.id, "email": user.email}


# =====================================
# 3. Logout Route
# =====================================
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="user_id")
    return response



def get_current_user(
    user_id: str = Cookie(None), 
    db: Session = Depends(get_db)
):
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/auth/login"})
    
    # 🟢 Convert string cookie to integer safely
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=307, headers={"Location": "/auth/login"})

    user = db.query(models.User).filter(models.User.id == user_id_int).first()
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/auth/login"})

    return user