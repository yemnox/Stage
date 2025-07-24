import logging
from fastapi import FastAPI, Request, Response, status, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi import Form
from typing import Optional, Dict, Any, List
import os
import secrets
import random
from datetime import datetime, timedelta
import asyncio
import platform
import getpass
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app.routers
sys.path.append(str(Path(__file__).resolve().parent.parent))

from .models import User, Equipment, dummy_users, dummy_equipment, Role, Permission
from .routers import device_routes
from . import admin
from fastapi import HTTPException, status

# Initialize app
app = FastAPI(title="Equipment Monitoring Dashboard")

# Include device monitoring routes
app.include_router(device_routes.router)

# Store sessions in app state
app.state.sessions = {}

# Include admin routes
app.include_router(admin.router)

# Profile route
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in request.app.state.sessions:
            return RedirectResponse(url="/login")
        
        session_data = request.app.state.sessions[session_id]
        user = next((u for u in dummy_users.values() if str(u.id) == str(session_data.get("id"))), None)
        
        if not user:
            return RedirectResponse(url="/login")
            
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "current_user": user,
            "user": user  # For backward compatibility
        })
        
    except Exception as e:
        print(f"Profile page error: {str(e)}")
        return RedirectResponse(url="/login")

# Windows Authentication Configuration
WINDOWS_AUTH_ENABLED = True  # Set to False to disable Windows Auth

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

try:
    templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
except Exception as e:
    print(f"Error initializing templates: {e}")
    templates = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Home page route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

def get_windows_username() -> Optional[str]:
    """Get the username of the currently logged-in Windows user."""
    try:
        return getpass.getuser()
    except Exception as e:
        print(f"Error getting Windows username: {e}")
        return None

