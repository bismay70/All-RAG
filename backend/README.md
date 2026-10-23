# RAGLab AI Backend

## Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

If activation is blocked, keep using `.\.venv\Scripts\python.exe` directly.

## API

- Health: `GET /api/v1/health`
- Docs: `http://localhost:8000/docs`
- Upload: `POST /api/v1/documents`
- Chat: `POST /api/v1/chat`

The backend loads the repository root `.env` without printing secret values.

