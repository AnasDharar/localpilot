"""LocalPilot design tokens and stylesheet — dark, minimal, desktop-assistant aesthetic."""
from __future__ import annotations

# ── Palette ──────────────────────────────────────────────────────────────────
BG_PRIMARY = "#0F1117"          # Deep near-black
BG_SECONDARY = "#161921"        # Slightly lifted panels
BG_TERTIARY = "#1C1F2B"         # Cards / conversation area
BG_INPUT = "#222638"            # Input-ish surfaces
BORDER = "#2A2E3F"              # Subtle dividers
BORDER_FOCUS = "#4A7CFF"        # Focus rings

ACCENT = "#4A7CFF"              # Calm blue accent
ACCENT_HOVER = "#5D8CFF"
ACCENT_PRESSED = "#3968E0"
ACCENT_DIM = "#2A4A99"          # Muted for backgrounds

TEXT_PRIMARY = "#E8EAED"        # Main text
TEXT_SECONDARY = "#9CA3AF"      # Labels, hints
TEXT_MUTED = "#6B7280"          # Footer, timestamps
TEXT_INVERSE = "#FFFFFF"        # On accent backgrounds

SUCCESS = "#34D399"             # Green — ready / success
WARNING = "#FBBF24"             # Amber — processing
ERROR = "#F87171"               # Soft red — errors
LISTENING = "#818CF8"           # Indigo-violet — listening

SCROLLBAR_BG = BG_SECONDARY
SCROLLBAR_HANDLE = "#2A2E3F"
SCROLLBAR_HOVER = "#363B50"

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI, Inter, Roboto, sans-serif"
FONT_SIZE_XS = "11px"
FONT_SIZE_SM = "12px"
FONT_SIZE_MD = "13px"
FONT_SIZE_LG = "15px"
FONT_SIZE_XL = "20px"
FONT_SIZE_TITLE = "22px"

# ── Spacing & Radii ─────────────────────────────────────────────────────────
RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_LG = "14px"
RADIUS_ROUND = "50%"

# ── Microphone button ───────────────────────────────────────────────────────
MIC_SIZE = 64
MIC_ICON_IDLE = "🎤"
MIC_ICON_LISTENING = "⏹"

# ── Stylesheet ───────────────────────────────────────────────────────────────

def build_stylesheet() -> str:
    """Return the complete QSS for the application."""
    return f"""
    /* ── Global ────────────────────────────────────────────────────── */
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_MD};
        color: {TEXT_PRIMARY};
        background: transparent;
    }}
    QMainWindow {{
        background: {BG_PRIMARY};
    }}

    /* ── Scroll area ───────────────────────────────────────────────── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {SCROLLBAR_BG};
        width: 6px;
        border: none;
        border-radius: 3px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {SCROLLBAR_HANDLE};
        min-height: 28px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {SCROLLBAR_HOVER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}

    /* ── Labels ─────────────────────────────────────────────────────── */
    QLabel {{
        background: transparent;
        padding: 0px;
    }}
    QLabel#appTitle {{
        font-size: {FONT_SIZE_TITLE};
        font-weight: 700;
        color: {TEXT_PRIMARY};
        letter-spacing: 0.5px;
    }}
    QLabel#statusDot {{
        font-size: 8px;
    }}
    QLabel#statusLabel {{
        font-size: {FONT_SIZE_SM};
        color: {TEXT_SECONDARY};
    }}
    QLabel#footerLabel {{
        font-size: {FONT_SIZE_XS};
        color: {TEXT_MUTED};
    }}
    QLabel#hintLabel {{
        font-size: {FONT_SIZE_XS};
        color: {TEXT_MUTED};
        font-style: italic;
    }}
    QLabel#activityLabel {{
        font-size: {FONT_SIZE_SM};
        color: {TEXT_SECONDARY};
        padding: 6px 12px;
    }}
    QLabel#timerLabel {{
        font-size: {FONT_SIZE_SM};
        color: {WARNING};
        padding: 4px 10px;
        background: rgba(251, 191, 36, 0.08);
        border-radius: {RADIUS_SM};
    }}
    QLabel#elapsedLabel {{
        font-size: {FONT_SIZE_SM};
        color: {TEXT_MUTED};
        font-variant-numeric: tabular-nums;
    }}

    /* ── Combo box ──────────────────────────────────────────────────── */
    QComboBox {{
        background: {BG_INPUT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM};
        padding: 5px 10px;
        font-size: {FONT_SIZE_SM};
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {ACCENT_DIM};
    }}
    QComboBox:focus {{
        border-color: {BORDER_FOCUS};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background: {BG_INPUT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_DIM};
        selection-color: {TEXT_INVERSE};
        border-radius: {RADIUS_SM};
        outline: none;
    }}

    /* ── Push buttons ──────────────────────────────────────────────── */
    QPushButton {{
        background: {BG_INPUT};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM};
        padding: 6px 16px;
        font-size: {FONT_SIZE_SM};
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {BG_TERTIARY};
        color: {TEXT_PRIMARY};
        border-color: {ACCENT_DIM};
    }}
    QPushButton:pressed {{
        background: {ACCENT_DIM};
    }}
    QPushButton:disabled {{
        color: {TEXT_MUTED};
        border-color: {BORDER};
        background: {BG_SECONDARY};
    }}

    /* Primary action button */
    QPushButton#primaryBtn {{
        background: {ACCENT};
        color: {TEXT_INVERSE};
        border: none;
        font-weight: 600;
        padding: 8px 20px;
        border-radius: {RADIUS_MD};
    }}
    QPushButton#primaryBtn:hover {{
        background: {ACCENT_HOVER};
    }}
    QPushButton#primaryBtn:pressed {{
        background: {ACCENT_PRESSED};
    }}
    QPushButton#primaryBtn:disabled {{
        background: {ACCENT_DIM};
        color: {TEXT_MUTED};
    }}

    /* ── Card panels ───────────────────────────────────────────────── */
    QFrame#card {{
        background: {BG_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_LG};
    }}
    QFrame#conversationCard {{
        background: {BG_TERTIARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_LG};
    }}

    /* ── Text edit (transcript display) ────────────────────────────── */
    QTextEdit {{
        background: transparent;
        color: {TEXT_PRIMARY};
        border: none;
        font-size: {FONT_SIZE_MD};
        selection-background-color: {ACCENT_DIM};
    }}
    """
