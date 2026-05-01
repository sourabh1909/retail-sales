# 🛒 Retail Sales Dashboard — FastAPI + Streamlit + Gemini AI

## Project Structure

```
retail_app/
├── .env                  ← your secrets (never commit this)
├── .gitignore
├── requirements.txt
├── retail_sales.csv
├── backend/
│   ├── main.py           ← FastAPI server (sessions, analytics, AI chat)
│   └── data_loader.py    ← data cleaning & summary builder
└── frontend/
    └── app.py            ← Streamlit dashboard
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your .env file
Edit `.env` and add your free Gemini API key:
```
GEMINI_API_KEY="AIza..."
BACKEND_HOST="127.0.0.1"
BACKEND_PORT=8000
DATA_PATH="retail_sales.csv"
```
Get a free key at: https://aistudio.google.com/app/apikey

### 3. Run the FastAPI backend
Open a terminal in the `retail_app/` folder:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Run the Streamlit frontend
Open a **second terminal** in the `retail_app/` folder:
```bash
streamlit run frontend/app.py
```

### 5. Open the app
Visit: http://localhost:8501

---

## API Endpoints (FastAPI)

| Method | Endpoint                  | Description                  |
|--------|---------------------------|------------------------------|
| GET    | /health                   | Backend health check         |
| POST   | /session/new              | Create a new chat session    |
| GET    | /session/{id}             | Get session metadata         |
| DELETE | /session/{id}             | Clear a session's chat       |
| GET    | /sessions                 | List all active sessions     |
| POST   | /chat                     | Send a message, get AI reply |
| GET    | /analytics/kpis           | Overall KPI metrics          |
| GET    | /analytics/categories     | Stats by category            |
| GET    | /analytics/regions        | Stats by region              |
| GET    | /analytics/monthly        | Monthly sales & profit       |
| GET    | /analytics/raw            | Paginated raw data           |

Interactive API docs: http://localhost:8000/docs

---

## Security
- API key lives only in `.env` — never in code
- `.env` is listed in `.gitignore`
- Each browser tab gets its own session ID
- Sessions are stored in server memory (reset on restart)
