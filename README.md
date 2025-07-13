# Equipment Monitoring Dashboard

A real-time equipment monitoring dashboard built with FastAPI and Chart.js, featuring a modern blue color palette.

## Features

- Real-time monitoring of equipment status
- Interactive data rate charts
- Responsive design for all screen sizes
- Clean and modern user interface
- Simulated data for demonstration purposes

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd equipment_monitor
   ```

2. Create and activate a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the FastAPI development server:
   ```bash
   cd app
   uvicorn main:app --reload
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

## Project Structure

```
equipment_monitor/
├── app/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   └── dashboard.html
│   └── main.py
├── tests/
├── requirements.txt
└── README.md
```

## Configuration

The application comes with default settings. To customize the behavior, you can create a `.env` file in the root directory with your configuration:

```env
# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Application settings
UPDATE_INTERVAL=2000  # Data refresh interval in milliseconds
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
