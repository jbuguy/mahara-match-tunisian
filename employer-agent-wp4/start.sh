docker compose up -d db

cd employer-agent-wp4\frontend
npm.cmd install
npm.cmd run build

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload