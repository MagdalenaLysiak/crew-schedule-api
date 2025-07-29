# Flight Crew Management System

Web application for managing flight crew assignments and schedules at Luton Airport (LTN). The system handles crew member management, flight data integration and intelligent scheduling with conflict detection.

## Features

### Core Functionality
- **Crew management**: Add, view, and delete crew members (Pilots & Flight Attendants)
- **Flight data integration**: Load real-time flight data from AviationStack API
- **Scheduling**: Assign crew to flights with automatic conflict detection
- **Schedule view**: View and manage crew schedules by date
- **Timezone support**: Timezones handling with GMT offsets

### Business Rules
- **Buffer time**: 3-hour minimum buffer between flight assignments
- **Daily limits**: Maximum 2 flights per crew member per day (1 departure + 1 arrival - must be in this order) 
- **Crew limits**: Maximum 2 pilots and 4 flight attendants per flight
- **Luton-Specific**: Enforces proper departure/arrival sequence for Luton-based operations

## Architecture

### Backend (FastAPI + SQLAlchemy)
```
app/
├── database.py         # database configuration
├── models.py           # SQLAlchemy models
├── schemas.py          # pydantic schemas for API
├── routes.py           # API endpoints
├── utils.py            # flight data utilities
├── validations.py      # business logic validation
└── tests/
```

### Frontend (React + TypeScript)
```
src/
├── components/
│   ├── CrewManager.tsx        # crew member management
│   ├── FlightAssignment.tsx   # flight assignment interface
│   ├── CrewManagementApp.tsx  # schedule viewing and management
│   └── MessageBanner.tsx      # user feedback notifications
├── services/
│   └── apiService.ts          # API communication layer
├── types/
│    └── index.ts              # type definitions
└── tests/
```

## Database Schema

### Core Tables

#### `flights`
- Flight information with timezone data
- Tracks departure/arrival times and durations
- Includes origin/destination GMT offsets

#### `crew_members`
- Staff informatoin (pilots and flight attendants)
- Role-based permissions and availability status

#### `flight_assignments`
- Links crew members to specific flights
- Stores assignment metadata and timing

## Setup and Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- MySQL Server
- MySQL Workbench
- AviationStack API key

### MySQL Installation
1. Download MySQL Community Server from https://dev.mysql.com/downloads/mysql/
2. Run the installer and choose "Developer Default" setup
3. Set root password during installation (remember this password)
4. Ensure MySQL Server is running on localhost:3306

### MySQL Database Setup

**Option 1: Using MySQL Workbench (Recommended)**
1. Open MySQL Workbench
2. Connect to your local MySQL server
3. Run this SQL command:
   ```sql
   CREATE DATABASE crew_db;
   ```

**Option 2: Using Command Line (if mysql command is available)**
```bash
mysql -u root -ppass -e "CREATE DATABASE crew_db;"
```

### Backend Setup
```bash
# First install Python from python.org/downloads/

# IMPORTANT: Run these commands from the ROOT directory

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
# Your prompt should now show (venv) at the beginning

# Install dependencies (make sure venv is activated)
pip install -r requirements.txt

# Configure environment
copy .env.example .env  # On Windows
cp .env.example .env   # On macOS/Linux
# Edit .env file and add:
# - Your AviationStack API key
# - Your MySQL database URL (update username/password/database name as needed)
# Example: DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/crew_db

# Run server (make sure virtual environment is activated)
uvicorn main:app --reload --port 8000

# Run if uvicorn command is not working
pip install backports.zoneinfo

# Alternative if uvicorn command not found
python -m uvicorn main:app --reload --port 8000
```

### Troubleshooting
If you get "Could not import module 'main'" error:
1. **CRITICAL**: Make sure you're in the ROOT directory (crew-schedule-api/) where main.py is located
2. Check that main.py exists in your current directory: `dir main.py` (Windows) or `ls main.py` (macOS/Linux)
3. If main.py is not found, navigate to the correct directory

If you get "uvicorn is not recognized" or "No module named uvicorn" error:
1. Make sure virtual environment is activated: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux)
2. Verify activation worked your prompt should show `(venv)` at the beginning
3. If you have `(venv)` but still get "No module named uvicorn", reinstall dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Verify uvicorn is installed: `pip list | findstr uvicorn` (Windows) or `pip list | grep uvicorn` (macOS/Linux)
5. Alternative without activating venv: `venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000`
6. Make sure you're in the ROOT directory (crew-schedule-api/) not the frontend directory
7. If you get database connection errors, verify:
   - MySQL is running on localhost:3306
   - Database `crew_db` exists (create it: `mysql -u root -ppass -e "CREATE DATABASE crew_db;"`)
   - Username/password in DATABASE_URL are correct
   - Test connection: `mysql -u root -ppass -e "SHOW DATABASES;"`
   - If using different credentials, update DATABASE_URL in .env file

### Frontend Setup
```bash
# First install node.js from nodejs.org/en/download

# IMPORTANT: Run these commands from the FRONTEND directory
cd crew-schedule-ui

# Install dependencies
npm install

# Start development server (runs on http://localhost:3000)
npm run dev
```

## API Endpoints

### Crew Management
- `GET /crew` - list all crew members
- `POST /crew` - create new crew member
- `DELETE /crew/{crew_id}` - delete crew member

### Flight Operations
- `GET /flights` - list all flights
- `POST /load-flights` - load flights from API / only flights from current day (free plan limitations)

### Scheduling
- `POST /assign-flight/{crew_id}/{flight_id}` - assign crew to flight
- `GET /crew/{crew_id}/availability-check/{flight_id}` - check availability
- `GET /schedules` - list all schedules
- `DELETE /assignment/{assignment_id}` - remove assignment

##  Usage Guide

### 1. Add Crew Members
- Navigate to "Crew Management" tab
- Enter crew member name and select role (Pilot/Flight Attendant)
- Click "Add Crew Member"

### 2. Load Flight Data
- Go to "Flight Assignments" tab
- Select a date (optional, defaults to today)
- Click "Load Flights for Date" to fetch from AviationStack API

### 3. Assign Flights
- Select a crew member from the dropdown
- Choose a flight from available flights
- Click "Check Availability' to validate assignment
- If available, click "Assign Flight"

### 4. View Schedules
- Switch to "Schedule Overview" tab
- Use date picker to filter schedules
- View all assignments for selected date

## Business Logic and Validations

### Automatic Conflict Detection
- **Time Conflicts**: Ensures 3-hour buffer between flights
- **Daily Limits**: Prevents over-scheduling (max 2 flights/day)
- **Origin/Destination Consistency**: Prevents booking a return flight arriving at a different airport than the departure airport of the outbound flight.
- **Role Limits**: Enforces crew size restrictions per flight
- **Sequence Validation**: Ensures proper departure/arrival order for Luton flights

### Error Handling
- Validation messages
- API error handling with fallbacks
- Error notifications

## Deployment
**TBC**

## Environment Variables

### Single .env file (in root directory)
```
API_KEY=your_aviationstack_api_key
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/crew_db
FRONTEND_URL=http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000
```

## Future Enhancements

- **Authentication** Secure login and access control for users
- **Mobile version** Responsive design optimized for mobile devices
- **Automatic Return Flight Suggestions** Automatically proposes suitable return flights based on outbound selection
