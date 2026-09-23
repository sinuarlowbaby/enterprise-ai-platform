# Enterprise AI Platform - Backend Services

FastAPI backend application featuring async lifespan management, health check endpoint, modular chat routing, and strict environment configuration verification on boot.

## 🚀 Quick Start (Python 3.12 & `uv`)

### 1. Create Virtual Environment
```powershell
uv venv --python 3.12 .venv
```

### 2. Activate Virtual Environment
- **Windows PowerShell**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows CMD**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Linux/macOS**:
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```powershell
uv sync --all-extras
# or
uv pip install -e ".[dev]"
```

### 4. Run Development Server
```powershell
uv run uvicorn app.main:app --reload --port 8000
```

- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 5. Run Automated Tests
```powershell
uv run pytest -v
```

## ⚙️ Configuration & Boot Halt Protection
The backend verifies the presence of an active `.env` file either in `backend/.env` or in the parent project root. If `.env` is missing or if mandatory environment variables (`DATABASE_URL`, `REDIS_URL`, `POSTGRES_DB`) are not defined, the server will intentionally abort boot and output a clear diagnostic message.
