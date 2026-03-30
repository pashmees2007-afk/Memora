import os
import re
from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash
from database import setup_database, get_all_pages, search_pages, insert_page, delete_page, get_dashboard_stats
from scraper import scrape_url, generate_tags

app = Flask(__name__)
app.secret_key = "super_secret_key"
setup_database()

# ─── Helpers ────────────────────────────────────────────────────────────────

def web_highlight(content, query, length=240):
    if not content: return "(no content)"
    snippet = content[:length].replace("\n", " ").strip()
    if len(content) > length: snippet += "..."
    if not query: return snippet
    idx = content.lower().find(query.lower())
    if idx != -1:
        start = max(0, idx - length // 2)
        end = min(len(content), idx + length // 2)
        snippet = content[start:end].replace('\n', ' ').strip()
        if start > 0: snippet = "..." + snippet
        if end < len(content): snippet += "..."
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark style='background:#818CF8; color:#fff; padding:0 4px; border-radius:4px;'>{m.group(0)}</mark>", snippet)

def render(template, **kwargs):
    clean = (template
             .replace('{% extends "base" %}', '')
             .replace('{% block content %}', '')
             .replace('{% endblock %}', ''))
    content = render_template_string(clean, **kwargs)
    dummy = BASE_HTML.replace("{% block content %}{% endblock %}", "<!-- SLOT -->")
    base  = render_template_string(dummy, **kwargs)
    return base.replace("<!-- SLOT -->", content)

# ─── Base Template ───────────────────────────────────────────────────────────

BASE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Memora – Digital Memory Archive</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
</head>
<body>
<div class="container">
    <header>
        <a href="{{ url_for('hero') }}" class="logo">Memora</a>
        <nav>
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('search') }}">Search</a>
            <a href="{{ url_for('add') }}">Add Link</a>
        </nav>
    </header>

    <div id="flash-container">
        {% with messages = get_flashed_messages() %}
          {% if messages %}{% for m in messages %}
            <div class="alert-success">{{ m }}</div>
          {% endfor %}{% endif %}
        {% endwith %}
    </div>

    <main>{% block content %}{% endblock %}</main>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // Staggered reveal for cards
    document.querySelectorAll('.page-card').forEach((c, i) => {
        c.style.opacity = '0';
        c.style.transform = 'translateY(10px)';
        c.style.transition = 'all 0.4s easeOutQuad';
        setTimeout(() => {
            c.style.opacity = '1';
            c.style.transform = 'translateY(0)';
        }, 50 * i + 100);
    });
});
</script>
</body>
</html>"""

# ─── Page Templates ──────────────────────────────────────────────────────────

HOME_HTML = """
{% extends "base" %}
{% block content %}
<div class="stats-row">
    <div class="stat-tile tile-cyan">
        <div class="s-label">Total Pages</div>
        <div class="s-value">{{ stats.total }}</div>
    </div>
    <div class="stat-tile tile-violet">
        <div class="s-label">Top Topic</div>
        <div class="s-value">{{ stats.top_tag }}</div>
    </div>
    <div class="stat-tile tile-emerald">
        <div class="s-label">Last Added</div>
        <div class="s-value">{{ stats.latest|string|truncate(22, True) }}</div>
    </div>
</div>

<p class="section-heading">Saved Knowledge</p>

{% if pages %}
    {% for page in pages %}
    <div class="page-card">
        <h3>{{ page.title or 'Untitled' }}</h3>
        <a href="{{ page.url }}" class="url-link" target="_blank">{{ page.url }}</a>
        {% if page.tags %}
            <div class="tag-row">
                {% for t in page.tags.split(', ') %}<span class="tag-pill">{{ t }}</span>{% endfor %}
            </div>
        {% endif %}
        <div class="card-footer">
            <span class="card-meta">Added {{ page.date_added|string|truncate(16, True, '') }} &nbsp;&#183;&nbsp; ID {{ page.id }}</span>
            <form action="{{ url_for('delete', page_id=page.id) }}" method="post" class="trash-form">
                <button class="trash-btn" type="submit" title="Delete" onclick="return confirm('Delete this page?')">🗑️</button>
            </form>
        </div>
    </div>
    {% endfor %}
{% else %}
    <div class="empty-state">
        <h3>Your archive is empty</h3>
        <p>Head to <strong>Add Link</strong> to save your first piece of knowledge.</p>
    </div>
{% endif %}
{% endblock %}
"""

SEARCH_HTML = """
{% extends "base" %}
{% block content %}
<p class="section-heading">Search Knowledge Base</p>
<form method="get" action="{{ url_for('search') }}" style="display:flex; gap:12px; margin-bottom:2rem; align-items:center;">
    <input class="pill-input" type="text" name="q" value="{{ query }}" placeholder="Search anything — Python, AI, History...">
    <button class="pill-btn" type="submit">Search</button>
