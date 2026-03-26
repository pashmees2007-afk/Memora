import os
import re
from flask import Flask, render_template_string, request, redirect, url_for, flash
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
    <title>Memora – Intelligence Hub</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Great+Vibes&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

        :root {
            --indigo:  #818CF8;
            --cyan:    #22D3EE;
            --violet:  #A78BFA;
            --emerald: #34D399;
            --danger:  #F87171;
            --text:    #F1F5F9;
            --muted:   #94A3B8;
            --cobalt:  #60A5FA;
        }

        html { scroll-behavior: smooth; }

        body {
            font-family: 'Inter', sans-serif;
            background: #0F172A;
            min-height: 100vh;
            color: var(--text);
            position: relative;
            overflow-x: hidden;
        }

        /* ── Deep Liquid Mesh Background ────── */
        .mesh-bg {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: -1;
            overflow: hidden;
            background: #0F172A;
        }
        .blob {
            position: absolute;
            width: 70vmax;
            height: 70vmax;
            border-radius: 50%;
            filter: blur(100px);
            animation: drift 25s infinite alternate ease-in-out;
            opacity: 0.4;
        }
        .blob-1 { top: -20%; left: -20%; background: #1E1B4B; }
        .blob-2 { bottom: -20%; right: -20%; background: #064E3B; opacity: 0.3; animation-delay: -7s; }
        .blob-3 { top: 10%; right: -15%; background: #312E81; opacity: 0.2; animation-delay: -14s; }

        @keyframes drift {
            from { transform: translate(0, 0) scale(1); }
            to   { transform: translate(10%, 10%) scale(1.15); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }

        .container { max-width: 960px; margin: auto; padding: 28px 24px; }

        /* Glass utility */
        .glass {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: saturate(180%) blur(15px);
            -webkit-backdrop-filter: saturate(180%) blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }

        /* Header - Floating Island */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 32px;
            margin: 20px auto 40px;
            width: fit-content;
            border-radius: 100px;
            background: rgba(255, 255, 255, 0.05); /* Higher transparency */
            backdrop-filter: saturate(180%) blur(20px);
            -webkit-backdrop-filter: saturate(180%) blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            animation: slideDown 0.6s ease-out both;
        }
        
        .logo {
            font-family: 'Great Vibes', cursive;
            font-size: 2.4rem;
            background: linear-gradient(180deg, #FFFFFF 0%, #CBD5E1 40%, #94A3B8 60%, #475569 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(129, 140, 248, 0.3);
            text-decoration: none;
        }
        
        nav a {
            margin-left: 1.6rem;
            color: rgba(255, 255, 255, 0.5);
            text-decoration: none;
            font-size: 0.88rem;
            font-weight: 500;
            letter-spacing: 0.4px;
            border-bottom: 2px solid transparent;
            padding-bottom: 2px;
            transition: color 0.25s, border-color 0.25s;
        }
        nav a:hover { color: #fff; border-bottom-color: var(--indigo); }

        /* Flash */
        .alert-success {
            background: rgba(52, 211, 153, 0.1);
            color: var(--emerald);
            padding: 14px 18px;
            border-left: 4px solid var(--emerald);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            font-weight: 500;
            animation: fadeUp 0.4s ease both;
        }

        /* Stat tiles */
        .stats-row { display: flex; gap: 16px; margin-bottom: 2rem; }
        .stat-tile {
            flex: 1;
            padding: 24px 20px;
            border-radius: 24px;
            text-align: center;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: saturate(180%) blur(15px);
            cursor: default;
            transition: transform 0.15s ease;
            animation: springPop 0.7s cubic-bezier(.34,1.56,.64,1) both;
        }
        .stat-tile:hover { transform: translateY(-6px) scale(1.02); }
        .tile-cyan    { box-shadow: 0 10px 30px rgba(34, 211, 238, 0.15); }
        .tile-violet  { box-shadow: 0 10px 30px rgba(167, 139, 250, 0.15); }
        .tile-emerald { box-shadow: 0 10px 30px rgba(52, 211, 153, 0.15); }

        .s-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; position: relative; }
        .s-value { font-size: 2.2rem; font-weight: 700; line-height: 1; position: relative; }
        .tile-cyan .s-value { color: var(--cyan); }
        .tile-violet .s-value { color: var(--violet); font-size: 1.4rem; }
        .tile-emerald .s-value { color: var(--emerald); font-size: 1.1rem; margin-top: 6px; }

        /* Page cards */
        .page-card {
            padding: 22px 24px;
            margin-bottom: 14px;
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: saturate(180%) blur(15px);
            opacity: 0;
            transition: background 0.2s, border-color 0.2s, transform 0.2s;
            animation: fadeUp 0.5s ease both;
        }
        .page-card:hover { 
            background: rgba(255, 255, 255, 0.06); 
            border-color: rgba(129, 140, 248, 0.3);
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(129, 140, 248, 0.1);
        }
        .page-card h3 { color: #fff; font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; }
        .url-link {
            color: var(--cobalt);
            font-size: 0.82rem;
            text-decoration: none;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 92%;
            margin-bottom: 8px;
        }
        .url-link:hover { color: #93C5FD; }
        .snippet { color: var(--muted); font-size: 0.88rem; line-height: 1.6; margin-top: 6px; }
        .tag-pill {
            display: inline-block;
            background: rgba(129, 140, 248, 0.15);
            color: var(--indigo);
            border: 1px solid rgba(129, 140, 248, 0.3);
            padding: 2px 10px;
            border-radius: 100px;
            font-size: 0.72rem;
            letter-spacing: 0.5px;
            margin: 6px 2px 0;
        }
        .card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; }
        .card-meta { font-size: 0.72rem; color: rgba(148, 163, 184, 0.5); }

        /* Trash button */
        .trash-form { margin:0; }
        .trash-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: rgba(248,113,113,.35);
            font-size: 1.1rem;
            padding: 4px 7px;
            border-radius: 8px;
            transition: color .2s, background .2s;
        }
        .trash-btn:hover { color:var(--danger); background:rgba(248,113,113,.1); }

        /* Section label */
        .section-heading {
            font-size:.72rem; font-weight:600; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:1rem;
        }

        /* Inputs */
        .pill-input {
            flex: 1;
            padding: 13px 20px;
            border-radius: 100px;
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.12);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            font-size: .95rem;
            outline: none;
            transition: border-color .25s, box-shadow .25s;
            box-sizing: border-box;
            min-width: 0;
        }
        .pill-input:focus { border-color:var(--indigo); box-shadow:0 0 0 3px rgba(129,140,248,.18); }
        .pill-input::placeholder { color:rgba(148,163,184,.4); }
        .pill-btn {
            padding: 13px 26px;
            border-radius: 100px;
            background: var(--indigo);
            color: #fff;
            border: none;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: .9rem;
            cursor: pointer;
            transition: background .2s, transform .15s;
            white-space: nowrap;
        }
        .pill-btn:hover { background:#6D63F5; transform:scale(1.03); }

        /* Empty state */
        .empty-state { text-align:center; padding:4rem 1rem; color:var(--muted); }
        .empty-state h3 { color:rgba(255,255,255,.3); margin-bottom:.5rem; }

        /* Animations */
        @keyframes slideDown {
            from { opacity:0; transform:translateY(-20px); }
            to   { opacity:1; transform:translateY(0); }
        }
        @keyframes springPop {
            from { opacity:0; transform:scale(.85) translateY(10px); }
            to   { opacity:1; transform:scale(1) translateY(0); }
        }
        @keyframes fadeUp {
            from { opacity:0; transform:translateY(16px); }
            to   { opacity:1; transform:translateY(0); }
        }
    </style>
</head>
<body>
<div class="mesh-bg">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
</div>
<div class="container">
    <header>
        <a href="{{ url_for('hero') }}" class="logo">Memora</a>
        <nav>
            <a href="{{ url_for('dashboard') }}">Home</a>
            <a href="{{ url_for('search') }}">Search</a>
            <a href="{{ url_for('add') }}">Add URL</a>
        </nav>
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}{% for m in messages %}
        <div class="alert-success">{{ m }}</div>
      {% endfor %}{% endif %}
    {% endwith %}

    <main>{% block content %}{% endblock %}</main>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // Tilt effect on stat tiles
    document.querySelectorAll('.stat-tile').forEach(tile => {
        tile.addEventListener('mousemove', e => {
            const r = tile.getBoundingClientRect();
            const x = ((e.clientX - r.left) / r.width  - .5) * 16;
            const y = ((e.clientY - r.top)  / r.height - .5) * -16;
            tile.style.transform = `perspective(500px) rotateX(${y}deg) rotateY(${x}deg) translateY(-4px)`;
        });
        tile.addEventListener('mouseleave', () => tile.style.transform = '');
    });
    // Staggered reveal for page cards
    document.querySelectorAll('.page-card').forEach((c, i) => {
        c.style.animationDelay = (.05 * i + .2) + 's';
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
            {% for t in page.tags.split(', ') %}<span class="tag-pill">{{ t }}</span>{% endfor %}
        {% endif %}
        <div class="card-footer">
            <span class="card-meta">Added {{ page.date_added|string|truncate(16, True, '') }} &nbsp;&#183;&nbsp; ID {{ page.id }}</span>
            <form action="{{ url_for('delete', page_id=page.id) }}" method="post" class="trash-form">
                <button class="trash-btn" type="submit" title="Delete" onclick="return confirm('Delete this page?')">&#128465;</button>
            </form>
        </div>
    </div>
    {% endfor %}
{% else %}
    <div class="empty-state glass">
        <h3>Your archive is empty</h3>
        <p>Head to <strong>Add URL</strong> to save your first piece of knowledge.</p>
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
            <p class="snippet">{{ highlight_func(row.content, query) }}</p>
            {% if row.tags %}
                {% for t in row.tags.split(', ') %}<span class="tag-pill">{{ t }}</span>{% endfor %}
            {% endif %}
            <div class="card-footer"><span class="card-meta">ID {{ row.id }}</span></div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty-state glass"><h3>No results</h3><p>Try different keywords.</p></div>
    {% endif %}
{% endif %}
{% endblock %}
"""

ADD_HTML = """
{% extends "base" %}
{% block content %}
<p class="section-heading">Add New Knowledge</p>
<div class="glass" style="padding:32px;">
    <p style="color:var(--muted); margin-bottom:18px; font-size:.9rem;">Paste a URL — Memora will scrape, auto-tag, and index it instantly.</p>
    <form method="post" action="{{ url_for('add') }}" style="display:flex; gap:12px; align-items:center;">
        <input class="pill-input" type="text" name="url" placeholder="https://example.com/article" required>
        <button class="pill-btn" type="submit">Save &#8594;</button>
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
    return HERO_HTML

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
