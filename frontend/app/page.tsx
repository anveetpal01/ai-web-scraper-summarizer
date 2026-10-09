import Summarizer from "@/components/summarizer";

export default function Home() {
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">
          <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="8" />
            <path d="M9 11h14M9 16h14M9 21h8" />
          </svg>
          PageGist
        </span>
        <a
          className="topbar-link"
          href="https://github.com/anveetpal01/ai-web-scraper-summarizer"
          target="_blank"
          rel="noopener noreferrer"
        >
          Source on GitHub
        </a>
      </header>

      <main className="main">
        <section className="intro">
          <h1>Get the gist of any web page.</h1>
        </section>

        <Summarizer />
      </main>
    </div>
  );
}
