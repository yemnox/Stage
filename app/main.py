import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime
import random
from typing import List, Dict, Any
import asyncio
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Equipment Monitoring Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

try:
    templates = Jinja2Templates(directory="templates")
except Exception as e:
    logger.error(f"Error initializing templates: {str(e)}")
    raise

# Mock data for demonstration
class Equipment(BaseModel):
    id: int
    name: str
    status: str
    last_checked: str
    data_rate: float

# Sample equipment data
equipments = [
    Equipment(
        id=1,
        name="Router-1",
        status="online",
        last_checked=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_rate=0.0
    ),
    Equipment(
        id=2,
        name="Switch-1",
        status="online",
        last_checked=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_rate=0.0
    ),
    Equipment(
        id=3,
        name="Firewall-1",
        status="warning",
        last_checked=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_rate=0.0
    ),
]

# Store historical data for charts
data_history: Dict[int, List[Dict[str, Any]]] = {
    eq.id: [] for eq in equipments
}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "equipments": equipments}
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
