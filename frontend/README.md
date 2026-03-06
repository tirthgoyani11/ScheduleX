# ScheduleX — Smart Timetable & Resource Optimization

AI-powered timetable scheduling system built for CVM University.

## Tech Stack

- **Frontend:** Vite, React 18, TypeScript, shadcn/ui, Tailwind CSS
- **Backend:** Python 3.14, FastAPI, SQLAlchemy (async), OR-Tools CP-SAT
- **Database:** SQLite (dev) / PostgreSQL (prod)

## Getting Started

```sh
# Install dependencies
npm install

# Start the development server
npm run dev
```

The app runs at `http://localhost:8080` by default.

## Backend

```sh
cd ../timetable_system
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.
