# ✦ Memora – Intelligence Hub

**Memora** is a high-end, minimalist personal knowledge retrieval system. It transforms scattered digital footprints into a private, searchable intelligence with a premium "Deep Liquid Mesh" aesthetic.

---

## ✨ Features

- 🌒 **Deep Liquid Mesh UI**: A futuristic, dark-mode research aesthetic with animated background "blobs" and glassmorphism surfaces.
- ⚡ **Staggered Animations**: Fluid entry sequences and micro-animations for a premium desktop-app feel.
- 🔍 **Intelligence Search**: Full-text search with teal-highlighted keyword recall.
- 🏷️ **Auto-Tagging**: Smart topic extraction for every saved page.
- 🛡️ **Robust Scraper**: Advanced browser-fingerprint headers and **Jina AI fallback** to bypass bot-detection (Medium, 1001fonts, etc.).
- 🗄️ **Private Storage**: All data stays local in a SQLite database with FTS5 indexing.

---

## 📁 Project Structure

```
Memora/
│
├── app.py           ← Web Dashboard (The "Intelligence Hub")
├── main.py          ← CLI Interface (Terminal-based)
├── scraper.py       ← Smart Scraper (Requests + BS4 + Jina Fallback)
├── database.py      ← SQLite / FTS5 Engine
├── knowledge.db     ← Your private encrypted-ready database
├── requirements.txt ← Core dependencies
└── .gitignore       ← Clean repo management
```

---

## ⚙️ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Hub
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🖥️ How to Use

1. **Dashboard**: View your total knowledge stats and recent entries.
2. **Add URL**: Paste a link; Memora will scrape, clean, and auto-tag it instantly.
3. **Search**: Find anything across your entire archive with lightning-fast recall.
4. **Delete**: Manage your archive with a minimalist trash-icon interface.

---

## 🛠️ Technical Stack

- **Backend**: Python / Flask
- **Database**: SQLite with FTS5 Extension
- **Frontend**: Vanilla CSS / Glassmorphism / JS Tilt & Stagger
- **Scraping**: BeautifulSoup4 / Requests / Jina AI Proxy

---

*Private · Intelligent · Fluid*