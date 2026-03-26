"""
gui.py - Desktop GUI for the Personal Knowledge Web Archiver
Run with: python gui.py

Design: Warm off-white background, slate-ink typography, teal accent buttons.
Clean editorial feel — like a personal productivity tool you'd actually enjoy using.

Requires: main.py, scraper.py, database.py in the same folder.
"""

import tkinter as tk
from tkinter import messagebox
import threading

# ── Backend imports ────────────────────────────────────────────────────────────
from scraper import scrape_multiple
from database import setup_database, insert_page, search_pages, get_all_pages, delete_page


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS  (change these to retheme the whole app)
# ══════════════════════════════════════════════════════════════════════════════

COLOR = {
    # Backgrounds
    "bg_app":        "#F7F5F2",   # warm off-white — the canvas
    "bg_card":       "#FFFFFF",   # pure white cards / panels
    "bg_sidebar":    "#1E2A38",   # deep navy sidebar
    "bg_input":      "#FFFFFF",
    "bg_hover":      "#E8F4F0",   # subtle teal hover

    # Accent
    "accent":        "#2A9D8F",   # teal — primary action color
    "accent_dark":   "#21867A",   # teal darker (hover)
    "accent_light":  "#D4F0EC",   # teal wash (tag backgrounds)

    # Danger
    "danger":        "#E76F51",
    "danger_dark":   "#D45B3C",

    # Typography
    "text_primary":  "#1A1A2E",   # near-black
    "text_secondary":"#6B7280",   # grey
    "text_muted":    "#9CA3AF",
    "text_white":    "#FFFFFF",
    "text_link":     "#2A9D8F",

    # Borders
    "border":        "#E5E1DB",
    "border_focus":  "#2A9D8F",

    # Status
    "status_ok":     "#2A9D8F",
    "status_err":    "#E76F51",
    "status_info":   "#6B7280",
}

FONT = {
    "title":     ("Georgia", 22, "bold"),
    "subtitle":  ("Georgia", 11, "italic"),
    "heading":   ("Helvetica Neue", 14, "bold"),
    "subhead":   ("Helvetica Neue", 11, "bold"),
    "body":      ("Helvetica Neue", 10),
    "body_sm":   ("Helvetica Neue", 9),
    "btn":       ("Helvetica Neue", 10, "bold"),
    "btn_lg":    ("Helvetica Neue", 12, "bold"),
    "mono":      ("Courier", 9),
    "nav":       ("Helvetica Neue", 10, "bold"),
    "status":    ("Helvetica Neue", 9),
}

PAD = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 40}

NAV_W = 180          # sidebar width
STATUS_H = 28        # status bar height
CARD_RADIUS = 8      # visual only (Canvas used for rounded cards)
BTN_H = 36           # button height


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class HoverButton(tk.Label):
    """
    A styled button built from a Label so we can control every pixel.
    Supports normal / hover / pressed states.
    """

    def __init__(self, parent, text, command=None,
                 bg=None, fg=None, hover_bg=None,
                 font=None, padx=20, pady=8,
                 width=None, cursor="hand2", **kwargs):

        self._bg      = bg       or COLOR["accent"]
        self._fg      = fg       or COLOR["text_white"]
        self._hover   = hover_bg or COLOR["accent_dark"]
        self._cmd     = command

        super().__init__(
            parent,
            text=text,
            bg=self._bg,
            fg=self._fg,
            font=font or FONT["btn"],
            padx=padx,
            pady=pady,
            cursor=cursor,
            relief="flat",
            bd=0,
            **kwargs,
        )
        if width:
            self.config(width=width)

        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        self.config(bg=self._hover)

    def _on_leave(self, _):
        self.config(bg=self._bg)

    def _on_click(self, _):
        self.config(bg=self._bg)
        if self._cmd:
            self._cmd()


