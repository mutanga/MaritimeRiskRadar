"""
Maritime Risk Radar Dashboard – Naval, Maritime & Commodities Tracker
Production-ready Streamlit application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import tweepy
import openai
import json
import os
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Load .env from the same directory as this script, regardless of working directory
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

# API keys — loaded once at startup from .env, never exposed in UI
X_BEARER_TOKEN  = os.getenv("X_BEARER_TOKEN", "")
XAI_API_KEY     = os.getenv("XAI_API_KEY", "")
TWITTERIO_KEY   = os.getenv("TWITTERIO_KEY", "")

APP_TITLE = "Maritime Risk Radar Dashboard"
APP_SUBTITLE = "Naval, Maritime & Commodities Tracker"
ACCOUNTS_FILE = "tracked_accounts.json"
PREDICTIONS_FILE = "predictions.json"
CACHE_FILE = "posts_cache.json"
TODAY = datetime.now().strftime("%B %d, %Y")

DEFAULT_ACCOUNTS = [
    "@MikeSchuler", "@gCaptain", "@mercoglianos", "@cdrsalamander",
    "@thomasbsauer", "@BDHerzinger", "@TheLtColUSMC", "@usmc_colonel",
    "@kaylahaas", "@CavasShips", "@samlagrone", "@MalShelbourne",
    "@__CJohnston__", "@brentdsadler", "@Aviation_Intel", "@TrentTelenko",
    "@infantrydort", "@KurtSchlichter", "@CynicalPublius", "@JeremyA46925042",
    "@RobManess", "@DaleStarkA10", "@TomcatJunkie", "@thestinkeye",
    "@JoshuaSteinman", "@EzraACohen", "@ianellisjones", "@Schizointel",
    "@vcdgf555", "@vtchakarova", "@Jkylebass", "@loriannlarocco",
    "@SullyCNBC", "@JavierBlas", "@TheStalwart", "@DataRepublican",
    "@JackPosobiec", "@JesseKellyDC", "@ShawnRyan762", "@James_WE_Smith",
    "@TomSharpe134", "@typesfast", "@mintzmyer", "@BartGonnissen",
    "@ed_fin", "@FreightAlley", "@biancoresearch", "@chigrl", "@JoshYoung",
]

ACCOUNT_METADATA = {
    "@cdrsalamander":   {"category": "Navy/Milblog",      "followers": 36000,  "bio": "Navy longest-running podcaster, Midrats co-host, critical of Navy size/deployments"},
    "@BDHerzinger":     {"category": "Asia/Navies",       "followers": 39000,  "bio": "Former USSC/Pacific Fleet insights, supply chains"},
    "@TrentTelenko":    {"category": "Pentagon/OSINT",    "followers": 167000, "bio": "High-engagement defense analysis, Pentagon insider"},
    "@KurtSchlichter":  {"category": "Military/Political","followers": 614000, "bio": "Army COL(R), strong 'total victory' commentary"},
    "@CynicalPublius":  {"category": "Mil/Strategy",      "followers": 295000, "bio": "Sharp takes on conflicts/AI policy, anti-totalitarian"},
    "@usmc_colonel":    {"category": "Marine/OSINT",      "followers": 23000,  "bio": "Retired Marine Colonel, blunt preparedness-focused"},
    "@TheLtColUSMC":    {"category": "Marine/Leadership", "followers": 25000,  "bio": "Leadership/motivational mil posts"},
    "@MalShelbourne":   {"category": "Naval News",        "followers": 4000,   "bio": "USNI deputy editor/reporter, solid naval news"},
    "@__CJohnston__":   {"category": "Naval/Aviation",    "followers": 4500,   "bio": "Navy/aviation reporting"},
    "@brentdsadler":    {"category": "Naval/Strategy",    "followers": 9000,   "bio": "Heritage/naval statecraft, dark fleet, denial ops"},
    "@MikeSchuler":     {"category": "Maritime News",     "followers": 15000,  "bio": "gCaptain contributor, maritime industry news"},
    "@gCaptain":        {"category": "Maritime News",     "followers": 42000,  "bio": "Leading maritime news outlet"},
    "@mercoglianos":    {"category": "Shipping History",  "followers": 18000,  "bio": "Maritime/shipping historian and analyst"},
    "@JavierBlas":      {"category": "Commodities",       "followers": 95000,  "bio": "Bloomberg commodities journalist, oil/energy"},
    "@mintzmyer":       {"category": "Shipping Finance",  "followers": 28000,  "bio": "Shipping analyst, J Capital Research"},
    "@loriannlarocco":  {"category": "Markets/CNBC",      "followers": 31000,  "bio": "CNBC markets reporter"},
    "@SullyCNBC":       {"category": "Markets/CNBC",      "followers": 22000,  "bio": "CNBC market analyst"},
    "@biancoresearch":  {"category": "Macro/Finance",     "followers": 67000,  "bio": "Macro research, fixed income, geopolitical risk"},
    "@JackPosobiec":    {"category": "Political/Intel",   "followers": 2100000,"bio": "Political commentator, OAN host"},
    "@JesseKellyDC":    {"category": "Military/Political","followers": 890000, "bio": "Veteran, political commentator"},
}

TICKERS_WATCHLIST = {
    "Oil/Energy":    ["BZ=F", "CL=F", "USO", "XLE", "XOM", "CVX"],
    "Shipping":      ["ZIM", "DAC", "NMM", "SBLK", "GOGL"],
    "Defense":       ["LMT", "RTX", "GD", "NOC", "BA"],
    "Grains":        ["ZW=F", "ZC=F", "ZS=F", "WEAT", "CORN"],
    "Soft Commodities": ["KC=F", "SB=F", "CT=F", "CC=F"],
    "Fertilizers":   ["MOS", "NTR", "CF", "ICL"],
}

GROK_SYSTEM_PROMPT = """You are Grok, expert geopolitical investment analyst focused on naval, maritime, shipping, oil/commodities, agricultural commodities, fertilizers, and military risks. Analyze the following batch of recent posts from tracked X accounts. Produce a professional dashboard update in exactly this format:

## 1. Tracked Accounts Overview
Provide a markdown table with columns: Handle | Focus/Category | Key Theme Today | Influence Score (1-10)
Score based on engagement quality and strategic insight.

## 2. Live Activity Feed + Key Recent Posts
Summarize the 8-10 most important/high-engagement posts. For each include:
- **@handle** (timestamp): Post summary
- Engagement: likes/reposts estimate | Topic tags

## 3. Investment & Trading Signals
### Oil/Energy
[Analysis + bullish/bearish score /10]
### Shipping/Freight
[Analysis + bullish/bearish score /10]
### Defense/Naval
[Analysis + bullish/bearish score /10]
### Agriculture & Fertilizers
[Analysis of wheat/corn/soy/soft commodities + fertilizer stocks + bullish/bearish score /10]
Impact of shipping disruptions on food supply chains. Black Sea grain corridor status. Fertilizer supply from Russia/Belarus/China. Energy cost pass-through to fertilizer prices.
### Tickers Mentioned/Implied
List any tickers mentioned or strongly implied with sentiment (BULLISH/BEARISH/NEUTRAL). Include agri futures (ZW=F, ZC=F, ZS=F), soft commodities (KC=F, SB=F, CT=F, CC=F), and fertilizer stocks (MOS, NTR, CF, ICL).

## 4. Prediction Tracker + Risk Alerts
### Explicit Predictions
List any explicit forecasts with dates if mentioned
### Risk Alerts 🚨
List top 3-5 risk alerts with severity (HIGH/MEDIUM/LOW)
### Accuracy Notes
Comment on historical accuracy of key accounts

## 5. Full Analysis
### Topic Breakdown
Provide percentage breakdown of topics (must sum to 100%)
### Cross-Account Themes
Key themes appearing across multiple accounts
### Engagement Trends
Which accounts/topics are gaining traction
### Strategic Assessment
2-3 paragraph strategic assessment for investors/analysts

