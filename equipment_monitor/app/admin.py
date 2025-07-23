from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from .models import User, Role, Permission, dummy_users
from datetime import datetime
import secrets

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

# Admin middleware to check if user has admin access
async def require_admin(request: Request):
    print("\n=== Admin Access Check ===")
    session_id = request.cookies.get("session_id")
    print(f"Session ID: {session_id}")
    
    if not session_id or session_id not in request.app.state.sessions:
        print("No valid session found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    user_data = request.app.state.sessions[session_id]
    print(f"User data from session: {user_data}")
    
    user = next((u for u in dummy_users.values() if str(u.id) == str(user_data.get("id"))), None)
    print(f"Found user: {user}")
    
    if not user:
        print("User not found in dummy_users")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    print(f"User role: {user.role}")
    print(f"User permissions: {user.permissions}")
    
    has_permission = user.has_permission(Permission.MANAGE_USERS.value)
    print(f"Has MANAGE_USERS permission: {has_permission}")
    
    if not has_permission:
        print("User doesn't have required permission")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    print("Access granted to admin dashboard\n")
    return user

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: User = Depends(require_admin)):
    print("\n=== Admin Dashboard Debug ===")
    print(f"Current User: {user}")
    print(f"User Role: {user.role}")
    print(f"User Permissions: {user.permissions}")
    print(f"All Users: {[u.username for u in dummy_users.values()]}")
    
    # Prepare context with additional debug info
    context = {
        "request": request,
        "users": list(dummy_users.values()),
        "roles": [{"name": role.value["name"], "permissions": list(role.value["permissions"])} for role in Role],
        "permissions": [p.value for p in Permission],
        "current_user": user  # Make sure current_user is available in the template
    }
    
    print(f"Template context: {context.keys()}")
    print("Rendering admin dashboard...\n")
    
    return templates.TemplateResponse("admin/dashboard.html", context)

@router.post("/users/create", response_class=RedirectResponse)
async def create_user(
    request: Request,
    name: str,
    email: str,
    username: str,
    role: str,
    password: str,
    user: User = Depends(require_admin)
):
    if email in dummy_users:
        return RedirectResponse("/admin/dashboard?error=User+already+exists", status_code=303)
    
    # Create new user
    new_user = User(
        id=max(u.id for u in dummy_users.values()) + 1,
        name=name,
        email=email,
        username=username,
        password=password,  # In production, hash the password
        role=role,
        domain="DESKTOP-YEMNOX",
        created_at=datetime.now(),
        is_active=True
    )
    
    dummy_users[email] = new_user
    return RedirectResponse("/admin/dashboard?message=User+created+successfully", status_code=303)

@router.post("/users/{user_id}/delete", response_class=RedirectResponse)
async def delete_user(user_id: int, request: Request, user: User = Depends(require_admin)):
    user_to_delete = next((u for u in dummy_users.values() if u.id == user_id), None)
    if not user_to_delete:
        return RedirectResponse("/admin/dashboard?error=User+not+found", status_code=303)
    
    # Don't allow deleting yourself
    if user_to_delete.id == user.id:
        return RedirectResponse("/admin/dashboard?error=Cannot+delete+your+own+account", status_code=303)
    
    # In a real app, you might want to soft delete
    del dummy_users[user_to_delete.email]
    return RedirectResponse("/admin/dashboard?message=User+deleted+successfully", status_code=303)

@router.post("/users/{user_id}/toggle-active", response_class=RedirectResponse)
async def toggle_user_active(user_id: int, request: Request, user: User = Depends(require_admin)):
    user_to_toggle = next((u for u in dummy_users.values() if u.id == user_id), None)
    if not user_to_toggle:
        return RedirectResponse("/admin/dashboard?error=User+not+found", status_code=303)
    
    if user_to_toggle.id == user.id:
        return RedirectResponse("/admin/dashboard?error=Cannot+deactivate+your+own+account", status_code=303)
    
    user_to_toggle.is_active = not user_to_toggle.is_active
    action = "activated" if user_to_toggle.is_active else "deactivated"
    return RedirectResponse(f"/admin/dashboard?message=User+{action}+successfully", status_code=303)
