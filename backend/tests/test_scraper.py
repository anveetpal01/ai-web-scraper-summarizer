from app.scraper import clean_lines, extract_content

LONG_PARAGRAPH = "This sentence pads the article so it counts as the main content. " * 10

ARTICLE_PAGE = f"""
<html>
  <head>
    <title>Fallback title</title>
    <meta property="og:title" content="Real   Title">
    <meta name="description" content="A page used in tests.">
    <style>.hidden {{ display: none; }}</style>
  </head>
  <body>
    <header><nav><a href="/">Home</a> <a href="/about">About us</a></nav></header>
    <main>
      <article>
        <header><h1>How scraping works</h1><p>By Jane Doe</p></header>
        <p>First paragraph with
           a line break in the HTML source.</p>
        <p>Second <b>paragraph</b> here.<br>After a line break.</p>
        <p>{LONG_PARAGRAPH}</p>
        <aside>Related links</aside>
        <script>console.log("tracking")</script>
      </article>
    </main>
    <footer>Copyright footer</footer>
  </body>
</html>
"""


def test_extracts_title_and_description() -> None:
    title, description, _ = extract_content(ARTICLE_PAGE)
    assert title == "Real Title"
    assert description == "A page used in tests."


def test_keeps_article_content_and_drops_page_chrome() -> None:
    _, _, text = extract_content(ARTICLE_PAGE)
    lines = text.splitlines()

    assert lines[0] == "How scraping works"
    assert "By Jane Doe" in lines
    assert "First paragraph with a line break in the HTML source." in lines
    assert "Second paragraph here." in lines
    assert "After a line break." in lines

    for unwanted in ("Home", "About us", "Related links", "Copyright footer", "console.log", "display: none"):
        assert unwanted not in text


def test_falls_back_to_body_without_article() -> None:
    html = """
    <body>
      <header>Site header</header>
      <div><h2>Plain page</h2><p>Some text in a div.</p></div>
      <ul><li>One</li><li>Two</li></ul>
    </body>
    """
    _, _, text = extract_content(html)
    assert text.splitlines() == ["Plain page", "Some text in a div.", "One", "Two"]


def test_table_cells_are_separated() -> None:
    _, _, text = extract_content("<table><tr><td>Name</td><td>Age</td></tr><tr><td>Ann</td><td>30</td></tr></table>")
    assert text.splitlines() == ["Name Age", "Ann 30"]


def test_clean_lines_collapses_whitespace_and_duplicates() -> None:
    assert clean_lines("  a   b \n\n a b \n c\t\td \n") == "a b\nc d"