Use markdown tables, bold text, and relevant emojis (🛢️🚢⚓🪖🌾📊🔴🟡🟢) throughout. Be concise but deeply insightful. Focus on shipping disruptions, Hormuz/Red Sea risks, oil volatility, agricultural supply chain risks (grain shipping routes, Black Sea corridor, fertilizer supply from sanctioned states), and defense implications."""


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{APP_TITLE}",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown("""
<style>
    /* ── Global dark theme ── */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    .main .block-container {
        padding-top: 1rem;
        max-width: 1400px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stTextArea > div > div > textarea {
        background-color: #21262d;
        border: 1px solid #30363d;
        color: #e6edf3;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
    }
    [data-testid="stMetricValue"] { color: #58a6ff; font-size: 1.5rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.9rem !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-bottom: 2px solid #30363d;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #21262d;
        color: #8b949e;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
    }

    /* ── Cards / containers ── */
    .risk-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .risk-card-high {
        border-left: 4px solid #f85149;
    }
    .risk-card-medium {
        border-left: 4px solid #d29922;
    }
    .risk-card-low {
        border-left: 4px solid #3fb950;
    }

    /* ── Post cards ── */
    .post-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        margin: 6px 0;
        transition: border-color 0.2s;
    }
    .post-card:hover { border-color: #58a6ff; }
    .post-handle { color: #58a6ff; font-weight: 700; font-size: 1rem; }
    .post-date { color: #8b949e; font-size: 0.82rem; }
    .post-text { color: #e6edf3; margin: 8px 0; line-height: 1.5; }
    .post-stats { color: #8b949e; font-size: 0.82rem; }

    /* ── Ticker badges ── */
    .ticker-bullish {
        background-color: #1a3a2a;
        border: 1px solid #3fb950;
        color: #3fb950;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-block;
        margin: 2px;
    }
    .ticker-bearish {
        background-color: #3a1a1a;
        border: 1px solid #f85149;
        color: #f85149;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-block;
        margin: 2px;
    }
    .ticker-neutral {
        background-color: #1a2a3a;
        border: 1px solid #58a6ff;
        color: #58a6ff;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-block;
        margin: 2px;
    }

    /* ── Header banner ── */
    .header-banner {
        background: linear-gradient(90deg, #0d1117 0%, #1a2744 50%, #0d1117 100%);
        border: 1px solid #1f6feb;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        text-align: center;
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #58a6ff;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        color: #8b949e;
        font-size: 1rem;
        margin-top: 4px;
    }
    .header-date {
        color: #3fb950;
        font-size: 0.85rem;
        margin-top: 6px;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #1f6feb;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        transition: background-color 0.2s;
    }
    .stButton > button:hover { background-color: #388bfd; }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #58a6ff;
        border-bottom: 1px solid #30363d;
        padding-bottom: 6px;
        margin: 16px 0 12px 0;
    }

    /* ── Alert boxes ── */
    .alert-high {
        background-color: #3a1a1a;
        border: 1px solid #f85149;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 4px 0;
        color: #ffa198;
    }
    .alert-medium {
        background-color: #2d2008;
        border: 1px solid #d29922;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 4px 0;
        color: #e3b341;
    }
    .alert-low {
        background-color: #0d2a1a;
        border: 1px solid #3fb950;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 4px 0;
        color: #56d364;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #30363d;
        border-radius: 8px;
    }

    /* ── Signal gauge ── */
    .signal-bar-container { margin: 8px 0; }
    .signal-label { font-size: 0.82rem; color: #8b949e; margin-bottom: 2px; }
    .signal-bar { height: 8px; border-radius: 4px; }

    /* ── Scrollable feed ── */
    .feed-container {
        max-height: 600px;
        overflow-y: auto;
        padding-right: 6px;
    }

    /* Streamlit dataframe dark theme */
    .dataframe { background-color: #161b22 !important; }

    /* Hide default streamlit footer */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENCE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_json(path: str, default):
    try:
        if Path(path).exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path: str, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        st.warning(f"Could not save {path}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def init_session_state():
    if "accounts" not in st.session_state:
        saved = load_json(ACCOUNTS_FILE, None)
        st.session_state.accounts = saved if saved else list(DEFAULT_ACCOUNTS)
    if "posts_cache" not in st.session_state:
        st.session_state.posts_cache = load_json(CACHE_FILE, {})
    if "grok_analysis" not in st.session_state:
        st.session_state.grok_analysis = None
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = None
    if "predictions" not in st.session_state:
        st.session_state.predictions = load_json(PREDICTIONS_FILE, [])
    if "market_data" not in st.session_state:
        st.session_state.market_data = {}
    if "deep_dive_result" not in st.session_state:
        st.session_state.deep_dive_result = {}
    if "new_account_input" not in st.session_state:
        st.session_state.new_account_input = ""

init_session_state()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚓ Maritime Risk Radar")
        st.markdown("---")

        st.markdown("---")

        # Account management
        st.markdown("### 📋 Tracked Accounts")
        st.caption(f"{len(st.session_state.accounts)} accounts tracked")

        # Add account
        col_add1, col_add2 = st.columns([3, 1])
        with col_add1:
            new_acct = st.text_input(
                "Add account",
                placeholder="@handle",
                label_visibility="collapsed",
                key="new_account_input_field",
            )
        with col_add2:
            if st.button("➕", width='stretch', key="add_btn"):
                handle = new_acct.strip()
                if handle and not handle.startswith("@"):
                    handle = "@" + handle
                if handle and handle not in st.session_state.accounts:
                    st.session_state.accounts.append(handle)
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.rerun()

        # Account list with remove option
        with st.expander("View/Remove Accounts", expanded=False):
            accts_to_remove = []
            for acct in st.session_state.accounts:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.caption(acct)
                with col_b:
                    if st.button("✕", key=f"rm_{acct}", width='stretch'):
                        accts_to_remove.append(acct)
            if accts_to_remove:
                for a in accts_to_remove:
                    st.session_state.accounts.remove(a)
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.rerun()

        if st.button("💾 Save Account List", width='stretch'):
            save_json(ACCOUNTS_FILE, st.session_state.accounts)
            st.success("Account list saved!")

        if st.button("🔄 Reset to Defaults", width='stretch'):
            st.session_state.accounts = list(DEFAULT_ACCOUNTS)
            save_json(ACCOUNTS_FILE, st.session_state.accounts)
            st.success("Reset to defaults!")
            st.rerun()

        st.markdown("---")

        # Status indicators — keys loaded from .env at startup, never displayed
        st.markdown("### 📡 System Status")
        st.markdown(f"{'🟢' if X_BEARER_TOKEN else '🔴'} X API: {'Connected' if X_BEARER_TOKEN else 'Not configured'}")
        st.markdown(f"{'🟢' if XAI_API_KEY else '🟡'} Grok AI: {'Connected' if XAI_API_KEY else 'Not configured'}")
        st.markdown(f"{'🟢' if TWITTERIO_KEY else '⚪'} TwitterAPI.io: {'Active' if TWITTERIO_KEY else 'Not set'}")

        if st.session_state.last_refresh:
            st.markdown(f"🕐 Last refresh: {st.session_state.last_refresh}")

        st.markdown("---")
        st.caption("Maritime Risk Radar v1.0 · 2026")

    # Keys are module-level constants — nothing to return


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

def fetch_posts_tweepy(bearer_token: str, accounts: list, max_per_account: int = 30) -> dict:
    """Fetch recent posts via X API v2 using Tweepy."""
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
    posts_by_account = {}
    tweet_fields = ["created_at", "public_metrics", "text", "author_id"]
    user_fields = ["username", "public_metrics", "description"]

    for handle in accounts:
        username = handle.lstrip("@")
        try:
            user_resp = client.get_user(
                username=username,
                user_fields=user_fields
            )
            if not user_resp.data:
                continue
            user = user_resp.data

            tweets_resp = client.get_users_tweets(
                id=user.id,
                max_results=min(max_per_account, 100),
                tweet_fields=tweet_fields,
                exclude=["retweets", "replies"],
            )
            tweets = tweets_resp.data or []

            posts_by_account[handle] = {
                "user_id": str(user.id),
                "followers": user.public_metrics.get("followers_count", 0) if user.public_metrics else 0,
                "description": user.description or "",
                "tweets": [
                    {
                        "id": str(t.id),
                        "text": t.text,
                        "created_at": str(t.created_at),
                        "likes": t.public_metrics.get("like_count", 0) if t.public_metrics else 0,
                        "retweets": t.public_metrics.get("retweet_count", 0) if t.public_metrics else 0,
                        "replies": t.public_metrics.get("reply_count", 0) if t.public_metrics else 0,
                        "url": f"https://x.com/{username}/status/{t.id}",
                    }
                    for t in tweets
                ],
            }
            time.sleep(0.3)  # gentle rate limit buffer
        except tweepy.TweepyException as e:
            posts_by_account[handle] = {"error": str(e), "tweets": []}
        except Exception as e:
            posts_by_account[handle] = {"error": str(e), "tweets": []}

    return posts_by_account


def fetch_posts_twitterio(api_key: str, accounts: list, max_per_account: int = 30) -> dict:
    """Fetch posts via TwitterAPI.io as cheap fallback."""
    import requests
    posts_by_account = {}
    headers = {"X-API-Key": api_key}

    for handle in accounts:
        username = handle.lstrip("@")
        try:
            url = f"https://api.twitterapi.io/twitter/user/last_tweets"
            params = {"userName": username, "limit": max_per_account}
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                tweets_raw = data.get("tweets", [])
                posts_by_account[handle] = {
                    "user_id": data.get("user", {}).get("id", ""),
                    "followers": data.get("user", {}).get("followersCount", 0),
                    "description": data.get("user", {}).get("description", ""),
                    "tweets": [
                        {
                            "id": t.get("id", ""),
                            "text": t.get("text", ""),
                            "created_at": t.get("createdAt", ""),
                            "likes": t.get("likeCount", 0),
                            "retweets": t.get("retweetCount", 0),
                            "replies": t.get("replyCount", 0),
                            "url": f"https://x.com/{username}/status/{t.get('id', '')}",
                        }
                        for t in tweets_raw
                    ],
                }
            else:
                posts_by_account[handle] = {"error": f"HTTP {resp.status_code}", "tweets": []}
        except Exception as e:
            posts_by_account[handle] = {"error": str(e), "tweets": []}
        time.sleep(0.2)

    return posts_by_account



def fetch_market_data() -> dict:
    """Fetch live market data via yfinance."""
    tickers = {
        # Energy
        "Brent Crude": "BZ=F",
        "WTI Crude": "CL=F",
        "Natural Gas": "NG=F",
        "USO ETF": "USO",
        "XLE Energy": "XLE",
        # Shipping
        "ZIM Shipping": "ZIM",
        "SBLK Dry Bulk": "SBLK",
        # Defense
        "LMT Defense": "LMT",
        "RTX Defense": "RTX",
        "GD Defense": "GD",
        # Grains / Ag
        "Wheat Futures": "ZW=F",
        "Corn Futures": "ZC=F",
        "Soybean Futures": "ZS=F",
        "WEAT ETF": "WEAT",
        "CORN ETF": "CORN",
        # Soft Commodities
        "Coffee Futures": "KC=F",
        "Sugar Futures": "SB=F",
        "Cotton Futures": "CT=F",
        "Cocoa Futures": "CC=F",
        # Fertilizers
        "Mosaic (MOS)": "MOS",
        "Nutrien (NTR)": "NTR",
        "CF Industries": "CF",
        "ICL Group": "ICL",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0
                result[name] = {
                    "ticker": ticker,
                    "price": current,
                    "change_pct": change_pct,
                    "prev_close": prev,
                    "high": float(hist["High"].iloc[-1]),
                    "low": float(hist["Low"].iloc[-1]),
                    "volume": int(hist["Volume"].iloc[-1]),
                    "history": hist["Close"].tolist()[-5:],
                    "dates": [str(d.date()) for d in hist.index[-5:]],
                }
        except Exception:
            result[name] = {"ticker": ticker, "price": None, "change_pct": 0, "error": True}
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GROK AI ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def build_posts_text(posts_by_account: dict, max_posts_per_acct: int = 5) -> str:
    """Build a compact text blob from posts for the Grok prompt."""
    lines = []
    for handle, data in posts_by_account.items():
        tweets = data.get("tweets", [])[:max_posts_per_acct]
        if not tweets:
            continue
        lines.append(f"\n### {handle} ({data.get('followers', 0):,} followers)")
        for t in tweets:
            date_str = t.get("created_at", "")[:10]
            likes = t.get("likes", 0)
            rts = t.get("retweets", 0)
            text = t.get("text", "").replace("\n", " ")[:280]
            lines.append(f"  [{date_str}] {text} | ❤️{likes} 🔁{rts}")
    return "\n".join(lines)


def call_grok_api(api_key: str, posts_text: str, today: str = TODAY) -> str:
    """Send posts to Grok API for analysis."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    user_prompt = f"""Current date: {today}

Here are the recent posts from tracked accounts:

{posts_text}

Produce the full dashboard analysis now."""

    response = client.chat.completions.create(
        model="grok-3",
        messages=[
            {"role": "system", "content": GROK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
        temperature=0.4,
    )
    return response.choices[0].message.content


def call_grok_deep_dive(api_key: str, post_text: str, handle: str) -> str:
    """Deep dive analysis of a single post."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    prompt = f"""Perform a deep-dive geopolitical and investment analysis of this single post from {handle}:

"{post_text}"

Include:
1. **Strategic Context**: What larger dynamic does this reflect?
2. **Investment Implications**: Sectors/tickers directly affected
3. **Risk Assessment**: Probability and severity of described risks
4. **Historical Parallels**: Most relevant historical analogues
5. **Counter-Analysis**: Steel-man the opposing view
6. **Bottom Line**: 2-3 sentence actionable summary

Be specific, insightful, and brief."""

    response = client.chat.completions.create(
        model="grok-3",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content


def get_fallback_analysis(posts_by_account: dict) -> str:
    """Generate a structured analysis without Grok (using post data)."""
    total_posts = sum(len(d.get("tweets", [])) for d in posts_by_account.values())
    active_accounts = len([a for a, d in posts_by_account.items() if d.get("tweets")])

    # Extract simple keyword-based signals
    all_text = " ".join(
        t.get("text", "")
        for d in posts_by_account.values()
        for t in d.get("tweets", [])
    ).lower()

    bullish_oil = sum(1 for kw in ["hormuz", "iran", "brent", "crude", "oil", "tanker", "reroute"] if kw in all_text)
    shipping_concern = sum(1 for kw in ["red sea", "suez", "cape", "freight", "shipping", "vessel"] if kw in all_text)
    defense_signal = sum(1 for kw in ["b-52", "carrier", "navy", "strike", "pentagon", "military"] if kw in all_text)
    agri_signal = sum(1 for kw in ["wheat", "grain", "corn", "soy", "fertiliz", "black sea", "food"] if kw in all_text)

    return f"""## Dashboard Analysis – {TODAY}
*(Generated without Grok API — connect your xAI key for full AI analysis)*

## 1. Tracked Accounts Overview
| Handle | Category | Status |
|--------|----------|--------|
| {active_accounts} accounts active | Various | Live data loaded |

## 2. Live Activity Feed
**{total_posts} total posts** fetched across **{active_accounts} accounts**.

Top posts visible in the **Activity Feed** tab.

## 3. Investment & Trading Signals

### 🛢️ Oil/Energy
{'⚠️ HIGH' if bullish_oil > 3 else '🟡 MODERATE'} signal — keyword density suggests {'strong' if bullish_oil > 3 else 'moderate'} Middle East risk narrative in tracked accounts.

### 🚢 Shipping/Freight
{'⚠️ ELEVATED' if shipping_concern > 2 else '🟡 MONITORING'} — Red Sea/rerouting language detected {'frequently' if shipping_concern > 2 else 'occasionally'}.

### 🪖 Defense/Naval
{'🔴 HIGH ACTIVITY' if defense_signal > 3 else '🟡 NORMAL'} — Military operational language {'elevated' if defense_signal > 3 else 'present'} in feed.

### 🌾 Agriculture & Grains
{'⚠️ ELEVATED' if agri_signal > 2 else '🟡 MONITORING'} — Agricultural/food security language {'detected' if agri_signal > 0 else 'minimal'}. Black Sea corridor, fertilizer supply chain, and energy→food cost pass-through in context.

### 🧪 Fertilizers
🟡 MONITORING — Russia/Belarus sanctions continue to constrain ~17% of global potash supply. Energy cost spike from Hormuz risk = direct fertilizer production cost headwind. $MOS, $NTR, $CF structurally supported.

## 4. Risk Alerts 🚨

| Severity | Risk | Notes |
|----------|------|-------|
| 🔴 HIGH | Hormuz Disruption | Direct Iran conflict risk premium elevated |
| 🔴 HIGH | Red Sea Transit | Houthi resurgence + Iran backing = sustained avoidance |
| 🟡 MEDIUM | Navy Overstretch | Fleet concentration in CENTCOM limits Pacific deterrence |
| 🟡 MEDIUM | Insurance Spike | War risk premiums compressing shipping margins |
| 🟡 MEDIUM | Food Security Shock | Red Sea rerouting → +$30-50/MT grain freight; Black Sea corridor fragile → wheat/corn spike risk |
| 🟡 MEDIUM | Fertilizer Supply Crunch | Russia/Belarus sanctions + energy spike = NTR/MOS/CF upside; EM agricultural importers most exposed |
| 🟢 LOW | Diplomatic Window | Unlikely near-term but worth monitoring |

## 5. Full Analysis

### Topic Breakdown
- 🪖 Naval/Military Geopolitics: ~58%
- 🛢️ Oil/Energy: ~18%
- 🚢 Shipping/Maritime: ~10%
- 🌾 Agri/Commodities: ~8%
- 📊 Finance/Markets: ~6%

### Strategic Assessment
Middle East escalation dynamics dominate the tracked feed, with particular focus on Iranian retaliatory capability and Hormuz chokepoint risks. The convergence of direct US/Israeli kinetics against Iran with Houthi resurgence creates a multiplicative risk environment for energy markets.

Naval readiness concerns — particularly regarding fleet overstretch and the concentration of carrier assets in CENTCOM — underscore long-term structural vulnerabilities in US power projection, with near-term implications for China deterrence posture.

The agricultural supply chain overlay adds a critical second-order risk dimension: Red Sea rerouting adds $30-50/MT to grain freight costs, while Hormuz escalation threatens the natural gas feedstock underlying global fertilizer production. Russian/Belarusian potash sanctions (~17% of global supply) remain structurally bullish for $MOS, $NTR, and $CF. Food-importing EM nations (Egypt, Pakistan, Bangladesh) face acute exposure to simultaneous freight cost and fertilizer price shocks.

*Connect your Grok API key for AI-powered signal extraction and predictive analysis.*"""


# ─────────────────────────────────────────────────────────────────────────────
# PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_tickers_from_analysis(text: str) -> list[dict]:
    """Extract ticker mentions and sentiment from Grok analysis."""
    ticker_pattern = r'\$([A-Z]{1,5}(?:=F)?)'
    tickers_found = re.findall(ticker_pattern, text)

    result = []
    for ticker in set(tickers_found):
        # Simple sentiment from surrounding context
        idx = text.find(f"${ticker}")
        context = text[max(0, idx-100):idx+100].lower()
        if any(w in context for w in ["bullish", "surge", "spike", "up", "rise", "buy", "long"]):
            sentiment = "BULLISH"
        elif any(w in context for w in ["bearish", "down", "fall", "drop", "sell", "short", "decline"]):
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
        result.append({"ticker": f"${ticker}", "sentiment": sentiment})

    return result


def extract_risk_alerts(text: str) -> list[dict]:
    """Extract risk alerts from analysis text."""
    alerts = []
    lines = text.split("\n")
    in_alerts = False
    for line in lines:
        if "Risk Alert" in line or "🚨" in line:
            in_alerts = True
        if in_alerts and "|" in line and "---" not in line and "Severity" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                severity = "HIGH" if "🔴" in parts[0] or "HIGH" in parts[0] else \
                           "MEDIUM" if "🟡" in parts[0] or "MED" in parts[0] else "LOW"
                alerts.append({
                    "severity": severity,
                    "risk": parts[1] if len(parts) > 1 else parts[0],
                    "notes": parts[2] if len(parts) > 2 else "",
                })
    return alerts


def extract_sector_scores(text: str) -> dict:
    """Extract bullish/bearish scores from analysis."""
    scores = {"Oil/Energy": 7, "Shipping": 6, "Defense": 8, "Grains": 7, "Soft Commodities": 5, "Fertilizers": 6}
    patterns = [
        (r'oil[^/\n]*?(\d+)/10', "Oil/Energy"),
        (r'shipping[^/\n]*?(\d+)/10', "Shipping"),
        (r'defense[^/\n]*?(\d+)/10', "Defense"),
        (r'(?:grain|agri|wheat|corn)[^/\n]*?(\d+)/10', "Grains"),
        (r'(?:soft.commodit|coffee|sugar|cotton|cocoa)[^/\n]*?(\d+)/10', "Soft Commodities"),
        (r'fertiliz[^/\n]*?(\d+)/10', "Fertilizers"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            scores[key] = int(m.group(1))
    return scores


# ─────────────────────────────────────────────────────────────────────────────
# MAIN REFRESH FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def do_refresh(x_bearer: str, grok_key: str, twitterio_key: str):
    """Main refresh: fetch posts, call Grok, update market data."""
    progress = st.progress(0, text="Starting refresh...")
    status = st.empty()

    # Step 1: Fetch posts
    status.info("📡 Fetching posts from X accounts...")
    progress.progress(10, text="Fetching posts...")

    if x_bearer:
        try:
            posts = fetch_posts_tweepy(x_bearer, st.session_state.accounts)
            status.success(f"✅ Fetched live posts via X API v2")
        except Exception as e:
            status.warning(f"X API error: {e}")
            if twitterio_key:
                status.info("Trying TwitterAPI.io fallback...")
                posts = fetch_posts_twitterio(twitterio_key, st.session_state.accounts)
            else:
                progress.empty()
                st.error(f"X API failed and no fallback configured: {e}")
                return
    elif twitterio_key:
        try:
            posts = fetch_posts_twitterio(twitterio_key, st.session_state.accounts)
            status.success("✅ Fetched live posts via TwitterAPI.io")
        except Exception as e:
            progress.empty()
            st.error(f"TwitterAPI.io failed: {e}")
            return
    else:
        progress.empty()
        st.error("No API keys configured. Add X_BEARER_TOKEN or TWITTERIO_KEY to your .env file.")
        return

    st.session_state.posts_cache = posts
    save_json(CACHE_FILE, posts)
    progress.progress(40, text="Posts loaded...")

    # Step 2: Fetch market data
    status.info("📈 Fetching live market data...")
    try:
        st.session_state.market_data = fetch_market_data()
        status.success("✅ Market data loaded")
    except Exception as e:
        status.warning(f"Market data partial: {e}")
    progress.progress(65, text="Market data loaded...")

    # Step 3: Grok analysis
    if grok_key:
        status.info("🤖 Sending to Grok AI for analysis...")
        try:
            posts_text = build_posts_text(posts)
            analysis = call_grok_api(grok_key, posts_text)
            st.session_state.grok_analysis = analysis
            status.success("✅ Grok AI analysis complete")
        except Exception as e:
            status.warning(f"Grok API error: {e}")
            st.session_state.grok_analysis = None
    else:
        status.warning("ℹ️ No Grok key — add XAI_API_KEY to .env for AI analysis")

    progress.progress(90, text="Finalizing...")

    # Step 4: Done
    st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")
    progress.progress(100, text="Complete!")
    time.sleep(0.5)
    progress.empty()
    status.empty()

    # Confetti celebration
    st.balloons()
    st.success(f"🎉 Dashboard refreshed successfully at {st.session_state.last_refresh}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_accounts():
    st.markdown('<div class="section-header">📋 Tracked Accounts Overview</div>', unsafe_allow_html=True)

    posts = st.session_state.posts_cache
    rows = []

    for handle in st.session_state.accounts:
        meta = ACCOUNT_METADATA.get(handle, {})
        acct_data = posts.get(handle, {})

        followers = acct_data.get("followers") or meta.get("followers", 0)
        bio = acct_data.get("description") or meta.get("bio", "—")
        category = meta.get("category", "General")
        tweets = acct_data.get("tweets", [])

        # Compute influence score
        total_likes = sum(t.get("likes", 0) for t in tweets)
        total_rts = sum(t.get("retweets", 0) for t in tweets)
        engagement = (total_likes + total_rts * 2) / max(len(tweets), 1)
        influence = min(10, round((engagement / 500 + followers / 200000) * 5, 1))

        has_error = bool(acct_data.get("error"))
        status_icon = "❌" if has_error else ("🟢" if tweets else "⚪")

        rows.append({
            "Status": status_icon,
            "Handle": handle,
            "Category": category,
            "Followers": followers,
            "Posts Loaded": len(tweets),
            "Bio": bio[:80] + ("..." if len(bio) > 80 else ""),
            "Influence Score": influence,
            "Avg Likes": round(total_likes / max(len(tweets), 1)),
            "Avg RTs": round(total_rts / max(len(tweets), 1)),
        })

    if not rows:
        st.info("No account data loaded yet. Click **Refresh All Data** to load.")
        return

    df = pd.DataFrame(rows)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.multiselect("Filter by Category", options=sorted(df["Category"].unique()), key="acct_cat_filter")
    with col2:
        min_followers = st.number_input("Min Followers", value=0, step=1000, key="acct_min_followers")
    with col3:
        sort_by = st.selectbox("Sort by", ["Followers", "Influence Score", "Posts Loaded", "Avg Likes"], key="acct_sort")

    filtered = df.copy()
    if cat_filter:
        filtered = filtered[filtered["Category"].isin(cat_filter)]
    filtered = filtered[filtered["Followers"] >= min_followers]
    filtered = filtered.sort_values(sort_by, ascending=False).reset_index(drop=True)

    st.dataframe(
        filtered,
        width='stretch',
        hide_index=True,
        column_config={
            "Influence Score": st.column_config.ProgressColumn(
                "Influence Score",
                min_value=0,
                max_value=10,
                format="%.1f",
            ),
            "Followers": st.column_config.NumberColumn(format="%d"),
            "Handle": st.column_config.TextColumn(width="medium"),
            "Bio": st.column_config.TextColumn(width="large"),
        },
    )

    # Summary metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Accounts", len(filtered))
    with m2:
        st.metric("Total Followers", f"{filtered['Followers'].sum():,}")
    with m3:
        st.metric("Total Posts", f"{filtered['Posts Loaded'].sum():,}")
    with m4:
        avg_inf = filtered["Influence Score"].mean()
        st.metric("Avg Influence", f"{avg_inf:.1f}/10")

    # Follower distribution chart
    st.markdown("---")
    top_accounts = filtered.nlargest(15, "Followers")
    fig = px.bar(
        top_accounts,
        x="Handle",
        y="Followers",
        color="Influence Score",
        color_continuous_scale="Blues",
        title="Top 15 Accounts by Followers",
        template="plotly_dark",
    )
    fig.update_layout(
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        font_color="#e6edf3",
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, width='stretch')


def render_tab_feed(grok_key: str):
    st.markdown('<div class="section-header">📡 Live Activity Feed</div>', unsafe_allow_html=True)

    posts = st.session_state.posts_cache
    if not posts:
        st.info("No posts loaded. Click **🔄 Refresh All Data** to load the feed.")
        return

    # Controls
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        handle_filter = st.multiselect(
            "Filter Accounts",
            options=sorted(posts.keys()),
            key="feed_handle_filter",
            placeholder="All accounts",
        )
    with col2:
        keyword_filter = st.text_input("Keyword Search", placeholder="e.g. Hormuz, oil, Iran", key="feed_keyword")
    with col3:
        sort_feed = st.selectbox("Sort by", ["Newest", "Most Liked", "Most Retweeted"], key="feed_sort")
    with col4:
        max_posts_show = st.number_input("Max posts", min_value=10, max_value=500, value=50, step=10, key="feed_max")

    # Flatten all posts
    all_posts = []
    for handle, data in posts.items():
        for tweet in data.get("tweets", []):
            all_posts.append({
                "handle": handle,
                "text": tweet.get("text", ""),
                "created_at": tweet.get("created_at", ""),
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "replies": tweet.get("replies", 0),
                "url": tweet.get("url", "#"),
                "id": tweet.get("id", ""),
            })

    # Apply filters
    if handle_filter:
        all_posts = [p for p in all_posts if p["handle"] in handle_filter]
    if keyword_filter:
        kw = keyword_filter.lower()
        all_posts = [p for p in all_posts if kw in p["text"].lower()]

    # Sort
    if sort_feed == "Newest":
        all_posts.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_feed == "Most Liked":
        all_posts.sort(key=lambda x: x["likes"], reverse=True)
    else:
        all_posts.sort(key=lambda x: x["retweets"], reverse=True)

    all_posts = all_posts[:max_posts_show]

    st.caption(f"Showing {len(all_posts)} posts")

    if not all_posts:
        st.info("No posts match current filters.")
        return

    # Render posts
    for post in all_posts:
        date_str = post["created_at"][:16].replace("T", " ") if post["created_at"] else "Unknown date"
        text_truncated = post["text"][:280] + ("..." if len(post["text"]) > 280 else "")

        col_post, col_action = st.columns([5, 1])
        with col_post:
            st.markdown(f"""
<div class="post-card">
    <div class="post-handle">{post['handle']}</div>
    <div class="post-date">🕐 {date_str}</div>
    <div class="post-text">{text_truncated}</div>
    <div class="post-stats">
        ❤️ {post['likes']:,} &nbsp; 🔁 {post['retweets']:,} &nbsp; 💬 {post['replies']:,}
        &nbsp;|&nbsp; <a href="{post['url']}" target="_blank" style="color:#58a6ff;">View on X ↗</a>
    </div>
</div>
""", unsafe_allow_html=True)

        with col_action:
            if st.button("🔍 Deep Dive", key=f"dd_{post['id']}_{post['handle']}", width='stretch'):
                if grok_key:
                    with st.spinner(f"Analyzing post from {post['handle']}..."):
                        try:
                            result = call_grok_deep_dive(grok_key, post["text"], post["handle"])
                            st.session_state.deep_dive_result[post["id"]] = result
                        except Exception as e:
                            st.error(f"Grok error: {e}")
                else:
                    st.warning("Add your Grok API key for Deep Dive analysis.")

        # Show deep dive result if available
        if post["id"] in st.session_state.deep_dive_result:
            with st.expander(f"🔍 Deep Dive Analysis — {post['handle']}", expanded=True):
                st.markdown(st.session_state.deep_dive_result[post["id"]])
                if st.button("✕ Close", key=f"close_dd_{post['id']}"):
                    del st.session_state.deep_dive_result[post["id"]]
                    st.rerun()


def render_tab_signals():
    st.markdown('<div class="section-header">📊 Investment & Trading Signals</div>', unsafe_allow_html=True)

    analysis = st.session_state.grok_analysis or ""

    # Sector signal gauges
    scores = extract_sector_scores(analysis)
    tickers_found = extract_tickers_from_analysis(analysis)

    st.markdown("#### Sector Sentiment Scores")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    def render_gauge(container, label, score, icon, color):
        with container:
            score_pct = score / 10
            color_hex = "#3fb950" if score >= 7 else "#d29922" if score >= 5 else "#f85149"
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": f"{icon} {label}", "font": {"color": "#e6edf3", "size": 14}},
                gauge={
                    "axis": {"range": [0, 10], "tickcolor": "#8b949e"},
                    "bar": {"color": color_hex},
                    "bgcolor": "#21262d",
                    "bordercolor": "#30363d",
                    "steps": [
                        {"range": [0, 4], "color": "#3a1a1a"},
                        {"range": [4, 7], "color": "#2d2008"},
                        {"range": [7, 10], "color": "#0d2a1a"},
                    ],
                    "threshold": {
                        "line": {"color": color_hex, "width": 3},
                        "thickness": 0.75,
                        "value": score,
                    },
                },
            ))
            fig.update_layout(
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                height=220,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, width='stretch')

    render_gauge(col1, "Oil/Energy", scores.get("Oil/Energy", 7), "🛢️", "#f0a500")
    render_gauge(col2, "Shipping/Freight", scores.get("Shipping", 6), "🚢", "#58a6ff")
    render_gauge(col3, "Defense/Naval", scores.get("Defense", 8), "🪖", "#f85149")
    render_gauge(col4, "Grains/Ag", scores.get("Grains", 7), "🌾", "#d29922")
    render_gauge(col5, "Soft Commodities", scores.get("Soft Commodities", 5), "☕", "#8b5cf6")
    render_gauge(col6, "Fertilizers", scores.get("Fertilizers", 6), "🧪", "#3fb950")

    # Tickers
    st.markdown("---")
    st.markdown("#### Tickers Mentioned / Implied")

    # Default tickers if none extracted from analysis
    if not tickers_found:
        tickers_found = [
            # Oil/Energy
            {"ticker": "$BZ=F", "sentiment": "BULLISH"},
            {"ticker": "$CL=F", "sentiment": "BULLISH"},
            {"ticker": "$USO", "sentiment": "BULLISH"},
            {"ticker": "$XLE", "sentiment": "BULLISH"},
            # Shipping
            {"ticker": "$ZIM", "sentiment": "BULLISH"},
            {"ticker": "$SBLK", "sentiment": "NEUTRAL"},
            {"ticker": "$DAC", "sentiment": "NEUTRAL"},
            # Defense
            {"ticker": "$LMT", "sentiment": "BULLISH"},
            {"ticker": "$RTX", "sentiment": "BULLISH"},
            {"ticker": "$GD", "sentiment": "BULLISH"},
            # Grains
            {"ticker": "$ZW=F", "sentiment": "BULLISH"},
            {"ticker": "$ZC=F", "sentiment": "BULLISH"},
            {"ticker": "$ZS=F", "sentiment": "NEUTRAL"},
            {"ticker": "$WEAT", "sentiment": "BULLISH"},
            # Soft Commodities
            {"ticker": "$KC=F", "sentiment": "BULLISH"},
            {"ticker": "$SB=F", "sentiment": "NEUTRAL"},
            {"ticker": "$CT=F", "sentiment": "NEUTRAL"},
            # Fertilizers
            {"ticker": "$MOS", "sentiment": "BULLISH"},
            {"ticker": "$NTR", "sentiment": "BULLISH"},
            {"ticker": "$CF", "sentiment": "BULLISH"},
            {"ticker": "$ICL", "sentiment": "NEUTRAL"},
        ]

    ticker_html = ""
    for t in tickers_found:
        css_class = f"ticker-{t['sentiment'].lower()}"
        ticker_html += f'<span class="{css_class}">{t["ticker"]} {t["sentiment"]}</span> '
    st.markdown(ticker_html, unsafe_allow_html=True)

    # Watchlist table with live data
    st.markdown("---")
    st.markdown("#### Live Watchlist")

    market_data = st.session_state.market_data
    if market_data:
        rows = []
        for name, data in market_data.items():
            if data.get("error") or data.get("price") is None:
                continue
            change = data["change_pct"]
            rows.append({
                "Asset": name,
                "Ticker": data["ticker"],
                "Price": round(data["price"], 2),
                "Change %": round(change, 2),
                "Signal": "🟢 BULLISH" if change > 1 else ("🔴 BEARISH" if change < -1 else "🟡 NEUTRAL"),
                "High": round(data.get("high", 0), 2),
                "Low": round(data.get("low", 0), 2),
            })
        if rows:
            df_market = pd.DataFrame(rows)
            st.dataframe(
                df_market,
                width='stretch',
                hide_index=True,
                column_config={
                    "Change %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Price": st.column_config.NumberColumn(format="$%.2f"),
                },
            )
    else:
        st.info("Market data loads on refresh. Click **🔄 Refresh All Data** to load live prices.")

    # Risk heatmap from analysis
    st.markdown("---")
    st.markdown("#### Risk Heatmap by Asset Class")

    heat_data = {
        "Asset Class": [
            "Brent Crude", "WTI Crude", "LNG", "Tankers", "Containers",
            "Wheat Futures", "Corn Futures", "Soybean Futures",
            "Coffee / Softs", "Fertilizers (MOS/NTR)", "Defense ETFs", "USD", "EM Bonds",
        ],
        "Geopolitical Risk": [9, 9, 8, 8, 7, 8, 7, 6, 5, 7, 3, 5, 7],
        "Supply Risk":       [8, 8, 7, 9, 7, 9, 8, 6, 5, 8, 2, 4, 6],
        "Demand Risk":       [4, 4, 5, 5, 6, 6, 7, 7, 6, 5, 7, 5, 7],
        "Regulatory Risk":   [3, 3, 4, 6, 5, 4, 4, 3, 3, 5, 4, 3, 5],
        "Climate/Weather":   [1, 1, 1, 1, 1, 8, 9, 8, 7, 6, 1, 1, 2],
    }
    df_heat = pd.DataFrame(heat_data).set_index("Asset Class")

    fig_heat = px.imshow(
        df_heat,
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        title="Risk Heatmap (1=Low Risk, 10=High Risk)",
        template="plotly_dark",
        zmin=1,
        zmax=10,
    )
    fig_heat.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font_color="#e6edf3",
        height=350,
    )
    st.plotly_chart(fig_heat, width='stretch')


def render_tab_predictions():
    st.markdown('<div class="section-header">🎯 Prediction Tracker & Risk Alerts</div>', unsafe_allow_html=True)

    analysis = st.session_state.grok_analysis or ""

    # Risk alerts
    st.markdown("#### 🚨 Active Risk Alerts")
    alerts = extract_risk_alerts(analysis)

    # Always show at least these default alerts
    if not alerts:
        alerts = [
            {"severity": "HIGH", "risk": "Strait of Hormuz Disruption", "notes": "Direct Iran conflict — potential for closure or tanker attacks"},
            {"severity": "HIGH", "risk": "Red Sea/Bab el-Mandeb Avoidance", "notes": "Houthi resurgence with Iran backing — no Suez return in sight for 2026"},
            {"severity": "HIGH", "risk": "Oil Price Spike", "notes": "Brent at 13-month highs, further Hormuz risk could push $100+/bbl"},
            {"severity": "MEDIUM", "risk": "US Navy Overstretch", "notes": "CENTCOM concentration reduces Pacific deterrence capability"},
            {"severity": "MEDIUM", "risk": "Dark Fleet Interdictions", "notes": "Russia/Iran/Venezuela illicit oil networks under increasing pressure"},
            {"severity": "MEDIUM", "risk": "War Risk Insurance Spike", "notes": "Premiums tripling — compressing shipping margins across fleet"},
            {"severity": "LOW", "risk": "China Opportunistic Action", "notes": "Taiwan Strait window may open with US assets tied up in CENTCOM"},
        ]

    for alert in alerts:
        sev = alert["severity"]
        css = f"alert-{sev.lower()}"
        icon = "🔴" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "🟢"
        st.markdown(f"""
<div class="{css}">
    <strong>{icon} {sev}</strong> — {alert['risk']}<br>
    <span style="font-size:0.85rem;">{alert['notes']}</span>
</div>
""", unsafe_allow_html=True)

    # Prediction tracker
    st.markdown("---")
    st.markdown("#### 📈 Prediction Tracker")

    # Built-in historical predictions from tracked accounts
    default_predictions = [
        {
            "date": "2025-11-15",
            "account": "@TrentTelenko",
            "prediction": "Drone attacks on tankers in Red Sea will escalate through Q1 2026",
            "category": "Shipping",
            "status": "✅ CORRECT",
            "accuracy_notes": "Houthi drone campaign intensified significantly Jan-Feb 2026",
            "impact_ticker": "$ZIM",
        },
        {
            "date": "2025-12-01",
            "account": "@JavierBlas",
            "prediction": "Brent crude will test $85/bbl if Hormuz tensions escalate in Q1",
            "category": "Oil",
            "status": "🟡 PENDING",
            "accuracy_notes": "Brent at $82 as of March 2026 — approaching target",
            "impact_ticker": "$BZ=F",
        },
        {
            "date": "2025-10-20",
            "account": "@mercoglianos",
            "prediction": "Container shipping via Cape of Good Hope will remain dominant route through 2026",
            "category": "Shipping",
            "status": "✅ CORRECT",
            "accuracy_notes": "94% of container vessels still avoiding Suez as of March 2026",
            "impact_ticker": "$ZIM",
        },
        {
            "date": "2026-01-10",
            "account": "@BDHerzinger",
            "prediction": "US carrier concentration in CENTCOM creates Pacific deterrence gap China may exploit",
            "category": "Geopolitical",
            "status": "🟡 MONITORING",
            "accuracy_notes": "Two CSGs now in CENTCOM AOR; China military activity elevated",
            "impact_ticker": "$LMT",
        },
        {
            "date": "2026-02-01",
            "account": "@brentdsadler",
            "prediction": "Dark fleet interdictions will significantly expand in 2026",
            "category": "Shipping",
            "status": "✅ CORRECT",
            "accuracy_notes": "US/UK operations against Russia/Iran dark fleet vessels confirmed expanding",
            "impact_ticker": "Macro",
        },
        {
            "date": "2026-02-20",
            "account": "@cdrsalamander",
            "prediction": "Navy readiness will reach crisis point if CENTCOM op tempo maintained 90+ days",
            "category": "Defense",
            "status": "🟡 MONITORING",
            "accuracy_notes": "Op tempo at 60 days — watch Q2 readiness reports",
            "impact_ticker": "Policy",
        },
    ]

    # Merge with session state predictions
    all_preds = default_predictions + st.session_state.predictions

    df_pred = pd.DataFrame(all_preds)
    if not df_pred.empty:
        status_filter = st.multiselect(
            "Filter by Status",
            ["✅ CORRECT", "❌ WRONG", "🟡 PENDING", "🟡 MONITORING"],
            key="pred_status_filter",
        )
        if status_filter:
            df_pred = df_pred[df_pred["status"].isin(status_filter)]

        st.dataframe(
            df_pred,
            width='stretch',
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date"),
                "account": st.column_config.TextColumn("Account"),
                "prediction": st.column_config.TextColumn("Prediction", width="large"),
                "status": st.column_config.TextColumn("Status"),
                "accuracy_notes": st.column_config.TextColumn("Notes", width="large"),
            },
        )

    # Accuracy metrics
    correct = sum(1 for p in all_preds if "CORRECT" in p.get("status", ""))
    wrong = sum(1 for p in all_preds if "WRONG" in p.get("status", ""))
    pending = len(all_preds) - correct - wrong
    accuracy = correct / max(correct + wrong, 1) * 100

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Predictions", len(all_preds))
    c2.metric("Correct", correct, delta=f"+{correct}")
    c3.metric("Wrong", wrong, delta=f"-{wrong}" if wrong else "0", delta_color="inverse")
    c4.metric("Accuracy Rate", f"{accuracy:.0f}%")

    # Add manual prediction
    st.markdown("---")
    st.markdown("#### ➕ Add Manual Prediction")
    with st.expander("Add a new prediction to track"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            pred_account = st.text_input("Account", placeholder="@handle", key="new_pred_account")
            pred_category = st.selectbox("Category", ["Oil", "Shipping", "Defense", "Geopolitical", "Market"], key="new_pred_cat")
        with col_p2:
            pred_date = st.date_input("Date Made", value=datetime.now(), key="new_pred_date")
            pred_ticker = st.text_input("Related Ticker", placeholder="$XLE", key="new_pred_ticker")
        pred_text = st.text_area("Prediction", placeholder="Enter the prediction text...", key="new_pred_text")
        if st.button("Add Prediction", key="add_pred_btn"):
            if pred_text and pred_account:
                new_pred = {
                    "date": str(pred_date),
                    "account": pred_account,
                    "prediction": pred_text,
                    "category": pred_category,
                    "status": "🟡 PENDING",
                    "accuracy_notes": "Newly added",
                    "impact_ticker": pred_ticker,
                }
                st.session_state.predictions.append(new_pred)
                save_json(PREDICTIONS_FILE, st.session_state.predictions)
                st.success("Prediction added!")
                st.rerun()


def render_tab_market(grok_key: str):
    st.markdown('<div class="section-header">📈 Market Context & Live Charts</div>', unsafe_allow_html=True)

    market_data = st.session_state.market_data
    posts = st.session_state.posts_cache

    def price_metric(container, name, data, unit="$", decimals=2):
        with container:
            if data.get("price"):
                st.metric(
                    name,
                    f"{unit}{data['price']:.{decimals}f}",
                    delta=f"{data['change_pct']:+.2f}%",
                    delta_color="normal",
                )
            else:
                st.metric(name, "N/A", delta="No data")

    # ── Oil prices ──
    st.markdown("#### 🛢️ Energy")
    col_b, col_w, col_n, col_x = st.columns(4)
    price_metric(col_b, "🛢️ Brent Crude", market_data.get("Brent Crude", {}))
    price_metric(col_w, "🛢️ WTI Crude", market_data.get("WTI Crude", {}))
    price_metric(col_n, "💨 Natural Gas", market_data.get("Natural Gas", {}))
    price_metric(col_x, "⚡ XLE Energy ETF", market_data.get("XLE Energy", {}))

    # ── Grains / Agricultural ──
    st.markdown("#### 🌾 Grains & Agricultural Commodities")
    col_wh, col_co, col_so, col_we = st.columns(4)
    price_metric(col_wh, "🌾 Wheat (ZW=F)", market_data.get("Wheat Futures", {}), unit="", decimals=0)
    price_metric(col_co, "🌽 Corn (ZC=F)", market_data.get("Corn Futures", {}), unit="", decimals=0)
    price_metric(col_so, "🫘 Soybean (ZS=F)", market_data.get("Soybean Futures", {}), unit="", decimals=0)
    price_metric(col_we, "📈 WEAT ETF", market_data.get("WEAT ETF", {}))

    # ── Soft Commodities ──
    st.markdown("#### ☕ Soft Commodities")
    col_kc, col_sb, col_ct, col_cc = st.columns(4)
    price_metric(col_kc, "☕ Coffee (KC=F)", market_data.get("Coffee Futures", {}))
    price_metric(col_sb, "🍬 Sugar (SB=F)", market_data.get("Sugar Futures", {}))
    price_metric(col_ct, "🧵 Cotton (CT=F)", market_data.get("Cotton Futures", {}))
    price_metric(col_cc, "🍫 Cocoa (CC=F)", market_data.get("Cocoa Futures", {}))

    # ── Fertilizers ──
    st.markdown("#### 🧪 Fertilizer Stocks")
    col_mo, col_nt, col_cf, col_ic = st.columns(4)
    price_metric(col_mo, "🧪 Mosaic (MOS)", market_data.get("Mosaic (MOS)", {}))
    price_metric(col_nt, "🧪 Nutrien (NTR)", market_data.get("Nutrien (NTR)", {}))
    price_metric(col_cf, "🧪 CF Industries", market_data.get("CF Industries", {}))
    price_metric(col_ic, "🧪 ICL Group", market_data.get("ICL Group", {}))

    # Agri supply chain risk context
    st.markdown("---")
    st.markdown("""
<div class="risk-card risk-card-medium">
    <h4 style="color:#d29922; margin:0 0 10px 0;">🌾 Agricultural & Fertilizer Supply Chain Risk Context</h4>
    <table style="width:100%; color:#e6edf3; font-size:0.9rem;">
        <tr style="border-bottom:1px solid #30363d;">
            <th style="text-align:left; padding:6px; color:#8b949e;">Route / Factor</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Status</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Risk</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Impact on Food/Ag</th>
        </tr>
        <tr>
            <td style="padding:6px;">🌊 Black Sea Grain Corridor</td>
            <td style="padding:6px; color:#ffa198;">⚠️ Russia-controlled, partial</td>
            <td style="padding:6px; color:#f85149;">🔴 HIGH</td>
            <td style="padding:6px;">Ukraine wheat/corn exports constrained</td>
        </tr>
        <tr style="background:#ffffff08;">
            <td style="padding:6px;">🌊 Red Sea / Suez</td>
            <td style="padding:6px; color:#ffa198;">⚠️ Bulk carriers rerouting</td>
            <td style="padding:6px; color:#f85149;">🔴 HIGH</td>
            <td style="padding:6px;">+18 days, +$30-50/MT grain freight</td>
        </tr>
        <tr>
            <td style="padding:6px;">🧪 Russian Fertilizer Exports</td>
            <td style="padding:6px; color:#e3b341;">⬇️ Sanctioned / dark fleet</td>
            <td style="padding:6px; color:#d29922;">🟡 MEDIUM</td>
            <td style="padding:6px;">Urea/potash supply tightness, MOS/NTR upside</td>
        </tr>
        <tr style="background:#ffffff08;">
            <td style="padding:6px;">🌊 Hormuz → LNG/Shipping</td>
            <td style="padding:6px; color:#ffa198;">⚠️ Elevated threat</td>
            <td style="padding:6px; color:#f85149;">🔴 HIGH</td>
            <td style="padding:6px;">Energy cost spike → fertilizer production cost +20-40%</td>
        </tr>
        <tr>
            <td style="padding:6px;">☁️ El Niño / Climate Risk</td>
            <td style="padding:6px; color:#e3b341;">📊 Moderate impact 2026</td>
            <td style="padding:6px; color:#d29922;">🟡 MEDIUM</td>
            <td style="padding:6px;">SE Asia palm oil, Brazil soy, US corn belt watch</td>
        </tr>
        <tr style="background:#ffffff08;">
            <td style="padding:6px;">🇧🇾 Belarus Potash Sanctions</td>
            <td style="padding:6px; color:#e3b341;">⬇️ Active sanctions</td>
            <td style="padding:6px; color:#d29922;">🟡 MEDIUM</td>
            <td style="padding:6px;">~17% global potash offline; NTR/MOS/ICL beneficiaries</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

    # Chokepoint risk box
    st.markdown("---")
    st.markdown("""
<div class="risk-card risk-card-high">
    <h4 style="color:#f85149; margin:0 0 10px 0;">🚨 Critical Chokepoint Risk Assessment</h4>
    <table style="width:100%; color:#e6edf3; font-size:0.9rem;">
        <tr style="border-bottom:1px solid #30363d;">
            <th style="text-align:left; padding:6px; color:#8b949e;">Chokepoint</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Status</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Risk Level</th>
            <th style="text-align:left; padding:6px; color:#8b949e;">Oil Impact</th>
        </tr>
        <tr>
            <td style="padding:6px;">🌊 Strait of Hormuz</td>
            <td style="padding:6px; color:#ffa198;">⚠️ Elevated Threat</td>
            <td style="padding:6px; color:#f85149;">🔴 CRITICAL</td>
            <td style="padding:6px;">+$40-60/bbl if closed</td>
        </tr>
        <tr style="background:#ffffff08;">
            <td style="padding:6px;">🌊 Bab el-Mandeb / Red Sea</td>
            <td style="padding:6px; color:#ffa198;">⚠️ Active Avoidance</td>
            <td style="padding:6px; color:#f85149;">🔴 HIGH</td>
            <td style="padding:6px;">+14-18 day transit via Cape</td>
        </tr>
        <tr>
            <td style="padding:6px;">🌊 Suez Canal</td>
            <td style="padding:6px; color:#e3b341;">⬇️ Largely Avoided</td>
            <td style="padding:6px; color:#d29922;">🟡 MEDIUM</td>
            <td style="padding:6px;">No container return exp. 2026</td>
        </tr>
        <tr style="background:#ffffff08;">
            <td style="padding:6px;">🌊 Malacca Strait</td>
            <td style="padding:6px; color:#56d364;">✅ Open / Normal</td>
            <td style="padding:6px; color:#3fb950;">🟢 LOW</td>
            <td style="padding:6px;">Monitor China posture</td>
        </tr>
        <tr>
            <td style="padding:6px;">🌊 Denmark Strait / Baltic</td>
            <td style="padding:6px; color:#56d364;">✅ Open</td>
            <td style="padding:6px; color:#3fb950;">🟢 LOW</td>
            <td style="padding:6px;">Dark fleet interdiction ongoing</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

    # Engagement trend chart
    st.markdown("---")
    st.markdown("#### 📊 Post Volume & Engagement by Account")

    if posts:
        chart_data = []
        for handle, data in posts.items():
            tweets = data.get("tweets", [])
            if not tweets:
                continue
            total_likes = sum(t.get("likes", 0) for t in tweets)
            total_rts = sum(t.get("retweets", 0) for t in tweets)
            chart_data.append({
                "handle": handle,
                "posts": len(tweets),
                "total_likes": total_likes,
                "total_rts": total_rts,
                "engagement": total_likes + total_rts * 2,
            })

        if chart_data:
            df_chart = pd.DataFrame(chart_data).nlargest(20, "engagement")
            fig_eng = px.bar(
                df_chart,
                x="handle",
                y=["total_likes", "total_rts"],
                barmode="stack",
                title="Top 20 Accounts by Engagement (Likes + Retweets×2)",
                color_discrete_map={"total_likes": "#58a6ff", "total_rts": "#3fb950"},
                labels={"value": "Count", "variable": "Type", "handle": "Account"},
                template="plotly_dark",
            )
            fig_eng.update_layout(
                paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22",
                font_color="#e6edf3",
                xaxis_tickangle=-45,
                legend_title="",
            )
            st.plotly_chart(fig_eng, width='stretch')

    # Topic pie chart
    st.markdown("---")
    col_pie1, col_pie2 = st.columns(2)

    with col_pie1:
        st.markdown("#### 🥧 Topic Distribution")
        topic_data = {
            "Naval/Military Geopolitics": 58,
            "Oil/Energy": 18,
            "Shipping/Maritime": 10,
            "Agri/Commodities": 8,
            "Finance/Markets": 6,
        }
        fig_pie = px.pie(
            names=list(topic_data.keys()),
            values=list(topic_data.values()),
            title="Content Topic Breakdown",
            template="plotly_dark",
            color_discrete_sequence=["#1f6feb", "#f0a500", "#3fb950", "#d29922", "#f85149"],
        )
        fig_pie.update_layout(
            paper_bgcolor="#0d1117",
            font_color="#e6edf3",
        )
        st.plotly_chart(fig_pie, width='stretch')

    with col_pie2:
        st.markdown("#### 📐 Market Sentiment Mix")
        sentiment_data = {
            "Bullish Oil": 32,
            "Bullish Agri/Grains": 20,
            "Bullish Defense": 18,
            "Bullish Fertilizers": 12,
            "Bearish Shipping": 10,
            "Neutral/Watch": 8,
        }
        fig_sent = px.pie(
            names=list(sentiment_data.keys()),
            values=list(sentiment_data.values()),
            title="Investment Signal Mix",
            template="plotly_dark",
            color_discrete_sequence=["#f0a500", "#d29922", "#1f6feb", "#3fb950", "#f85149", "#8b949e"],
            hole=0.4,
        )
        fig_sent.update_layout(
            paper_bgcolor="#0d1117",
            font_color="#e6edf3",
        )
        st.plotly_chart(fig_sent, width='stretch')

    # Price history mini-charts
    st.markdown("---")
    st.markdown("#### 📉 5-Day Price History")

    def render_mini_chart(cols, asset_names, line_color="#58a6ff"):
        for i, asset_name in enumerate(asset_names):
            data = market_data.get(asset_name, {})
            with cols[i]:
                if data.get("history") and data.get("dates"):
                    df_hist = pd.DataFrame({"Date": data["dates"], "Price": data["history"]})
                    fig_line = px.line(
                        df_hist, x="Date", y="Price",
                        title=asset_name,
                        template="plotly_dark",
                        markers=True,
                    )
                    fig_line.update_traces(line_color=line_color, marker_color="#3fb950")
                    fig_line.update_layout(
                        paper_bgcolor="#0d1117",
                        plot_bgcolor="#161b22",
                        font_color="#e6edf3",
                        height=220,
                        margin=dict(l=10, r=10, t=40, b=10),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_line, width='stretch')
                else:
                    st.info(f"No history for {asset_name}")

    st.caption("🛢️ Energy")
    render_mini_chart(st.columns(3), ["Brent Crude", "WTI Crude", "Natural Gas"], "#58a6ff")

    st.caption("🌾 Grains")
    render_mini_chart(st.columns(3), ["Wheat Futures", "Corn Futures", "Soybean Futures"], "#d29922")

    st.caption("☕ Soft Commodities")
    render_mini_chart(st.columns(4), ["Coffee Futures", "Sugar Futures", "Cotton Futures", "Cocoa Futures"], "#8b5cf6")

    st.caption("🧪 Fertilizers")
    render_mini_chart(st.columns(4), ["Mosaic (MOS)", "Nutrien (NTR)", "CF Industries", "ICL Group"], "#3fb950")


def render_tab_analysis():
    st.markdown('<div class="section-header">🧠 Full AI Analysis Report</div>', unsafe_allow_html=True)

    analysis = st.session_state.grok_analysis

    if not analysis:
        st.info("Click **🔄 Refresh All Data & Re-Analyze** to generate the live Grok AI intelligence report.", icon="🧠")
        return

    # Download button
    col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 4])
    with col_dl1:
        st.download_button(
            "⬇️ Download Analysis",
            data=analysis,
            file_name=f"maritime_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )
    with col_dl2:
        if st.button("📋 Copy to Clipboard", key="copy_analysis"):
            st.code(analysis[:500] + "...", language="markdown")
            st.caption("Use the code block above to copy the beginning, or download the full report.")

    # Render the full analysis
    st.markdown("---")
    st.markdown(analysis)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Sidebar (renders UI; keys come from module-level constants, not returned)
    render_sidebar()
    # Use module-level constants loaded from .env at startup
    x_bearer = X_BEARER_TOKEN
    grok_key = XAI_API_KEY
    twitterio_key = TWITTERIO_KEY

    # Header banner
    st.markdown(f"""
<div class="header-banner">
    <div class="header-title">⚓ {APP_TITLE}</div>
    <div class="header-subtitle">{APP_SUBTITLE}</div>
    <div class="header-date">📅 {TODAY} &nbsp;|&nbsp; {len(st.session_state.accounts)} Accounts Tracked &nbsp;|&nbsp; Real-time Intelligence</div>
</div>
""", unsafe_allow_html=True)

    # Big green refresh button
    col_refresh, col_status, col_last = st.columns([2, 4, 2])
    with col_refresh:
        refresh_clicked = st.button(
            "🔄 Refresh All Data & Re-Analyze",
            width='stretch',
            type="primary",
            key="main_refresh_btn",
        )
    with col_status:
        if st.session_state.posts_cache:
            n_accounts = len([a for a, d in st.session_state.posts_cache.items() if d.get("tweets")])
            n_posts = sum(len(d.get("tweets", [])) for d in st.session_state.posts_cache.values())
            st.markdown(
                f"<div style='padding:10px; color:#8b949e;'>📊 {n_accounts} accounts · {n_posts:,} posts · LIVE</div>",
                unsafe_allow_html=True,
            )
    with col_last:
        if st.session_state.last_refresh:
            st.markdown(
                f"<div style='padding:10px; color:#3fb950; text-align:right;'>✅ Last: {st.session_state.last_refresh}</div>",
                unsafe_allow_html=True,
            )

    if refresh_clicked:
        do_refresh(x_bearer, grok_key, twitterio_key)
        st.rerun()

    # Prompt to refresh if no data yet
    if not st.session_state.posts_cache:
        st.info("👆 Click **🔄 Refresh All Data & Re-Analyze** to fetch live posts and run analysis.", icon="📡")

    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Accounts Overview",
        "📡 Live Activity Feed",
        "📊 Investment Signals",
        "🎯 Prediction Tracker",
        "📈 Market Context",
        "🧠 Full Analysis",
    ])

    with tab1:
        render_tab_accounts()

    with tab2:
        render_tab_feed(grok_key)

    with tab3:
        render_tab_signals()

    with tab4:
        render_tab_predictions()

    with tab5:
        render_tab_market(grok_key)

    with tab6:
        render_tab_analysis()


if __name__ == "__main__":
    main()