class PlaceholderText(tk.Text):
    """Text widget with placeholder / hint text behaviour."""

    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, **kwargs)
        self._placeholder = placeholder
        self._has_placeholder = False
        self._show_placeholder()
        self.bind("<FocusIn>",  self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        self.config(fg=COLOR["text_muted"])
        self.delete("1.0", "end")
        self.insert("1.0", self._placeholder)
        self._has_placeholder = True

    def _on_focus_in(self, _):
        if self._has_placeholder:
            self.delete("1.0", "end")
            self.config(fg=COLOR["text_primary"])
            self._has_placeholder = False

    def _on_focus_out(self, _):
        if not self.get("1.0", "end").strip():
            self._show_placeholder()

    def real_value(self):
        """Return the actual user-typed text (empty string if placeholder shown)."""
        if self._has_placeholder:
            return ""
        return self.get("1.0", "end").strip()


class ScrollableFrame(tk.Frame):
    """A vertically-scrollable container."""

    def __init__(self, parent, bg=COLOR["bg_app"], **kwargs):
        outer = tk.Frame(parent, bg=bg, **kwargs)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical",
                                 command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=bg)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_resize(event):
            canvas.itemconfig(window_id, width=event.width)

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_canvas_resize)

        # Mouse-wheel scrolling
        def _scroll(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _scroll)

        # Expose inner frame as self.frame
        self.frame = inner
        # Expose outer as self (so .pack / .grid work on the outer container)
        self._outer = outer

    def pack(self, **kwargs):
        self._outer.pack(**kwargs)

    def grid(self, **kwargs):
        self._outer.grid(**kwargs)


