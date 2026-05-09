# 🛒 Retail Sales Dashboard — FastAPI + Streamlit + Gemini AI

## Project Structure

```
retail_app/
├── .env                  ← your secrets (never commit this)
├── .gitignore
├── requirements.txt
├── retail_sales.csv
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
DATA_PATH="retail_sales.csv"
```
Get a free key at: https://aistudio.google.com/app/apikey

### 3. Run the Streamlit frontend
Open a **second terminal** in the `retail_app/` folder:
```bash
streamlit run frontend/app.py
```

### 4. Open the app
Visit : https://retail-data-plots.streamlit.app/

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

Interactive API docs: https://retail-data-plots.streamlit.app/docs

---

## Security
- API key lives only in `.env` — never in code
- `.env` is listed in `.gitignore`
- Each browser tab gets its own session ID
- Sessions are stored in server memory (reset on restart)
