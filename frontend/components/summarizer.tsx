"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ErrorResponse, SummarizeResponse } from "@/lib/types";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: SummarizeResponse }
  | { status: "error"; message: string };

// Base URL of the FastAPI backend. Set NEXT_PUBLIC_API_URL in production.
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const WORDS_PER_MINUTE = 230;

export default function Summarizer() {
  const [url, setUrl] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);
  const isLoading = state.status === "loading";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!url.trim()) {
      setState({ status: "error", message: "Please paste a URL first." });
      inputRef.current?.focus();
      return;
    }

    setState({ status: "loading" });
    try {
      const response = await fetch(`${API_URL}/api/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = (await response.json().catch(() => null)) as SummarizeResponse | ErrorResponse | null;

      if (!response.ok || !data || "error" in data) {
        const message = data && "error" in data ? data.error : `Request failed (HTTP ${response.status}).`;
        setState({ status: "error", message });
        return;
      }
      setState({ status: "success", data });
    } catch {
      setState({
        status: "error",
        message: `Couldn't reach the backend at ${API_URL}. Make sure it is running and try again.`,
      });
    }
  }

  return (
    <>
      <section className="panel" aria-label="Summarize a web page">
        <form className="form" onSubmit={handleSubmit} noValidate>
          <label htmlFor="url" className="label">
            Page URL
          </label>
          <div className="field-row">
            <div className="input-wrap">
              <LinkIcon />
              <input
                ref={inputRef}
                id="url"
                name="url"
                type="text"
                inputMode="url"
                autoComplete="url"
                spellCheck={false}
                placeholder="https://example.com/article"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                disabled={isLoading}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Summarizing...
                </>
              ) : (
                <>
                  Summarize
                  <ArrowIcon />
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      <div className="output" aria-live="polite">
        {state.status === "loading" && <LoadingCard />}
        {state.status === "error" && <ErrorCard message={state.message} />}
        {state.status === "success" && <ResultCard data={state.data} />}
      </div>
    </>
  );
}

function LoadingCard() {
  return (
    <div className="card loading" role="status">
      <div className="progress" aria-hidden="true">
        <span />
      </div>
      <div className="loading-row">
        <span className="spinner" aria-hidden="true" />
        <div>
          <p className="loading-title">Loading...</p>
          <p className="muted">Fetching the page and writing the summary. This usually takes a few seconds.</p>
        </div>
      </div>
      <div className="skeleton" style={{ width: "92%" }} />
      <div className="skeleton" style={{ width: "100%" }} />
      <div className="skeleton" style={{ width: "64%" }} />
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="card error" role="alert">
      <AlertIcon />
      <div>
        <p className="error-title">Couldn&apos;t summarize that page</p>
        <p>{message}</p>
      </div>
    </div>
  );
}

function ResultCard({ data }: { data: SummarizeResponse }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const hostname = new URL(data.url).hostname.replace(/^www\./, "");
  const readingMinutes = Math.max(1, Math.round(data.wordCount / WORDS_PER_MINUTE));

  useEffect(() => () => clearTimeout(timer.current), []);

  async function copySummary() {
    const text = [data.title, "", data.summary, "", ...data.keyPoints.map((point) => `- ${point}`)].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked (e.g. insecure context); nothing useful to do.
    }
  }

  return (
    <article className="card result">
      <p className="result-meta">
        <span className="source">{hostname}</span>
        <span className="sep" aria-hidden="true" />
        <span>{readingMinutes} min read, summarized</span>
      </p>
      <h2 className="result-title">{data.title}</h2>

      <p className="result-summary">{data.summary}</p>

      {data.keyPoints.length > 0 && (
        <>
          <h3 className="section-label">Key points</h3>
          <ol className="points">
            {data.keyPoints.map((point, index) => (
              <li key={index}>
                <span className="point-num">{String(index + 1).padStart(2, "0")}</span>
                <span>{point}</span>
              </li>
            ))}
          </ol>
        </>
      )}

      <div className="result-footer">
        <span className="muted">
          {data.wordCount.toLocaleString()} words scraped
          {data.truncated && " (long page, only the first part was used)"}
        </span>
        <div className="actions">
          <button type="button" className="btn btn-ghost" onClick={copySummary}>
            {copied ? "Copied" : "Copy summary"}
          </button>
          <a className="btn btn-ghost" href={data.url} target="_blank" rel="noopener noreferrer">
            Open page
            <ExternalIcon />
          </a>
        </div>
      </div>
    </article>
  );
}

function LinkIcon() {
  return (
    <svg className="input-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 13a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 0 0-7.07-7.07L11.5 4.43" />
      <path d="M14 11a5 5 0 0 0-7.07 0L4.1 13.83a5 5 0 0 0 7.07 7.07l1.33-1.33" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg className="btn-icon arrow" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function ExternalIcon() {
  return (
    <svg className="btn-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg className="error-icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5v.01" />
    </svg>
  );
}