class Divider(tk.Frame):
    """A thin horizontal rule."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=1,
                         bg=COLOR["border"], **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
#  RESULT CARD  (used in Search and View All)
# ══════════════════════════════════════════════════════════════════════════════

def make_result_card(parent, row_data, show_id=False):
    """
    Build a single result card widget.
    row_data must have keys: title, url, content (or snippet), id, date_added (optional)
    """
    card = tk.Frame(parent, bg=COLOR["bg_card"],
                    highlightbackground=COLOR["border"],
                    highlightthickness=1)
    card.pack(fill="x", pady=(0, PAD["sm"]), padx=2)

    inner = tk.Frame(card, bg=COLOR["bg_card"])
    inner.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])

    # ── Top row: ID tag + title ─────────────────────────────────
    top = tk.Frame(inner, bg=COLOR["bg_card"])
    top.pack(fill="x")

    if show_id:
        id_badge = tk.Label(top, text=f" #{row_data.get('id', '?')} ",
                            bg=COLOR["accent_light"], fg=COLOR["accent"],
                            font=FONT["body_sm"], padx=4)
        id_badge.pack(side="left", padx=(0, PAD["xs"]))

    title_text = row_data.get("title") or "Untitled"
    tk.Label(top, text=title_text,
             bg=COLOR["bg_card"], fg=COLOR["text_primary"],
             font=FONT["subhead"],
             anchor="w", wraplength=600, justify="left"
             ).pack(side="left", fill="x", expand=True)

    # ── URL and Tags ─────────────────────────────────────────────
    url_label = tk.Label(inner,
                         text=row_data.get("url", ""),
                         bg=COLOR["bg_card"], fg=COLOR["text_link"],
                         font=FONT["body_sm"],
                         anchor="w", wraplength=620, justify="left",
                         cursor="hand2")
    url_label.pack(fill="x", pady=(2, 0))

    tags = row_data.get("tags")
    if tags:
        tk.Label(inner, text=f"Tags: {tags}",
                 bg=COLOR["bg_card"], fg=COLOR["accent"],
                 font=FONT["body_sm"], anchor="w").pack(fill="x", pady=(2, 0))

    # ── Snippet / content ────────────────────────────────────────
    content = row_data.get("content") or row_data.get("snippet") or ""
    snippet = content[:260].replace("\n", " ").strip()
    if len(content) > 260:
        snippet += "…"

    if snippet:
        # Check if we should highlight a query (simple bracket highlight simulation)
        query = row_data.get("query", "")
        if query and query.lower() in snippet.lower():
            # Basic text display, no rich text formatting in basic tk.Label
            # We just show the snippet as generated by highlight_text from backend
            pass
            
        tk.Label(inner, text=snippet,
                 bg=COLOR["bg_card"], fg=COLOR["text_secondary"],
                 font=FONT["body_sm"],
                 anchor="w", wraplength=620, justify="left"
                 ).pack(fill="x", pady=(4, 0))

    # ── Date and Delete Row ──────────────────────────────────────────
    bottom_row = tk.Frame(inner, bg=COLOR["bg_card"])
    bottom_row.pack(fill="x", pady=(8, 0))
    
    date_val = row_data.get("date_added")
    if date_val:
        date_str = str(date_val)[:16]
        tk.Label(bottom_row, text=f"Saved {date_str}",
                 bg=COLOR["bg_card"], fg=COLOR["text_muted"],
                 font=FONT["body_sm"], anchor="w"
                 ).pack(side="left")

    del_cmd = row_data.get("delete_cmd")
    if del_cmd:
        HoverButton(bottom_row, text="Delete", bg=COLOR["danger"], hover_bg=COLOR["danger_dark"], padx=10, pady=2, command=lambda: del_cmd(row_data['id'])).pack(side="right")

    return card


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION CLASS
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    """
    Root window. Holds the sidebar nav + a content area.
    Each 'screen' is built by clearing and repopulating self.content_frame.
    """

    def __init__(self):
        super().__init__()
        self.title("Personal Knowledge Web Archiver")
        self.geometry("900x600")
        self.configure(bg=COLOR["bg_app"])
        setup_database()
        
        # Setup sidebar and main area
        self.sidebar = tk.Frame(self, bg=COLOR["bg_sidebar"], width=NAV_W)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.main_area = tk.Frame(self, bg=COLOR["bg_app"])
        self.main_area.pack(side="left", fill="both", expand=True)

        # Nav Title
        tk.Label(self.sidebar, text="Archiver", font=FONT["heading"], bg=COLOR["bg_sidebar"], fg=COLOR["text_white"]).pack(pady=20)
        
        # Nav Buttons
        HoverButton(self.sidebar, text="Home", bg=COLOR["bg_sidebar"], command=self.show_home).pack(fill="x", pady=2)
        HoverButton(self.sidebar, text="Add URL", bg=COLOR["bg_sidebar"], command=self.show_add).pack(fill="x", pady=2)
        HoverButton(self.sidebar, text="Search", bg=COLOR["bg_sidebar"], command=self.show_search).pack(fill="x", pady=2)

        self.show_home()

    def clear_window(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def show_home(self):
        self.clear_window()
        
        title_fr = tk.Frame(self.main_area, bg=COLOR["bg_app"])
        title_fr.pack(fill="x", padx=PAD["lg"], pady=(PAD["lg"], 0))
        tk.Label(title_fr, text="Dashboard", font=FONT["title"], bg=COLOR["bg_app"], fg=COLOR["text_primary"]).pack(side="left")

        # Display Learning Dashboard
        from database import get_dashboard_stats
        stats = get_dashboard_stats()
        
        dash = tk.Frame(self.main_area, bg=COLOR["bg_card"], highlightbackground=COLOR["border"], highlightthickness=1)
        dash.pack(pady=20, padx=PAD["lg"], fill="x")
        
        tk.Label(dash, text="📊 Learning Insights", font=FONT["heading"], bg=COLOR["bg_card"], fg=COLOR["accent"]).pack(pady=(15, 10))
        tk.Label(dash, text=f"Total Pages: {stats['total']}", font=FONT["body"], bg=COLOR["bg_card"], fg=COLOR["text_primary"]).pack(pady=2)
        tk.Label(dash, text=f"Top Topic: {stats['top_tag']}", font=FONT["body"], bg=COLOR["bg_card"], fg=COLOR["text_primary"]).pack(pady=2)
        tk.Label(dash, text=f"Last Added: {stats['latest']}", font=FONT["body"], bg=COLOR["bg_card"], fg=COLOR["text_primary"]).pack(pady=(2, 15))

        tk.Label(self.main_area, text="Recent Activity", font=FONT["heading"], bg=COLOR["bg_app"], fg=COLOR["text_primary"]).pack(anchor="w", padx=PAD["lg"])
        
        scroll = ScrollableFrame(self.main_area, bg=COLOR["bg_app"])
        scroll.pack(fill="both", expand=True, padx=PAD["lg"], pady=PAD["md"])
        
        def delete_cmd(pid):
            if messagebox.askyesno("Confirm", "Delete this page?"):
                delete_page(pid)
                self.show_home()

        pages = get_all_pages()
        for p in pages[:10]: # show latest 10
            r = dict(p)
            r['delete_cmd'] = delete_cmd 
            make_result_card(scroll.frame, r, show_id=True)
            
    def show_add(self):
        self.clear_window()
        tk.Label(self.main_area, text="Add New Knowledge", font=FONT["title"], bg=COLOR["bg_app"], fg=COLOR["text_primary"]).pack(anchor="w", padx=PAD["lg"], pady=PAD["lg"])
        
        card = tk.Frame(self.main_area, bg=COLOR["bg_card"], highlightbackground=COLOR["border"], highlightthickness=1, padx=20, pady=20)
        card.pack(fill="x", padx=PAD["lg"])
        
        tk.Label(card, text="Paste a web article URL to automatically scrape and auto-tag its contents:", bg=COLOR["bg_card"], fg=COLOR["text_secondary"]).pack(anchor="w", pady=(0, 10))
        
        url_entry = tk.Entry(card, font=FONT["body"], bg=COLOR["bg_input"], relief="solid")
        url_entry.pack(fill="x", pady=10, ipady=5)
        
        status_lbl = tk.Label(card, text="", bg=COLOR["bg_card"], fg=COLOR["status_info"])
        status_lbl.pack(pady=5)
        
        def on_add():
            u = url_entry.get().strip()
            if not u: return
            status_lbl.config(text="Scraping...", fg=COLOR["status_info"])
            self.update_idletasks() # force UI refresh
            
            from scraper import scrape_url, generate_tags
            import threading
            def bg_task():
                title, content = scrape_url(u)
                if title and content:
                    tags = generate_tags(content)
                    succ = insert_page(u, title, content, tags)
                    if succ:
                        msg = f"Saved: {title}"
                        fg = COLOR["status_ok"]
                    else:
                        msg = "Failed or Duplicate."
                        fg = COLOR["status_err"]
                else:
                    msg = "Connection or Scrape Error."
                    fg = COLOR["status_err"]
                # Update UI thread
                status_lbl.after(0, lambda: status_lbl.config(text=msg, fg=fg))
                url_entry.after(0, lambda: url_entry.delete(0, 'end'))
            
            threading.Thread(target=bg_task, daemon=True).start()

        HoverButton(card, text="Scrape & Save", command=on_add).pack(anchor="w", pady=10)

    def show_search(self):
        self.clear_window()
        tk.Label(self.main_area, text="Highlighted Context Search", font=FONT["title"], bg=COLOR["bg_app"], fg=COLOR["text_primary"]).pack(anchor="w", padx=PAD["lg"], pady=PAD["lg"])
        
        search_fr = tk.Frame(self.main_area, bg=COLOR["bg_app"])
        search_fr.pack(fill="x", padx=PAD["lg"])
        
        q_entry = tk.Entry(search_fr, font=FONT["body"], relief="solid")
        q_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))
        
        scroll = ScrollableFrame(self.main_area, bg=COLOR["bg_app"])
        scroll.pack(fill="both", expand=True, padx=PAD["lg"], pady=PAD["md"])
        
        def on_search():
            for w in scroll.frame.winfo_children(): w.destroy()
            q = q_entry.get().strip()
            if not q: return
            res = search_pages(q)
            from main import highlight_text
            
            if not res:
                tk.Label(scroll.frame, text="No matches found.", bg=COLOR["bg_app"], fg=COLOR["text_muted"]).pack(pady=20)
                return
                
            for r in res:
                row = dict(r)
                row["snippet"] = highlight_text(row["content"], q)
                make_result_card(scroll.frame, row, show_id=True)
                
        HoverButton(search_fr, text="Search", command=on_search).pack(side="right")



# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()