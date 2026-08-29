## KnowAhead Repo Setup

### 1. Clone

```bash
git clone https://github.com/sinetric/syncs-hackathon-team-human.git
cd syncs-hackathon-team-human
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd ../frontend
npm install
```

### 4. Environment variables

Copy `env.example` to `.env` and fill in required API keys when necessary.

### 5. Run

Backend:
```bash
python main.py
```

Frontend:
```bash
npm run dev
```