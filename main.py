
"""
main.py - CLI interface for the Personal Knowledge Web Archiver.
Run this file to start the program.

Usage:
    python main.py
"""

import os
import sys

# Windows console encoding fix for unicode characters (emojis, borders)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from scraper import scrape_multiple, load_urls_from_file, generate_tags
from database import setup_database, insert_page, search_pages, get_all_pages, delete_page, get_dashboard_stats

# ─── Pretty-print helpers ──────────────────────────────────────────────────────

DIVIDER = "─" * 60

def print_header():
    """Print the app banner."""
    print("\n" + "═" * 60)
    print("   📚  Personal Knowledge Web Archiver")
    print("═" * 60)


def print_dashboard():
    """Display learning insights dashboard before the menu."""
    stats = get_dashboard_stats()
    print(f"\n{DIVIDER}")
    print("  📊 LEARNING DASHBOARD")
    print(DIVIDER)
    print(f"  Total Pages : {stats['total']}")
    print(f"  Top Topic   : {stats['top_tag']}")
    print(f"  Last Added  : {stats['latest']}")

def print_menu():
    """Print the main menu options."""
    print_dashboard()
    print(f"\n{DIVIDER}")
    print("  MENU")
    print(DIVIDER)
    print("  1. Add URLs (from file or manual input)")
    print("  2. Search saved content")
    print("  3. View all saved pages")
    print("  4. Delete a saved page")
    print("  5. Exit")
    print(DIVIDER)

def get_snippet(content, length=200):
    """Return the first `length` characters of content as a preview."""
    if not content:
        return "(no content)"
    snippet = content[:length].replace("\n", " ").strip()
    return snippet + "..." if len(content) > length else snippet

import re

