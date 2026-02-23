# ByeSamosa

Personal Oura Ring data analyzer that replaces the $7/month subscription with AI-powered insights.

Download CSV exports from Oura's Membership Hub (manually or via Playwright automation), import them via CLI, and view health metrics and AI-generated recommendations on a warm, editorial-style dashboard.

## Stack

- **Frontend**: Next.js (App Router) + Tailwind CSS + Recharts + Framer Motion
- **Backend**: FastAPI + Uvicorn
- **Data**: Pydantic models + JSON file storage + Pandas baselines
- **AI**: Claude API for daily health insights

## Setup

```bash
# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..

# Environment variables
cp .env.example .env
# Add your ANTHROPIC_API_KEY (required for AI insights)
```

## Usage

```bash
# Start the full app (FastAPI on :8000 + Next.js on :3000)
python -m byesamosa.pipeline serve

# Pull Oura export via browser automation
python -m byesamosa.pipeline pull

# Import a CSV export manually
python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DD
```

## Data Flow

```
Oura CSV export → Pydantic validation → JSON storage → Pandas baselines → Claude AI insight → Dashboard
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (required for AI insights) |
| `OURA_EMAIL` | Oura account email (for automated pull) |
| `GMAIL_OTP_EMAIL` | Gmail address for receiving Oura OTP codes |
| `GMAIL_OTP_APP_PASSWORD` | Gmail App Password for IMAP access |

## Testing

```bash
pytest tests/
```