</form>
{% if query %}
    <p class="section-heading">Results for &ldquo;{{ query }}&rdquo;</p>
    {% if results %}
        {% for row in results %}
        <div class="page-card">
            <h3>{{ row.title or 'Untitled' }}</h3>
            <a href="{{ row.url }}" class="url-link" target="_blank">{{ row.url }}</a>
            <p class="snippet">{{ highlight_func(row.content, query)|safe }}</p>
            {% if row.tags %}
                <div class="tag-row">
                    {% for t in row.tags.split(', ') %}<span class="tag-pill">{{ t }}</span>{% endfor %}
                </div>
            {% endif %}
            <div class="card-footer"><span class="card-meta">ID {{ row.id }}</span></div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty-state"><h3>No results</h3><p>Try different keywords.</p></div>
    {% endif %}
{% endif %}
{% endblock %}
"""

ADD_HTML = """
{% extends "base" %}
{% block content %}
<p class="section-heading">Add New Knowledge</p>
<div class="glass" style="padding:40px; border-style: solid;">
    <p style="color:var(--text-secondary); margin-bottom:24px; font-size:14px;">Paste a URL — Memora will scrape, auto-tag, and index it instantly for your memory archive.</p>
    <form method="post" action="{{ url_for('add') }}" style="display:flex; gap:12px; align-items:center;">
        <input class="pill-input" type="text" name="url" placeholder="https://example.com/article" required>
        <button class="pill-btn" type="submit">Save Link</button>
    </form>
</div>
{% endblock %}
"""

# ─── Hero Landing Page ────────────────────────────────────────────────────────

HERO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memora</title>
    <link href="https://fonts.googleapis.com/css2?family=Great+Vibes&family=Inter:wght@300;400&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        html, body { height:100%; overflow:hidden; background:#0A0C10; display:flex; align-items:center; justify-content:center; }
        .hero { text-align:center; display:flex; flex-direction:column; align-items:center; gap:1.6rem; }
        .hero-title {
            font-family:'Great Vibes', cursive; font-size:5rem; color:#818CF8;
            text-shadow:0 0 40px rgba(129,140,248,.5), 0 0 80px rgba(129,140,248,.2);
            opacity:0; transform:translateY(20px);
            animation: slideUp 1.2s ease-out 0s forwards, breathe 4s ease-in-out 2s infinite;
        }
        .tagline { display:flex; flex-direction:column; gap:.5rem; }
        .tag-line1 { font-family:'Inter',sans-serif; font-size:1.2rem; font-weight:300; color:#94A3B8; letter-spacing:1px; opacity:0; filter:blur(6px); animation:blurClear 1s ease-out .6s forwards; }
        .tag-line2 { font-family:'Inter',sans-serif; font-size:1.2rem; font-weight:300; color:#94A3B8; letter-spacing:1px; opacity:0; animation:fadein 1.5s ease-out 1s forwards; }
        .divider { width:0; height:1px; background:#818CF8; border:none; animation:expandLine .8s ease-out 1.5s forwards; }
        .enter-btn {
            font-family:'Inter',sans-serif; font-size:.9rem; letter-spacing:2px; text-transform:uppercase;
            color:#818CF8; text-decoration:none; border:1px solid rgba(129,140,248,.4);
            padding:10px 28px; border-radius:100px; opacity:0;
            transition:background .3s, border-color .3s;
            animation:fadein 1s ease-out 2.2s forwards;
        }
        .enter-btn:hover { background:rgba(129,140,248,.12); border-color:#818CF8; }
        @keyframes slideUp  { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes breathe  { 0%,100%{opacity:1} 50%{opacity:.8} }
        @keyframes blurClear{ from{opacity:0;filter:blur(6px)} to{opacity:1;filter:blur(0)} }
        @keyframes fadein   { from{opacity:0} to{opacity:1} }
        @keyframes expandLine{ from{width:0} to{width:40px} }
    </style>
</head>
<body>
<div class="hero">
    <h1 class="hero-title">Memora</h1>
    <div class="tagline">
        <p class="tag-line1">A personal knowledge retrieval system, not just storage.</p>
        <p class="tag-line2">Your scattered digital footprints, indexed into a private intelligence.</p>
    </div>
    <hr class="divider">
    <a href="/app" class="enter-btn">Enter &rarr;</a>
</div>
</body>
</html>"""

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def hero():
    return render_template("landing.html")

@app.route("/app")
def dashboard():
    pages = get_all_pages()
    stats = get_dashboard_stats()
    return render(HOME_HTML, pages=pages, stats=stats)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = search_pages(query) if query else []
    return render(SEARCH_HTML, query=query, results=results, highlight_func=web_highlight)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if url:
            title, content = scrape_url(url)
            if title is not None and content is not None:
                tags = generate_tags(content)
                if insert_page(url, title, content, tags):
                    flash(f"Saved: {title}")
                else:
                    flash("URL already in archive.")
            else:
                flash("Failed to scrape. Check the URL or your connection.")
        return redirect(url_for("dashboard"))
    return render(ADD_HTML)

@app.route("/delete/<int:page_id>", methods=["POST"])
def delete(page_id):
    if delete_page(page_id):
        flash(f"Page #{page_id} deleted.")
    else:
        flash("Could not delete — page not found.")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')
    # Use 0.0.0.0 and dynamic port for cloud hosting (Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
