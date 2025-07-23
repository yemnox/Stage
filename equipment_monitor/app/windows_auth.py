import os
import win32api
import win32security
import win32con
from typing import Optional, Dict, Tuple

def get_windows_username() -> Optional[str]:
    """Get the username of the currently logged-in Windows user."""
    try:
        return os.getenv('USERNAME')
    except Exception as e:
        print(f"Error getting Windows username: {e}")
        return None

def get_windows_domain() -> Optional[str]:
    """Get the domain of the currently logged-in Windows user."""
    try:
        return os.getenv('USERDOMAIN')
    except Exception as e:
        print(f"Error getting Windows domain: {e}")
        return None

def get_windows_user_info() -> Optional[Dict[str, str]]:
    """Get information about the currently logged-in Windows user."""
    try:
        username = get_windows_username()
        domain = get_windows_domain()
        
        if not username or not domain:
            return None
            
        return {
            'username': username,
            'domain': domain,
            'full_username': f"{domain}\\{username}" if domain else username
        }
    except Exception as e:
        print(f"Error getting Windows user info: {e}")
        return None

def is_user_in_windows_group(username: str, group_name: str) -> bool:
    """Check if a user is a member of a Windows group."""
    try:
        # Get the SID of the group
        try:
            group_sid = win32security.LookupAccountName(None, group_name)[0]
        except:
            # Group not found
            return False
            
        # Get the SID of the user
        try:
            user_sid = win32security.LookupAccountName(None, username)[0]
        except:
            # User not found
            return False
            
        # Get the token of the current process
        token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32con.TOKEN_QUERY | win32con.TOKEN_DUPLICATE | win32con.TOKEN_IMPERSONATE
        )
        
        # Duplicate the token with the required access rights
        token = win32security.DuplicateTokenEx(
            token,
            win32security.SecurityImpersonation,
            win32security.TOKEN_READ
        )
        
        # Check if the user is in the group
        return win32security.CheckTokenMembership(token, group_sid)
        
    except Exception as e:
        print(f"Error checking Windows group membership: {e}")
        return False
