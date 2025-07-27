.\venv\Scripts\activate #for windows
source venv/bin/activate #for linux
uvicorn app.main:app --reload --port 4000
pip install -r ../requirements.txt #to update the packages
use equipment_monitor