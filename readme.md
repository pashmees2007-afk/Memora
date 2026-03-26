
# 📚 Personal Knowledge Web Archiver

A lightweight Python tool to scrape, store, and search web page content — all from your terminal.

---

## 📁 Project Structure

```
personal_knowledge_archiver/
│
├── main.py          ← CLI interface (run this)
├── scraper.py       ← Web scraping logic (requests + BeautifulSoup)
├── database.py      ← SQLite database operations (FTS5 search)
├── urls.txt         ← Sample URL list (edit this)
├── requirements.txt ← Python dependencies
└── README.md        ← This file
```

> `knowledge.db` is created automatically when you run the program.

---

## ⚙️ Setup Instructions

### Step 1 — Make sure Python is installed
You need **Python 3.8 or newer**.

```bash
python --version
```

### Step 2 — Install required libraries

```bash
pip install -r requirements.txt
```

This installs:
- `requests` — for fetching web pages
- `beautifulsoup4` — for parsing HTML

> `sqlite3` is part of Python's standard library — no install needed.

### Step 3 — Run the program

```bash
python main.py
```

---

## 🖥️ How to Use

When you run `main.py`, you'll see this menu:

```
══════════════════════════════════════════════════════════
   📚  Personal Knowledge Web Archiver
══════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────
  MENU
──────────────────────────────────────────────────────────
  1. Add URLs (from file or manual input)
  2. Search saved content
  3. View all saved pages
  4. Delete a saved page
  5. Exit
──────────────────────────────────────────────────────────
```

### Option 1 — Add URLs
- **From file**: Type `A`, then enter a filename (default: `urls.txt`).  
  Edit `urls.txt` to list your desired URLs (one per line).
- **Manually**: Type `B`, then paste/type URLs one by one. Press Enter on a blank line to finish.

### Option 2 — Search
- Enter any keyword (e.g., `machine learning`, `Python`, `history`).
- Results show the page title, URL, and a 200-character content snippet.
- Uses SQLite FTS5 — fast full-text search across all saved content.

### Option 3 — View All Saved Pages
- Lists every saved page with its ID, title, URL, and the date it was saved.

### Option 4 — Delete a Page
- Shows all saved pages and lets you delete one by entering its ID.

### Option 5 — Exit
- Safely exits the program. All data is preserved in `knowledge.db`.

---

## 🗄️ Database Schema

File: `knowledge.db` (created automatically)

**Table: `pages`**
| Column      | Type      | Description                    |
|-------------|-----------|--------------------------------|
| id          | INTEGER   | Auto-incremented primary key   |
| url         | TEXT      | The page URL (unique)          |
| title       | TEXT      | The `<title>` tag content      |
| content     | TEXT      | Extracted + cleaned body text  |
| date_added  | TIMESTAMP | When the page was saved        |

**Virtual Table: `pages_fts`** (FTS5)  
Mirrors `title` and `content` for fast keyword search.

---

## 🔍 How the Search Works

The tool uses SQLite's **FTS5** (Full-Text Search version 5) extension. When you search for a word:
1. SQLite checks the `pages_fts` index (not the raw text — it's faster).
2. Results are ranked by relevance.
3. The app displays the title, URL, and a snippet.

---

## ⚠️ Known Limitations

- Some websites **block scrapers** and will return errors — this is normal.
- JavaScript-heavy websites (SPAs like Twitter, Gmail) won't return useful content — this tool uses `requests`, not a browser.
- Very large pages may take a moment to scrape.

---

## 🧪 Quick Test

1. Run `python main.py`
2. Choose **1 → A → Enter** (uses default `urls.txt`)
3. Wait for pages to be scraped and saved
4. Choose **2**, type `Python` → see search results
5. Choose **3** → see all saved pages

---

## 📦 Dependencies

```
requests==2.31.0
beautifulsoup4==4.12.3
```

`sqlite3` is built into Python (no install needed).

---

*Built with Python 3 · requests · BeautifulSoup4 · SQLite FTS5*