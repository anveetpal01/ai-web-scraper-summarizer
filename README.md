# AI Web Scraper & Summarizer

A full-stack app: paste a web page URL, a Python backend scrapes the page's main text, and the Google Gemini API turns it into a short summary with key points.

**Live demo:** _add your deployed frontend URL here_
**Backend API:** _add your deployed backend URL here_ (interactive docs at `/docs`)

## Features

- Simple UI with a URL input, a **Summarize** button and a **Loading...** state while the backend works
- FastAPI backend with a `POST /api/summarize` endpoint and auto-generated API docs (Swagger UI at `/docs`)
- Main-content extraction with BeautifulSoup: strips scripts, styles, navigation, headers, footers and sidebars, and prefers the page's `<article>` / `<main>` element
- AI summary (2–4 sentences) plus 3–5 key points from Gemini's free tier, returned as structured JSON
- Clear error messages for bad URLs, unreachable sites, 404s, non-HTML files (PDFs, images), timeouts and AI quota limits
- Basic SSRF protection: requests to `localhost`, private IP ranges and cloud metadata addresses are blocked, including through redirects
- Unit and API tests with pytest
- Works on mobile, supports light and dark mode

## Tech stack

| Part | Technology |
| --- | --- |
| Frontend | Next.js 16 (React 19, TypeScript), plain CSS |
| Backend | Python, FastAPI, Uvicorn |
| Scraping | httpx (async HTTP client) + BeautifulSoup 4 with the lxml parser |
| AI | Google Gemini API via the official `google-genai` SDK (`gemini-3.5-flash-lite` by default, free tier) |
| Tests | pytest |
| Hosting | Vercel (frontend and backend as two projects) |

## How it works

```
Browser (Next.js frontend, port 3000)
   │  POST http://localhost:8000/api/summarize   { "url": "https://..." }
   ▼
FastAPI backend (port 8000)
   1. Validate and normalize the URL, block private addresses   (app/url_safety.py)
   2. Download the HTML and extract the main text               (app/scraper.py)
   3. Send the text to Gemini, get back { summary, key_points } (app/summarizer.py)
   │
   ▼
JSON response → rendered as a summary card in the UI
```

## Project structure

```
ai-web-scraper-summarizer/
├── backend/                    # Python / FastAPI API
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, routes, error handlers
│   │   ├── config.py           # Settings from environment variables / .env
│   │   ├── schemas.py          # Pydantic request and response models
│   │   ├── scraper.py          # Page download + text extraction
│   │   ├── summarizer.py       # Gemini API call and response parsing
│   │   ├── url_safety.py       # URL validation and private-address checks
│   │   └── errors.py           # AppError (user-facing message + HTTP status)
│   ├── tests/                  # pytest tests
│   ├── .env.example            # Template for backend/.env
│   ├── requirements.txt
│   └── requirements-dev.txt    # + test dependencies
├── frontend/                   # Next.js UI
│   ├── app/                    # Page, layout, styles, favicon
│   ├── components/
│   │   └── summarizer.tsx      # Form, loading, error and result UI
│   ├── lib/types.ts            # API response types
│   ├── .env.example            # Template for frontend/.env.local (optional)
│   └── package.json
└── README.md
```

## Running locally

You need **two terminals**: one for the backend, one for the frontend.

### Prerequisites

- [Python](https://www.python.org/downloads/) **3.10 or newer** (check with `python --version`)
- [Node.js](https://nodejs.org/) **20.9 or newer** (check with `node -v`)
- A free **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey). Sign in with a Google account, click **Create API key**, and copy it. No credit card is needed.

Clone the repository first:

```bash
git clone https://github.com/anveetpal01/ai-web-scraper-summarizer.git
cd ai-web-scraper-summarizer
```

### 1. Backend (FastAPI) — terminal 1

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

#### Where to put the `.env` file

The API key goes in **`backend/.env`**, inside the `backend` folder, next to `requirements.txt`:

```
ai-web-scraper-summarizer/
└── backend/
    ├── .env              ← create it here
    ├── .env.example
    ├── requirements.txt
    └── app/
```

Copy the example file and edit it:

```bash
# macOS / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

```env
GEMINI_API_KEY=your_actual_key_here

# Optional, defaults to gemini-3.5-flash-lite
# GEMINI_MODEL=gemini-3.8-flash

# Optional, defaults to http://localhost:3000
# CORS_ORIGINS=http://localhost:3000
```

The key is only used by the backend and is never sent to the browser. `.env` is listed in `.gitignore`, so it won't be committed.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

### 2. Frontend (Next.js) — terminal 2

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**, paste a URL and press **Summarize**.

The frontend calls the backend at `http://localhost:8000` by default. If your backend runs somewhere else, create `frontend/.env.local` (see `frontend/.env.example`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

No API key is needed in the frontend.

### Calling the backend directly

```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Web_scraping"}'
```

### Running the tests

From the `backend` folder, with the virtual environment active:

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover URL validation, private-address blocking, text extraction and the API's error handling. They don't call the Gemini API, so no key is needed.

## API reference

### `POST /api/summarize`

**Request body**

```json
{ "url": "https://example.com/article" }
```

`https://` is added automatically if the scheme is missing, so `example.com/article` also works.

**Success response (200)**

```json
{
  "url": "https://example.com/article",
  "title": "Article title",
  "summary": "A short 2-4 sentence summary of the page...",
  "keyPoints": ["First key point.", "Second key point.", "Third key point."],
  "wordCount": 1834,
  "truncated": false
}
```

`truncated` is `true` when the page was very long and only the first ~24,000 characters were sent to the AI.

**Error response**

```json
{ "error": "The website responded with HTTP 404." }
```

| Status | When |
| --- | --- |
| 400 | Missing or invalid URL, unsupported scheme, unknown domain, private/local address |
| 415 | The URL is not a web page (PDF, image, etc.) |
| 422 | Not enough readable text on the page (empty, login wall, JavaScript-only) |
| 429 | Gemini free-tier rate limit reached |
| 500 | `GEMINI_API_KEY` missing or invalid |
| 502 / 503 / 504 | The website or the AI service failed or timed out |

### `GET /api/health`

Returns `{ "status": "ok" }`.

## Deploying to Vercel

The frontend and backend are deployed as **two Vercel projects from the same repository**. Vercel supports FastAPI natively and detects the `app` object in `backend/app/main.py`.

**1. Deploy the backend**

1. Go to [vercel.com/new](https://vercel.com/new) and import the repository.
2. Set **Root Directory** to `backend`. Vercel detects FastAPI.
3. Under **Environment Variables**, add `GEMINI_API_KEY`.
4. Deploy. You'll get a URL like `https://your-backend.vercel.app`. Open `/api/health` on it to check it works.

**2. Deploy the frontend**

1. Import the same repository again as a new project.
2. Set **Root Directory** to `frontend`. Vercel detects Next.js.
3. Add the environment variable `NEXT_PUBLIC_API_URL` = your backend URL (no trailing slash).
4. Deploy. You'll get a URL like `https://your-frontend.vercel.app`.

**3. Allow the frontend in the backend's CORS settings**

1. In the backend project, add the environment variable `CORS_ORIGINS` = your frontend URL (for example `https://your-frontend.vercel.app`).
2. Redeploy the backend (**Deployments → ⋯ → Redeploy**) so the change takes effect.

The backend can also run on any Python host such as Render or Railway with the start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Limitations

- Only static HTML is scraped. Pages that render their content with JavaScript (many single-page apps) may return little or no text.
- Some sites block automated requests (Cloudflare challenges, logins, paywalls). Those will show an error instead of a summary.
- Very long pages are trimmed to the first ~24,000 characters before summarizing.
- The Gemini free tier has per-minute and per-day request limits. If you hit them, wait a minute and try again.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "Couldn't reach the backend at http://localhost:8000" | Start the backend (`uvicorn app.main:app --reload --port 8000`) in the `backend` folder |
| "The server is missing GEMINI_API_KEY" | Create `backend/.env` with your key and restart the backend |
| "Gemini rejected the API key" | Copy the key again from AI Studio, with no quotes or spaces around it |
| "The Gemini model ... wasn't found" | Remove `GEMINI_MODEL` from `backend/.env` to use the default, or pick a model from the [Gemini docs](https://ai.google.dev/gemini-api/docs/models) |
| CORS error in the browser console | Add the frontend's URL to `CORS_ORIGINS` in the backend's environment and restart/redeploy it |
| PowerShell won't run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt |
| "The website responded with HTTP 403" | The site blocks scrapers. Try a different page |
