"""FastAPI application: receives a URL, scrapes it and returns an AI summary."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError
from app.schemas import ErrorResponse, SummarizeRequest, SummarizeResponse
from app.scraper import scrape_page
from app.summarizer import ensure_ai_configured, summarize_page
from app.url_safety import normalize_url

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Web Scraper & Summarizer API",
    description="Scrapes the main text of a web page and summarizes it with Google Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

ERROR_RESPONSES = {status: {"model": ErrorResponse} for status in (400, 415, 422, 429, 500, 502, 503, 504)}


@app.exception_handler(AppError)
async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"error": error.message})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": 'Send a JSON body like {"url": "https://example.com"}.'})


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "AI Web Scraper & Summarizer API. See /docs for the API reference."}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/summarize", response_model=SummarizeResponse, responses=ERROR_RESPONSES)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    try:
        url = normalize_url(request.url)
        ensure_ai_configured()
        page = await scrape_page(url)
        result = await summarize_page(page)
    except AppError:
        raise
    except Exception:
        # Handled here (not by a global handler) so the response still gets CORS headers.
        logger.exception("Unexpected error while summarizing %s", request.url)
        raise AppError("Something went wrong while summarizing this page.", 500) from None

    return SummarizeResponse(
        url=page.url,
        title=page.title,
        summary=result.summary,
        key_points=result.key_points,
        word_count=page.word_count,
        truncated=page.truncated,
    )