async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get the current user from session or Windows authentication."""
    # Check for session cookie first
    session_id = request.cookies.get("session_id")
    if session_id and session_id in request.app.state.sessions:
        return request.app.state.sessions[session_id]
    
    # If no session, try Windows Authentication if enabled
    if WINDOWS_AUTH_ENABLED and platform.system() == 'Windows':
        username = get_windows_username()
        if username:
            # Look for a user with a matching username (case-insensitive)
            username_lower = username.lower()
            user = next((u for u in dummy_users.values() if u.username.lower() == username_lower), None)
            
            if user:
                # Create a fresh User object to ensure permissions are properly initialized
                from .models import User as UserModel
                user_obj = next((u for u in dummy_users.values() if u.id == user.id), None)
                if not user_obj:
                    print(f"User {username} not found in dummy_users")
                    return None
                    
                print(f"Windows auth successful for {user_obj.username} with role {user_obj.role} and permissions: {user_obj.permissions}")
                
                # Create a session for the Windows-authenticated user
                session_id = secrets.token_urlsafe(32)
                user_data = {
                    "id": user_obj.id,
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "role": user_obj.role,
                    "permissions": list(user_obj.permissions) if hasattr(user_obj, 'permissions') else [],
                    "windows_auth": True,
                    "last_activity": datetime.now()
                }
                request.app.state.sessions[session_id] = user_data
                return user_data
    return None

# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Allow access to these paths without authentication
    public_paths = ["/", "/login", "/signup", "/windows-auth"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Get current user
    current_user = await get_current_user(request)
    if not current_user:
        # If this is an API request, return 401
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"}
            )
        # Otherwise redirect to login
        return RedirectResponse(url="/login")
    
    # Add user to request state
    request.state.user = current_user
    
    # Continue with the request
    response = await call_next(request)
    
    # If we have a session ID, make sure it's set in the response
    session_id = request.cookies.get("session_id")
    if session_id in sessions and not request.cookies.get("session_id"):
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=3600,  # 1 hour
            samesite="lax"
        )
    
    return response
    
    if not session_id:
        print("No session ID found in cookies")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    session = sessions.get(session_id)
    if not session:
        print(f"Invalid session ID: {session_id}")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    print(f"Authenticated request from {session.get('email')} for {request.url.path}")
    response = await call_next(request)
    return response

from .models import dummy_equipment, dummy_history

# Use dummy data from models
equipments = dummy_equipment

data_history = {
    eq.id: [data.dict() for data in dummy_history[eq.id].data]
    for eq in equipments
}

@app.get("/api/filters")
async def get_filters():
    from .models import LIGNES, ATELIERS
    return {
        "lignes": LIGNES,
        "ateliers": ATELIERS
    }

# Authentication routes
@app.get("/windows-auth")
async def windows_auth(request: Request, response: Response):
    """Handle Windows Authentication."""
    if not WINDOWS_AUTH_ENABLED or platform.system() != 'Windows':
        return RedirectResponse(url="/login")
    
    username = get_windows_username()
    if not username:
        # If we can't get Windows username, redirect to manual login
        return RedirectResponse(url="/login?auto_redirect=false")
    
    # Check if this Windows user exists in our system (case-insensitive match)
    username_lower = username.lower()
    user = None
    for email, user_obj in dummy_users.items():
        if user_obj.username.lower() == username_lower:
            user = user_obj
            break
    
    if not user:
        # User not found in our system
        return RedirectResponse(url="/login?error=windows_user_not_found")
    
    # Create session for the Windows-authenticated user
    session_id = secrets.token_urlsafe(32)
    request.app.state.sessions[session_id] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": list(user.permissions),
        "windows_auth": True,
        "last_activity": datetime.now()
    }
    
    # Set session cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=3600,  # 1 hour
        samesite="lax"
    )
    
    return response

@app.get("/dashboard")
async def dashboard(request: Request, ligne: Optional[str] = None, atelier: Optional[str] = None):
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in request.app.state.sessions:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        session_data = request.app.state.sessions[session_id]
        if datetime.now() - session_data["last_activity"] > timedelta(hours=1):
            # Session expired
            del request.app.state.sessions[session_id]
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Update last activity
        request.app.state.sessions[session_id]["last_activity"] = datetime.now()
        
        # Get the user's email from session
        user_email = session_data["email"]
        user_name = session_data["username"]
        
        # Get all equipment data and filter by ligne and atelier
        equipment_list = equipments
        if ligne:
            equipment_list = [e for e in equipment_list if e.ligne == ligne]
        if atelier:
            equipment_list = [e for e in equipment_list if e.atelier == atelier]
        
        print(f"Dashboard accessed by {user_email}")
        
        # Get the current user object
        user = next((u for u in dummy_users.values() if u.email == user_email), None)
        
        # Debug output
        print(f"\n=== Dashboard Debug Info ===")
        print(f"Session Data: {session_data}")
        print(f"User Email: {user_email}")
        print(f"Found User: {user}")
        if user:
            print(f"User Role: {user.role}")
            print(f"User Permissions: {user.permissions}")
        print("==========================\n")
        
        # Include the current user in the template context
        context = {
            "request": request,
            "user_email": user_email,
            "user_name": user_name,
            "equipment_list": equipment_list,
            "current_user": user  # Add the user object to the context
        }
        
        print("\n=== Template Context ===")
        print(f"Current User: {user}")
        if user:
            print(f"User Role: {user.role}")
            print(f"User Permissions: {user.permissions}")
        print("======================\n")
        
        return templates.TemplateResponse("dashboard.html", context)
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, auto_redirect: bool = True):
    try:
        print("Login page requested")
        windows_username = None
        if WINDOWS_AUTH_ENABLED and platform.system() == 'Windows':
            windows_username = get_windows_username()
            if windows_username and auto_redirect:
                username_lower = windows_username.lower()
                matching_user = None
                for email, user in dummy_users.items():
                    if user.username.lower() == username_lower:
                        matching_user = user
                        break
                if matching_user:
                    # Instead of auto-redirecting, pre-fill the form
                    return templates.TemplateResponse("login.html", {
                        "request": request,
                        "windows_auth_enabled": True,
                        "prefilled_username": windows_username,
                        "auto_submit": False,
                        "error": request.query_params.get("error", ""),
                        "message": request.query_params.get("message", "")
                    })
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "windows_auth_enabled": WINDOWS_AUTH_ENABLED and platform.system() == 'Windows',
            "prefilled_username": windows_username or "",
            "auto_submit": False,
            "error": request.query_params.get("error", ""),
            "message": request.query_params.get("message", "")
        })
    except Exception as e:
        print(f"Error in login_page: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

@app.post("/login")
async def login(request: Request, response: Response):
    try:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        
        if not username:
            return RedirectResponse("/login?error=username_required", status_code=status.HTTP_303_SEE_OTHER)
        
        # Find user by username (case-insensitive)
        user = None
        for u in dummy_users.values():
            if u.username.lower() == username.lower():
                user = u
                break
        
        # Check if user exists and either:
        # 1. No password is set (Windows auth user), or
        # 2. Password matches (regular user)
        if not user or (user.password and user.password != password):
            print(f"Login failed for username: {username}")
            return RedirectResponse("/login?error=invalid_credentials", status_code=status.HTTP_303_SEE_OTHER)
        
        # Create a fresh User object to ensure permissions are properly initialized
        from .models import User as UserModel
        user_obj = next((u for u in dummy_users.values() if u.id == user.id), None)
        if not user_obj:
            return RedirectResponse("/login?error=user_not_found", status_code=status.HTTP_303_SEE_OTHER)
            
        # Create session with user data
        session_id = secrets.token_urlsafe(32)
        request.app.state.sessions[session_id] = {
            "id": user_obj.id,
            "username": user_obj.username,
            "email": user_obj.email,
            "role": user_obj.role,
            "permissions": list(user_obj.permissions) if hasattr(user_obj, 'permissions') else [],
            "last_activity": datetime.now()
        }
        
        print(f"Session created for {user_obj.username} with role {user_obj.role} and permissions: {user_obj.permissions}")
        
        print(f"Login successful for {user.username} (ID: {user.id})")
        
        # Create response with redirect
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
        # Set session cookie with proper settings
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=3600,  # 1 hour
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="Lax",
            path="/"  # Make cookie available on all paths
        )
        
        print(f"Session cookie set for {user.email}. Redirecting to /dashboard")
        return response
    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response("An error occurred during login", status_code=500)

@app.post("/logout")
async def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id in request.app.state.sessions:
        del request.app.state.sessions[session_id]
    response.delete_cookie("session_id")
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, response: Response):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    name = form_data.get("name")
    
    # Simple user registration
    if any(user["email"] == email for user in request.app.state.sessions.values()):
        return Response("Email already registered", status_code=400)
    
    # Create session
    session_id = secrets.token_hex(16)
    request.app.state.sessions[session_id] = {
        "email": email,
        "name": name
    }
    
    response.set_cookie(key="session_id", value=session_id)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response = JSONResponse(
        content={"message": "Login successful"},
        status_code=status.HTTP_200_OK
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutes
        samesite="lax"
    )
    return response

@app.post("/api/signup")
async def signup(
    name: str = Form(...),
    surname: str = Form(...),
    email: str = Form(...),
    matricule: str = Form(...),
    password: str = Form(...)
):
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    user = create_user(email, matricule, name, surname, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    return {"message": "User created successfully. Please log in."}

@app.post("/api/logout")
async def logout():
    response = JSONResponse(
        content={"message": "Successfully logged out"},
        status_code=status.HTTP_200_OK
    )
    response.delete_cookie("access_token")
    return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "equipments": equipments}
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/equipment")
async def get_equipment():
    try:
        return equipments
    except Exception as e:
        logger.error(f"Error getting equipment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/filters")
async def get_filters():
    """
    Returns the available filters for the dashboard.
    """
    return {
        "lignes": LIGNES,
        "ateliers": ATELIERS
    }

@app.get("/api/equipment/{equipment_id}")
async def get_equipment_data(equipment_id: int):
    try:
        equipment = next((eq for eq in equipments if eq.id == equipment_id), None)
        if equipment:
            equipment_dict = equipment.dict()
            equipment_dict["last_checked"] = equipment.last_checked.isoformat() if equipment.last_checked else None
            return equipment_dict
        return {"error": "Equipment not found"}
    except Exception as e:
        logger.error(f"Error getting equipment {equipment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def update_equipment_data():
    try:
        while True:
            for eq in equipments:
                try:
                    # Simulate data rate changes
                    eq.data_rate = round(random.uniform(10, 100), 2)
                    eq.last_checked = datetime.now()
                    
                    # Update status based on data rate
                    if eq.data_rate > 80:
                        eq.status = "issue"
                    else:
                        eq.status = "online"
                    
                    # Store historical data (keep last 20 points)
                    if eq.id not in data_history:
                        data_history[eq.id] = []
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    data_history[eq.id].append({"time": timestamp, "value": eq.data_rate})
                    data_history[eq.id] = data_history[eq.id][-20:]
                except Exception as e:
                    logger.error(f"Error updating equipment {eq.id}: {str(e)}")
            
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Error in update_equipment_data: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_equipment_data())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=4000, reload=True)