def highlight_text(content, query, length=200):
    """
    Finds query in content, centers the snippet around it,
    and highlights the keyword by surrounding it with [WORD].
    """
    if not content:
        return "(no content)"
    if not query:
        return get_snippet(content, length)
        
    idx = content.lower().find(query.lower())
    if idx == -1:
        return get_snippet(content, length)
        
    start = max(0, idx - length // 2)
    end = min(len(content), idx + length // 2)
    
    snippet = content[start:end].replace('\n', ' ').strip()
    # Apply highlight rule: uppercase and wrap in brackets
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    highlighted = pattern.sub(lambda m: f"[{m.group(0).upper()}]", snippet)
    
    if start > 0: highlighted = "..." + highlighted
    if end < len(content): highlighted += "..."
    
    return highlighted


# ─── Feature: Add URLs ─────────────────────────────────────────────────────────

def feature_add_urls():
    """
    Let the user add URLs either from a text file or by typing them manually.
    Scrapes each URL and saves results to the database.
    """
    print(f"\n{DIVIDER}")
    print("  ADD URLs")
    print(DIVIDER)
    print("  How would you like to provide URLs?")
    print("  A. Load from a file (urls.txt)")
    print("  B. Enter URLs manually")
    print(DIVIDER)

    choice = input("  Your choice (A/B): ").strip().upper()

    urls = []

    if choice == "A":
        # ── Load from file ────────────────────────────────────────
        filepath = input("  Enter filename (press Enter for 'urls.txt'): ").strip()
        if not filepath:
            filepath = "urls.txt"

        if not os.path.exists(filepath):
            # Create a sample file if it doesn't exist
            print(f"\n  [INFO] '{filepath}' not found. Creating a sample file...")
            with open(filepath, "w") as f:
                f.write("# Add one URL per line (lines starting with # are ignored)\n")
                f.write("https://en.wikipedia.org/wiki/Python_(programming_language)\n")
                f.write("https://en.wikipedia.org/wiki/Artificial_intelligence\n")
            print(f"  [INFO] Sample '{filepath}' created. Edit it and run again.")
            return

        urls = load_urls_from_file(filepath)

    elif choice == "B":
        # ── Manual entry ──────────────────────────────────────────
        print("\n  Enter URLs one per line.")
        print("  Press Enter on a blank line when done.\n")
        while True:
            url = input("  URL: ").strip()
            if not url:
                break
            urls.append(url)

    else:
        print("  [ERROR] Invalid choice. Returning to menu.")
        return

    if not urls:
        print("\n  [INFO] No URLs provided.")
        return

    # ── Scrape and save ───────────────────────────────────────────
    print(f"\n  Scraping {len(urls)} URL(s)...\n")
    scraped_pages = scrape_multiple(urls)

    saved_count = 0
    for page in scraped_pages:
        tags = generate_tags(page["content"])
        success = insert_page(page["url"], page["title"], page["content"], tags)
        if success:
            saved_count += 1

    print(f"\n  ✅ Done! Saved {saved_count} new page(s) to the database.")


# ─── Feature: Search ──────────────────────────────────────────────────────────

def feature_search():
    """
    Let the user enter a search query and display matching pages.
    Uses SQLite FTS5 for full-text search across title and content.
    """
    print(f"\n{DIVIDER}")
    print("  SEARCH")
    print(DIVIDER)

    query = input("  Enter search keyword or phrase: ").strip()

    if not query:
        print("  [INFO] Search query cannot be empty.")
        return

    print(f"\n  Searching for: '{query}'...\n")

    try:
        results = search_pages(query)
    except Exception as e:
        print(f"  [ERROR] Search failed: {e}")
        print("  [TIP] Avoid special characters like: ( ) * \" ' - + :")
        return

    if not results:
        print("  No results found. Try a different keyword.")
        return

    print(f"  Found {len(results)} result(s):\n")

    for i, row in enumerate(results, start=1):
        tags_str = row['tags'] if row['tags'] else 'None'
        print(f"  [{i}] {row['title'] or 'No Title'}")
        print(f"      URL     : {row['url']}")
        print(f"      Tags    : {tags_str}")
        print(f"      Snippet : {highlight_text(row['content'], query)}")
        print()


# ─── Feature: View All ────────────────────────────────────────────────────────

def feature_view_all():
    """
    Display a list of all pages saved in the database.
    Shows ID, title, URL, and the date it was added.
    """
    print(f"\n{DIVIDER}")
    print("  ALL SAVED PAGES")
    print(DIVIDER)

    pages = get_all_pages()

    if not pages:
        print("  No pages saved yet. Use option 1 to add some!")
        return

    print(f"  {len(pages)} page(s) saved:\n")

    for page in pages:
        # Format the date nicely
        date_str = str(page["date_added"])[:16]  # e.g. "2024-01-15 14:30"
        tags_str = page['tags'] if page['tags'] else 'None'
        print(f"  ID: {page['id']}")
        print(f"  Title : {page['title'] or 'No Title'}")
        print(f"  URL   : {page['url']}")
        print(f"  Tags  : {tags_str}")
        print(f"  Added : {date_str}")
        print()


# ─── Feature: Delete ──────────────────────────────────────────────────────────

def feature_delete():
    """
    Let the user delete a saved page by its ID.
    Shows all pages first so the user can pick an ID.
    """
    print(f"\n{DIVIDER}")
    print("  DELETE A PAGE")
    print(DIVIDER)

    # Show saved pages so user knows what IDs exist
    pages = get_all_pages()
    if not pages:
        print("  No pages saved yet.")
        return

    for page in pages:
        print(f"  ID {page['id']}: {page['title'] or page['url']}")

    print()
    try:
        page_id = int(input("  Enter the ID of the page to delete: ").strip())
    except ValueError:
        print("  [ERROR] Please enter a valid number.")
        return

    confirm = input(f"  Are you sure you want to delete page ID {page_id}? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    success = delete_page(page_id)
    if success:
        print(f"  ✅ Page ID {page_id} deleted.")
    else:
        print(f"  [ERROR] No page found with ID {page_id}.")


# ─── Main Program Loop ────────────────────────────────────────────────────────

def main():
    """
    Entry point for the Personal Knowledge Web Archiver.
    Sets up the database and runs the main menu loop.
    """
    print_header()

    # Initialize the database (creates tables if they don't exist)
    setup_database()

    # Main loop
    while True:
        print_menu()
        choice = input("  Enter your choice (1-5): ").strip()

        if choice == "1":
            feature_add_urls()

        elif choice == "2":
            feature_search()

        elif choice == "3":
            feature_view_all()

        elif choice == "4":
            feature_delete()

        elif choice == "5":
            print("\n  Goodbye! Your knowledge base is saved in 'knowledge.db'.\n")
            break

        else:
            print("\n  [ERROR] Invalid choice. Please enter a number from 1 to 5.")


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()