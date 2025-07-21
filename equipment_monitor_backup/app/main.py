import logging
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Form
from typing import Optional, Dict
import os
import secrets
import random
from datetime import datetime, timedelta
import asyncio
from .models import User, Equipment, dummy_users, dummy_equipment

# Session management
sessions = {}

app = FastAPI(title="Equipment Monitoring Dashboard")

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

# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Allow access to these paths without authentication
    public_paths = ["/", "/login", "/signup"]
    if any(request.url.path == path for path in public_paths):
        return await call_next(request)
    
    # Check for session cookie
    session_id = request.cookies.get("session_id")
    print(f"Auth check for path: {request.url.path}, Session ID: {session_id}")
    
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

# Authentication routes
@app.get("/dashboard")
async def dashboard(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            print("No session cookie found")
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        session = sessions.get(session_id)
        if not session:
            print(f"Invalid session ID: {session_id}")
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Get the user's email from session
        user_email = session["email"]
        user_name = session["name"]
        
        # Get all equipment data
        equipment_list = equipments
        
        print(f"Dashboard accessed by {user_email}")
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_email": user_email,
            "user_name": user_name,
            "equipment": equipment_list
        })
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, response: Response):
    try:
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")
        
        if not email or not password:
            print("Missing email or password")
            return Response("Please provide both email and password", status_code=400)
        
        # Verify credentials
        user = dummy_users.get(email)
        if not user:
            print(f"User not found: {email}")
            return Response("Invalid email or password", status_code=401)
        
        if user.password != password:
            print(f"Invalid password for {email}")
            return Response("Invalid email or password", status_code=401)
        
        # Create session
        session_id = secrets.token_hex(16)
        sessions[session_id] = {"email": email, "name": user.name}
        print(f"Login successful for {email}")
        
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
        
        print(f"Session cookie set for {email}. Redirecting to /dashboard")
        return response
    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response("An error occurred during login", status_code=500)

@app.post("/logout")
async def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]
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
    if any(user["email"] == email for user in sessions.values()):
        return Response("Email already registered", status_code=400)
    
    # Create session
    session_id = secrets.token_hex(16)
    sessions[session_id] = {
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

@app.get("/api/equipment/{equipment_id}")
async def get_equipment_data(equipment_id: int):
    try:
        equipment = next((eq for eq in equipments if eq.id == equipment_id), None)
        if equipment:
            return equipment
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
                    eq.last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
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
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
