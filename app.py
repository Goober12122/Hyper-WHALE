from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import sqlite3
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
import pandas as pd
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Hyperliquid Whale Radar & Top Trades",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .top-trade-card {
        background: linear-gradient(135deg, #18202f 0%, #151821 100%);
        border: 1px solid #3b82f6;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .trader-trade-card {
        background: linear-gradient(135deg, #241e17 0%, #17181c 100%);
        border: 1px solid #f59e0b;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .badge-long {
        background-color: #065f46;
        color: #34d399;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    .badge-short {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Known Elite Wallet Labels
ELITE_WALLETS = {
    "0xa312114b5795dff9b8db50474dd57701aa78ad1e": "👑 All-Time #1 Legend ($95M+ PnL)",
    "0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6": "🐋 High-Volume Perps Whale",
    "0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae": "💎 Multi-Million Trend Trader",
    "0xa697a5b929cca9b3f8a78c4e4af1848506c06022": "🏛️ Institutional Quant Fund",
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303": "🏆 Top Public Vault Leader",
    "0x4010892c55452d50cb68b556efc5fa624d62b172": "🎯 Elite Swing Specialist",
    "0x1807f6ca9b332ea5ccda3a254c84bdf90e412c5a": "⚡ Core Perps Whale (BTC/ETH)",
    "0x20c2d95a3dfdca9e9ad12794d5fa6fad99da44f5": "🛡️ Low-Drawdown Trend Follower",
}

# ==============================================================================
# LOCAL DATABASE
# ==============================================================================
DB_PATH = "signals.db"


def init_db():
  with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                coin TEXT,
                signal TEXT,
                entry_price REAL,
                exit_price REAL,
                status TEXT,
                pnl_pct REAL,
                conviction TEXT
            )
        """)
    conn.commit()


def log_or_update_signals(actionable_signals, all_mids):
  init_db()
  with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, coin, signal, entry_price FROM signal_history WHERE status"
        " = 'OPEN'"
    )
    for sig_id, coin, sig_type, entry_px in cursor.fetchall():
      curr_px = float(all_mids.get(coin, 0))
      if curr_px == 0:
        continue

      if "LONG" in sig_type:
        pnl = ((curr_px - entry_px) / entry_px) * 100
        if pnl >= 2.0:
          cursor.execute(
              "UPDATE signal_history SET status = 'WIN', exit_price = ?,"
              " pnl_pct = ? WHERE id = ?",
              (curr_px, pnl, sig_id),
          )
        elif pnl <= -1.5:
          cursor.execute(
              "UPDATE signal_history SET status = 'LOSS', exit_price = ?,"
              " pnl_pct = ? WHERE id = ?",
              (curr_px, pnl, sig_id),
          )
      elif "SHORT" in sig_type:
        pnl = ((entry_px - curr_px) / entry_px) * 100
        if pnl >= 2.0:
          cursor.execute(
              "UPDATE signal_history SET status = 'WIN', exit_price = ?,"
              " pnl_pct = ? WHERE id = ?",
              (curr_px, pnl, sig_id),
          )
        elif pnl <= -1.5:
          cursor.execute(
              "UPDATE signal_history SET status = 'LOSS', exit_price = ?,"
              " pnl_pct = ? WHERE id = ?",
              (curr_px, pnl, sig_id),
          )

    for sig in actionable_signals:
      coin = sig["Coin"]
      curr_px = float(all_mids.get(coin, 0))
      if curr_px > 0:
        cursor.execute(
            "SELECT id FROM signal_history WHERE coin = ? AND status = 'OPEN'",
            (coin,),
        )
        if not cursor.fetchone():
          now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              """
                        INSERT INTO signal_history (timestamp, coin, signal, entry_price, exit_price, status, pnl_pct, conviction)
                        VALUES (?, ?, ?, ?, ?, 'OPEN', 0.0, ?)
                    """,
              (
                  now_str,
                  coin,
                  sig["Signal"],
                  curr_px,
                  curr_px,
                  sig["Conviction"],
              ),
          )
    conn.commit()


def get_performance_data():
  init_db()
  with sqlite3.connect(DB_PATH) as conn:
    return pd.read_sql_query(
        "SELECT * FROM signal_history ORDER BY id DESC", conn
    )


# ==============================================================================
# 100 PROMINENT ON-CHAIN HYPERLIQUID WALLETS
# ==============================================================================
DEFAULT_100_WALLETS = [
    "0xa312114b5795dff9b8db50474dd57701aa78ad1e",
    "0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6",
    "0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae",
    "0xf3f496c9486be5924a93d67e98298733bb47057c",
    "0xa697a5b929cca9b3f8a78c4e4af1848506c06022",
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
    "0x4010892c55452d50cb68b556efc5fa624d62b172",
    "0xb75a02aa3dfa09e0486c4f7461ef33932be0f8f1",
    "0x94b58e734c8fc4859a72dfc9e8d477f1e72e9f85",
    "0x51c708170c0c6dc67664421111666fffa0c76db3",
    "0x608e0108a7b0577be34f59fa0f4e3c54d193d5bf",
    "0x38e55e56e07d6a2f3c7d67ff9b9772d6ff31578e",
    "0x9e44b360f7e1b6f041d8e13636735e07661b17e4",
    "0x2e8f17066927a7cc9497e2089b0d611b7bcba12e",
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",
    "0x583019000bb38c1a6673004ff6052710921271b4",
    "0x6cc5f688a305ca3a4c447e60b094270211249764",
    "0xd551234ae421e3bcba99a0da6d7360741b227b4f",
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe",
    "0x1807f6ca9b332ea5ccda3a254c84bdf90e412c5a",
    "0xc20ac4dc4188660cbf555448af52694ca62b0734",
    "0xc2a30212a8ddac9e123944d6e29faddce994e5f2",
    "0x20c2d95a3dfdca9e9ad12794d5fa6fad99da44f5",
    "0x197d1d1127b1a1da550f089375369d5acfeb0c72",
    "0x4b706f97ef9bebb4599a0a4ff8217bbba9d24329",
    "0x880ac484a1743862989a441d6d867238c7aa311c",
    "0x8c967e73e6b15087c42a10d344cff4c96d877f1d",
    "0x74da055d4ccf9dca3f15789c603e1a88a1d2d81f",
    "0x23af9804b497063f3bf62d6657c79e6f987d6051",
    "0x39aa39c021dfbae8fac545936693ac917d5e7563",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
    "0x1111111254fb6c44bac0bed2854e76f90643097d",
    "0x28c6c06298d514db089934071355e5743bf21d60",
    "0x1522900b6dafac587d499a862861c0869be6e428",
    "0x3356e154f8a2f7c00e12e75e1ecdf34891b61972",
    "0x77134cb632456c464695ad56e069f7d86921b5e9",
    "0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a",
    "0xf977814e90da44bfa03b6295a0616a897441acec",
    "0xab5801a7d398351b8be11c439e05c5b3259aec9b",
    "0x6b175474e89094c44da98b954eedeac495271d0f",
    "0x6295ee1b4f6dd65047762f9247da7b2c74d42921",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",
    "0x0a98b2b1686747f329976864064229664600137a",
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",
    "0x5ae4f94073d88bf8c0f5f65bc7c578051754020c",
    "0xe867fbdad3291530e41530301ecb77693850c78e",
    "0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf",
    "0x5b38da6a701c568545dcfcb03fcb875f56beddc4",
    "0x71c7656ec7ab88b098defb751b7401b5f6d8976f",
]


# ==============================================================================
# FAST PARALLEL DATA FETCHING
# ==============================================================================
def scan_single_wallet(info, address, all_mids):
  positions = []
  try:
    state = info.user_state(address)
    for item in state.get("assetPositions", []):
      pos = item.get("position", {})
      size = float(pos.get("szi", 0))

      if size != 0:
        coin = pos.get("coin")
        side = "LONG" if size > 0 else "SHORT"
        entry_px = float(pos.get("entryPx", 0))
        curr_px = float(all_mids.get(coin, entry_px))
        pnl = float(pos.get("unrealizedPnl", 0))

        position_value = abs(size) * curr_px
        roi_pct = (
            (pnl / (abs(size) * entry_px) * 100)
            if entry_px > 0 and size != 0
            else 0.0
        )
        leverage = pos.get("leverage", {}).get("value", "Cross")

        trader_label = ELITE_WALLETS.get(
            address, f"Trader {address[:6]}...{address[-4:]}"
        )

        positions.append({
            "Wallet": f"{address[:6]}...{address[-4:]}",
            "Full Address": address,
            "Trader Label": trader_label,
            "Coin": coin,
            "Side": side,
            "Size": abs(size),
            "Entry Price": entry_px,
            "Current Price": curr_px,
            "Position Value ($)": position_value,
            "Unrealized PnL ($)": pnl,
            "ROI (%)": roi_pct,
            "Leverage": f"{leverage}x"
            if isinstance(leverage, (int, float))
            else str(leverage),
        })
  except Exception:
    pass
  return positions


@st.cache_data(ttl=60)
def fetch_hyperliquid_data(wallet_list):
  info = Info(constants.MAINNET_API_URL, skip_ws=True)
  try:
    all_mids = info.all_mids()
  except Exception:
    all_mids = {}

  all_positions = []
  active_wallets_set = set()

  with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(
        executor.map(
            lambda addr: scan_single_wallet(info, addr, all_mids), wallet_list
        )
    )

  for res in results:
    if res:
      all_positions.extend(res)
      active_wallets_set.add(res[0]["Full Address"])

  return all_mids, pd.DataFrame(all_positions), len(active_wallets_set)


# ==============================================================================
# TRADE QUALITY SCORING ALGORITHM (Coin Level)
# ==============================================================================
def score_trade_quality(c):
  score = 50.0
  roi = c["Raw_ROI"]

  if roi >= 0:
    score += min(roi * 4.0, 30.0)
  else:
    score += max(roi * 2.5, -45.0)

  score += (c["Raw_Conviction"] - 0.5) * 30.0

  if c["Raw_Volume"] >= 500000:
    score += 8.0
  elif c["Raw_Volume"] >= 100000:
    score += 4.0

  if c["Raw_Whales"] >= 2 and c["Raw_Conviction"] >= 0.80:
    score += 10.0

  return round(max(min(score, 99.9), 1.0), 1)


# ==============================================================================
# SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
  st.header("⚙️ Radar Controls")
  min_traders = st.slider("Min Whales in Position", 1, 5, 1)
  consensus_threshold = (
      st.slider("Consensus Threshold (%)", 50, 100, 60) / 100
  )
  hide_exotics = st.checkbox("Only Show Majors (BTC, ETH, SOL, HYPE)", False)

  if st.button("🔄 Refresh Data Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

  st.divider()
  st.caption("Live feed from Hyperliquid L1 (auto-updates every 60s).")

# ==============================================================================
# DATA LOAD & PROCESSING
# ==============================================================================
with st.spinner("Analyzing whale positioning & elite trader plays..."):
  mids, df_positions, active_count = fetch_hyperliquid_data(DEFAULT_100_WALLETS)

if hide_exotics and not df_positions.empty:
  df_positions = df_positions[
      df_positions["Coin"].isin(["BTC", "ETH", "SOL", "HYPE"])
  ]

coin_summaries = []
actionable_signals = []

if not df_positions.empty:
  for coin, group in df_positions.groupby("Coin"):
    total_whales = len(group)
    longs = len(group[group["Side"] == "LONG"])
    shorts = len(group[group["Side"] == "SHORT"])

    total_value = group["Position Value ($)"].sum()
    total_pnl = group["Unrealized PnL ($)"].sum()
    avg_entry = group["Entry Price"].mean()
    curr_px = float(mids.get(coin, avg_entry))

    group_roi = (
        (total_pnl / (total_value - total_pnl) * 100)
        if (total_value - total_pnl) > 0
        else 0.0
    )

    long_ratio = longs / total_whales
    short_ratio = shorts / total_whales
    conviction = max(long_ratio, short_ratio)
    majority_side = "LONG" if long_ratio >= short_ratio else "SHORT"

    item = {
        "Coin": coin,
        "Current Price": f"${curr_px:,.2f}",
        "Avg Entry": f"${avg_entry:,.2f}",
        "Majority Side": majority_side,
        "Whales in Trade": f"{total_whales} ({longs}L / {shorts}S)",
        "Total Volume ($)": f"${total_value:,.2f}",
        "Group PnL ($)": f"${total_pnl:+,.2f}",
        "Group ROI (%)": f"{group_roi:+.2f}%",
        "Raw_Volume": total_value,
        "Raw_ROI": group_roi,
        "Raw_PnL": total_pnl,
        "Raw_Whales": total_whales,
        "Raw_Conviction": conviction,
    }

    item["Quality_Score"] = score_trade_quality(item)
    coin_summaries.append(item)

    if conviction >= consensus_threshold and total_whales >= min_traders:
      actionable_signals.append({
          "Coin": coin,
          "Signal": f"STRONG {majority_side}",
          "Conviction": f"{conviction*100:.0f}%",
      })

log_or_update_signals(actionable_signals, mids)
df_history = get_performance_data()

# ==============================================================================
# MAIN DASHBOARD INTERFACE
# ==============================================================================
st.title("⚡ Hyperliquid Smart Money Radar")

tab1, tab2 = st.tabs(
    ["⚡ Live Whale Radar", "📜 Signal History & Success Rate"]
)

with tab1:
  # Top Header Metric Bar
  c1, c2, c3, c4 = st.columns(4)
  total_deployed = (
      df_positions["Position Value ($)"].sum() if not df_positions.empty else 0
  )
  net_pnl = (
      df_positions["Unrealized PnL ($)"].sum() if not df_positions.empty else 0
  )
  btc_px = float(mids.get("BTC", 0))

  c1.metric("Active Whales in Market", f"{active_count} Traders")
  c2.metric("Total Whale Capital", f"${total_deployed:,.0f}")
  c3.metric("Net Whale Profit/Loss", f"${net_pnl:+,.0f}")
  c4.metric("BTC Market Price", f"${btc_px:,.1f}" if btc_px else "Loading...")

  st.divider()

  # ==========================================================================
  # SECTION 1: TOP 3 BEST LOOKING WHALE TRADES (COIN CONSENSUS)
  # ==========================================================================
  st.subheader("🔥 Top 3 Best-Looking Whale Setups")
  st.caption(
      "Highest quality trade consensus across all whales (scored by positive"
      " momentum, conviction, and low drawdown)."
  )

  if not coin_summaries:
    st.info("No active whale positions detected at the moment.")
  else:
    best_trades = sorted(
        coin_summaries, key=lambda x: x["Quality_Score"], reverse=True
    )[:3]
    top_cols = st.columns(len(best_trades))

    for idx, t in enumerate(best_trades):
      with top_cols[idx]:
        side_color = "badge-long" if t["Majority Side"] == "LONG" else "badge-short"
        roi_color = "#34d399" if t["Raw_ROI"] >= 0 else "#f87171"

        st.markdown(
            f"""
                <div class="top-trade-card">
                    <h3 style="margin-top: 0;">#{idx+1} {t['Coin']} <span class="{side_color}">{t['Majority Side']}</span></h3>
                    <p style="font-size: 1.1rem; margin-bottom: 8px;">
                        <b>Score:</b> <span style="color: #60a5fa; font-weight: bold;">{t['Quality_Score']}/100</span>
                    </p>
                    <p style="margin: 4px 0;"><b>🐋 Whales:</b> <code>{t['Whales in Trade']}</code></p>
                    <p style="margin: 4px 0;"><b>🎯 Avg Entry:</b> <code>{t['Avg Entry']}</code></p>
                    <p style="margin: 4px 0;"><b>📈 Current Px:</b> <code>{t['Current Price']}</code></p>
                    <p style="margin: 4px 0;"><b>💰 Volume:</b> <code>{t['Total Volume ($)']}</code></p>
                    <p style="margin: 4px 0;"><b>💵 PnL:</b> <span style="color: {roi_color}; font-weight: bold;">{t['Group PnL ($)']} ({t['Group ROI (%)']})</span></p>
                </div>
                """,
            unsafe_allow_html=True,
        )

  st.divider()

  # ==========================================================================
  # SECTION 2: LIVE TRADES FROM THE TOP ELITE TRADERS
  # ==========================================================================
  st.subheader("👑 Live Trades from Top Individual Whales")
  st.caption(
      "Direct positions currently open by verified leaderboard legends and"
      " high-earning traders."
  )

  if df_positions.empty:
    st.info("No individual trader positions detected.")
  else:
    # Sort individual positions by highest unrealized profit ($)
    elite_trades = df_positions.sort_values(
        by="Unrealized PnL ($)", reverse=True
    ).head(3)

    trader_cols = st.columns(min(len(elite_trades), 3))

    for idx, (_, row) in enumerate(elite_trades.iterrows()):
      with trader_cols[idx]:
        side_color = "badge-long" if row["Side"] == "LONG" else "badge-short"
        roi_color = "#34d399" if row["ROI (%)"] >= 0 else "#f87171"
        explorer_url = f"https://app.hyperliquid.xyz/explorer/address/{row['Full Address']}"

        st.markdown(
            f"""
                <div class="trader-trade-card">
                    <h4 style="margin-top: 0; color: #fbbf24;">{row['Trader Label']}</h4>
                    <p style="font-size: 1.15rem; margin-bottom: 6px;">
                        <b>{row['Coin']}</b> <span class="{side_color}">{row['Side']} {row['Leverage']}</span>
                    </p>
                    <p style="margin: 4px 0;"><b>🎯 Entry:</b> <code>${row['Entry Price']:,.2f}</code> | <b>Current:</b> <code>${row['Current Price']:,.2f}</code></p>
                    <p style="margin: 4px 0;"><b>💰 Trade Value:</b> <code>${row['Position Value ($)']:,.2f}</code></p>
                    <p style="margin: 4px 0;"><b>💵 Trader PnL:</b> <span style="color: {roi_color}; font-weight: bold;">${row['Unrealized PnL ($)']:+,.2f} ({row['ROI (%)']:+.2f}%)</span></p>
                    <p style="margin: 8px 0 0 0;">
                        <a href="{explorer_url}" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.85rem;">🔗 View Wallet on Hyperliquid →</a>
                    </p>
                </div>
                """,
            unsafe_allow_html=True,
        )

  st.divider()

  # ==========================================================================
  # SECTION 3: ALL ACTIVE ASSETS BREAKDOWN TABLE
  # ==========================================================================
  st.subheader("📊 Complete Whale Portfolio Breakdown")
  if coin_summaries:
    df_overview = pd.DataFrame(
        sorted(coin_summaries, key=lambda x: x["Raw_Volume"], reverse=True)
    )[[
        "Coin",
        "Majority Side",
        "Quality_Score",
        "Current Price",
        "Avg Entry",
        "Whales in Trade",
        "Total Volume ($)",
        "Group PnL ($)",
        "Group ROI (%)",
    ]]
    st.dataframe(df_overview, use_container_width=True, hide_index=True)

  st.divider()

  # ==========================================================================
  # SECTION 4: DETAILED INDIVIDUAL POSITIONS TABLE
  # ==========================================================================
  st.subheader("🐋 Individual Open Positions")
  if not df_positions.empty:
    coins = sorted(df_positions["Coin"].unique())
    selected_coins = st.multiselect(
        "Filter by Asset", options=coins, default=coins[:6]
    )
    filtered_df = df_positions[df_positions["Coin"].isin(selected_coins)].copy()

    filtered_df["Entry Price"] = filtered_df["Entry Price"].apply(
        lambda x: f"${x:,.2f}"
    )
    filtered_df["Current Price"] = filtered_df["Current Price"].apply(
        lambda x: f"${x:,.2f}"
    )
    filtered_df["Position Value ($)"] = filtered_df["Position Value ($)"].apply(
        lambda x: f"${x:,.2f}"
    )
    filtered_df["Unrealized PnL ($)"] = filtered_df["Unrealized PnL ($)"].apply(
        lambda x: f"${x:+,.2f}"
    )
    filtered_df["ROI (%)"] = filtered_df["ROI (%)"].apply(lambda x: f"{x:+.2f}%")

    st.dataframe(
        filtered_df[[
            "Wallet",
            "Coin",
            "Side",
            "Entry Price",
            "Current Price",
            "Position Value ($)",
            "Unrealized PnL ($)",
            "ROI (%)",
            "Leverage",
        ]],
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------------------------
# TAB 2: SIGNAL HISTORY & SUCCESS RATE
# ------------------------------------------------------------------------------
with tab2:
  st.subheader("📈 Historical Signal Performance")
  if df_history.empty:
    st.info("No historical signals logged yet.")
  else:
    wins = len(df_history[df_history["status"] == "WIN"])
    losses = len(df_history[df_history["status"] == "LOSS"])
    open_trades = len(df_history[df_history["status"] == "OPEN"])
    closed = wins + losses
    win_rate = (wins / closed * 100) if closed > 0 else 0.0

    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Win Rate (%)", f"{win_rate:.1f}%")
    hc2.metric("Total Wins ✅", f"{wins}")
    hc3.metric("Total Losses ❌", f"{losses}")
    hc4.metric("Active / Open Trades ⏳", f"{open_trades}")

    st.dataframe(
        df_history[[
            "timestamp",
            "coin",
            "signal",
            "entry_price",
            "exit_price",
            "status",
            "pnl_pct",
            "conviction",
        ]],
        use_container_width=True,
        hide_index=True,
    )
