import streamlit as st
import urllib.request
import urllib.parse
import json
import textwrap
st.set_page_config(page_title="WikiSearch 📖", page_icon="📖", layout="centered")
def wiki_search(query: str, limit: int = 5) -> list[dict]:
    """Return a list of search results [{title, snippet}] from Wikipedia."""
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "utf8": 1,
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "WikiSearch-App/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    results = data.get("query", {}).get("search", [])
    return [
        {
            "title": r["title"],
            "snippet": _strip_html(r["snippet"]),
        }
        for r in results
    ]


def wiki_summary(title: str, sentences: int = 5) -> dict:
    """Return intro summary + metadata for a Wikipedia article."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "extracts|info|categories",
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "cllimit": 5,
        "format": "json",
        "utf8": 1,
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "WikiSearch-App/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))

    if "missing" in page:
        return {"error": f'No Wikipedia article found for "{title}".'}

    full_text = page.get("extract", "No content available.")
    all_sentences = [s.strip() for s in full_text.replace("\n", " ").split(".") if s.strip()]
    summary = ". ".join(all_sentences[:sentences]) + "."

    categories = [
        c["title"].replace("Category:", "")
        for c in page.get("categories", [])
        if "hidden" not in c.get("catimpl", "")
    ]

    return {
        "title": page.get("title", title),
        "summary": summary,
        "full_intro": full_text[:3000],
        "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"),
        "categories": categories[:5],
        "word_count": len(full_text.split()),
    }


def _strip_html(text: str) -> str:
    """Remove basic HTML tags from a string."""
    import re
    return re.sub(r"<[^>]+>", "", text)

if "results" not in st.session_state:
    st.session_state.results = []
if "article" not in st.session_state:
    st.session_state.article = None
if "history" not in st.session_state:
    st.session_state.history = []
st.markdown("""
    <h1 style='text-align:center; letter-spacing:3px; font-size:2.5rem;'>📖 WikiSearch</h1>
    <p style='text-align:center; color:gray; margin-top:-12px;'>
        Search & summarize Wikipedia — no browser needed
    </p>
    <hr style='margin-bottom:24px;'>
""", unsafe_allow_html=True)
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input("🔍 Search Wikipedia", placeholder="e.g. Black holes, Python language, World War II…")
with col2:
    num_results = st.selectbox("Results", [3, 5, 8, 10], index=1)

sentences = st.slider("📝 Summary length (sentences)", min_value=2, max_value=10, value=5)

search_btn = st.button("🔎 Search", use_container_width=True, type="primary")
if search_btn and query.strip():
    with st.spinner("Searching Wikipedia…"):
        try:
            st.session_state.results = wiki_search(query.strip(), limit=num_results)
            st.session_state.article = None
            if query not in st.session_state.history:
                st.session_state.history.insert(0, query)
                st.session_state.history = st.session_state.history[:8]
        except Exception as e:
            st.error(f"Search failed: {e}")

if st.session_state.results and st.session_state.article is None:
    st.markdown(f"### 🔎 Results for **\"{query}\"**")
    for i, r in enumerate(st.session_state.results):
        with st.container():
            st.markdown(f"""
                <div style='
                    background:#1a1a2e;
                    border-left:4px solid #3b82f6;
                    border-radius:8px;
                    padding:14px 18px;
                    margin-bottom:10px;
                '>
                    <span style='color:#60a5fa; font-weight:700; font-size:16px;'>{r["title"]}</span><br>
                    <span style='color:#cbd5e1; font-size:13px;'>{r["snippet"]}…</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"📄 Read Summary", key=f"btn_{i}"):
                with st.spinner(f"Loading '{r['title']}'…"):
                    try:
                        st.session_state.article = wiki_summary(r["title"], sentences=sentences)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not load article: {e}")

if st.session_state.article:
    art = st.session_state.article

    if "error" in art:
        st.error(art["error"])
    else:
        if st.button("← Back to results"):
            st.session_state.article = None
            st.rerun()

        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #0f172a, #1e293b);
                border-radius:12px;
                padding:24px 28px;
                margin-bottom:20px;
                border:1px solid #334155;
            '>
                <h2 style='color:#f8fafc; margin:0 0 6px 0;'>📚 {art["title"]}</h2>
                <span style='color:#64748b; font-size:13px;'>
                    ~{art["word_count"]:,} words in intro
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🗒️ Summary")
        st.info(art["summary"])

        if art["categories"]:
            st.markdown("**🏷️ Categories:** " + " · ".join(
                [f"`{c}`" for c in art["categories"]]
            ))

        with st.expander("📖 Full Introduction"):
            st.markdown(art["full_intro"])

        st.markdown(f"🔗 [Read full article on Wikipedia]({art['url']})")

        st.divider()

        with st.expander("📋 Plain text (copy-friendly)"):
            plain = f"=== {art['title']} ===\n\n{art['summary']}\n\nSource: {art['url']}"
            st.code(plain, language=None)

with st.sidebar:
    st.markdown("### 🕘 Recent Searches")
    if st.session_state.history:
        for h in st.session_state.history:
            if st.button(f"🔁 {h}", key=f"hist_{h}", use_container_width=True):
                with st.spinner(f"Searching '{h}'…"):
                    try:
                        st.session_state.results = wiki_search(h, limit=num_results)
                        st.session_state.article = None
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        if st.button("🗑️ Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("Your searches will appear here.")

    st.divider()
    st.markdown("### ℹ️ About")
    st.caption(
        "WikiSearch uses the **Wikipedia API** directly — "
        "no browser, no ads, just clean summaries."
    )

st.markdown("""
    <p style='text-align:center; color:#475569; font-size:12px; margin-top:40px;'>
        WikiSearch 📖 — Powered by the Wikipedia API & Streamlit
    </p>
""", unsafe_allow_html=True)
