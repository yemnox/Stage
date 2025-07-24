from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app.templates.monitoring
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the monitor instance
from app.templates.monitoring.monitor import monitor, run_monitoring

router = APIRouter(
    prefix="/api/devices",
    tags=["devices"],
    responses={404: {"description": "Not found"}},
)

# Start the monitoring loop when the module is loaded
@router.on_event("startup")
async def startup_event():
    asyncio.create_task(run_monitoring())

@router.get("/status", response_model=List[Dict[str, Any]])
async def get_devices_status():
    """Get the status of all devices."""
    try:
        # Get the current status from the monitor
        status = monitor.get_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting device status: {str(e)}"
        )

@router.get("/status/{device_name}", response_model=Dict[str, Any])
async def get_device_status(device_name: str):
    """Get the status of a specific device."""
    try:
        status = monitor.get_status(device_name)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status for device {device_name}: {str(e)}"
        )

@router.get("/history", response_model=Dict[str, Any])
async def get_devices_history(device_name: str = None):
    """Get the status history of all devices or a specific device."""
    try:
        history = monitor.get_history(device_name)
        return {"history": history}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting device history: {str(e)}"
        )
