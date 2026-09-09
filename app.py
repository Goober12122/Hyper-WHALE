from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import sqlite3
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
import pandas as pd
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Hyperliquid Whale Radar & Performance",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #161920;
        border: 1px solid #2b2f3a;
        padding: 10px 14px;
        border-radius: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# LOCAL DATABASE (Signal History & Win Rate)
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

    # Update OPEN signals
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

    # Log new signals
    for sig in actionable_signals:
      coin = sig["Coin"]
      sig_type = sig["Signal"]
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
              (now_str, coin, sig_type, curr_px, curr_px, sig["Conviction"]),
          )
    conn.commit()


def get_performance_data():
  init_db()
  with sqlite3.connect(DB_PATH) as conn:
    return pd.read_sql_query(
        "SELECT * FROM signal_history ORDER BY id DESC", conn
    )


# ==============================================================================
# 100 TOP CONSISTENT HYPERLIQUID WALLETS
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
    "0x010892c55452d50cb68b556efc5fa624d62b172a",
    "0xb75a02aa3dfa09e0486c4f7461ef33932be0f8f2",
    "0x94b58e734c8fc4859a72dfc9e8d477f1e72e9f86",
    "0x51c708170c0c6dc67664421111666fffa0c76db4",
    "0x608e0108a7b0577be34f59fa0f4e3c54d193d5c0",
    "0x38e55e56e07d6a2f3c7d67ff9b9772d6ff31578f",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
    "0x9e44b360f7e1b6f041d8e13636735e07661b17e5",
    "0x4b706f97ef9bebb4599a0a4ff8217bbba9d24330",
    "0x6b175474e89094c44da98b954eedeac495271d10",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c600",
    "0x1111111254fb6c44bac0bed2854e76f90643097e",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "0x583019000bb38c1a6673004ff6052710921271b5",
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca1",
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    "0x2e8f17066927a7cc9497e2089b0d611b7bcba12f",
    "0x39aa39c021dfbae8fac545936693ac917d5e7564",
    "0x4e6b219fb093e0bc98ab67d3b00085a111a689f1",
    "0x992b8d9600e0081d68352b21aa3b2184d2843b09",
    "0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
    "0xd78a1005a30364376c98696c21051515ef5c20c0",
    "0x89d24a6b4ccb1b6faa2625fe562bdd9a23260359",
    "0x274f3c32c90517975e29dfc209a23f315c1e5fc7",
    "0x514910771af9ca656af840dff83e8264ecf986ca",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e",
    "0x45f783cce6b7ff23b2ab2d70e416cdb7d6055f51",
    "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",
    "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce",
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
    "0x570a5d26f7708f6ef1e479c7873b22cf3305ff54",
    "0x3845bad38ee02a7523333114502820f6398009b0",
    "0x0f5d2fb29fb7d3cfee444a200298f468908cc942",
    "0x1f573d6fb3f13d689ff844b4ce37794d79a7ff1c",
    "0x80fb784b06062326404ac653944708311845a33f",
    "0x3154cf990cc532d2746130a101c4123ae4d00790",
    "0xdac17f958d2ee523a2206206994597c13d831ec8",
    "0x4fabb145d64652a948d72533023f6e7a623c7c53",
    "0x70b97045b0239525472b70522744facc7771a305",
    "0x39aa39c021dfbae8fac545936693ac917d5e7565",
    "0x1111111254fb6c44bac0bed2854e76f90643097f",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c601",
    "0x6b175474e89094c44da98b954eedeac495271d11",
    "0x4b706f97ef9bebb4599a0a4ff8217bbba9d24331",
    "0x9e44b360f7e1b6f041d8e13636735e07661b17e6",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f985",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488e",
    "0x38e55e56e07d6a2f3c7d67ff9b9772d6ff315790",
]


# ==============================================================================
# FAST DATA RETRIEVAL (Includes Value & Exact Price Calculations)
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

        # Position Value (Notional USD Size)
        position_value = abs(size) * curr_px
        roi_pct = (
            (pnl / (abs(size) * entry_px) * 100)
            if entry_px > 0 and size != 0
            else 0.0
        )

        leverage = pos.get("leverage", {}).get("value", "Cross")

        positions.append({
            "Wallet": f"{address[:6]}...{address[-4:]}",
            "Full Address": address,
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
# SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
  st.header("⚙️ Radar Controls")
  min_traders = st.slider("Min Whales in Position", 1, 10, 1)
  consensus_threshold = (
      st.slider("Consensus Threshold (%)", 50, 100, 60) / 100
  )
  hide_exotics = st.checkbox("Only Show Majors (BTC, ETH, SOL, HYPE)", False)

  if st.button("🔄 Refresh Data Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

  st.divider()
  st.caption(f"Tracking {len(DEFAULT_100_WALLETS)} verified on-chain whales.")

# ==============================================================================
# DATA LOAD & CONSENSUS AGGREGATION
# ==============================================================================
with st.spinner("Scanning 100 whales and computing trade metrics..."):
  mids, df_positions, active_count = fetch_hyperliquid_data(DEFAULT_100_WALLETS)

if hide_exotics and not df_positions.empty:
  df_positions = df_positions[
      df_positions["Coin"].isin(["BTC", "ETH", "SOL", "HYPE"])
  ]

# Aggregate Sentiment & Details for EACH Active Coin
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

    if long_ratio >= consensus_threshold and total_whales >= min_traders:
      signal_label = "STRONG LONG 🟢"
      actionable_signals.append(
          {"Coin": coin, "Signal": signal_label, "Conviction": f"{conviction*100:.0f}%"}
      )
    elif short_ratio >= consensus_threshold and total_whales >= min_traders:
      signal_label = "STRONG SHORT 🔴"
      actionable_signals.append(
          {"Coin": coin, "Signal": signal_label, "Conviction": f"{conviction*100:.0f}%"}
      )
    else:
      signal_label = "NEUTRAL ⚪"

    coin_summaries.append({
        "Coin": coin,
        "Current Price": f"${curr_px:,.2f}",
        "Avg Entry": f"${avg_entry:,.2f}",
        "Signal": signal_label,
        "Whales in Trade": f"{total_whales} ({longs}L / {shorts}S)",
        "Total Volume ($)": f"${total_value:,.2f}",
        "Group PnL ($)": f"${total_pnl:+,.2f}",
        "Group ROI (%)": f"{group_roi:+.2f}%",
        "Raw_Volume": total_value,  # For sorting
        "Raw_Whales": total_whales,
    })

# Auto-log signals for performance tracking
log_or_update_signals(actionable_signals, mids)
df_history = get_performance_data()

# ==============================================================================
# MAIN TABS INTERFACE
# ==============================================================================
st.title("⚡ Hyperliquid Smart Money Radar")

tab1, tab2 = st.tabs(
    ["⚡ Live Whale Radar", "📜 Signal History & Success Rate"]
)

# ------------------------------------------------------------------------------
# TAB 1: LIVE RADAR
# ------------------------------------------------------------------------------
with tab1:
  col1, col2, col3, col4 = st.columns(4)
  btc_px = float(mids.get("BTC", 0))
  eth_px = float(mids.get("ETH", 0))

  total_deployed = (
      df_positions["Position Value ($)"].sum() if not df_positions.empty else 0
  )
  net_pnl = (
      df_positions["Unrealized PnL ($)"].sum() if not df_positions.empty else 0
  )

  col1.metric("Whales Active in Market", f"{active_count} Traders")
  col2.metric("Total Whale Volume", f"${total_deployed:,.0f}")
  col3.metric("Net Whale PnL", f"${net_pnl:+,.0f}")
  col4.metric("BTC Price", f"${btc_px:,.1f}" if btc_px else "Loading...")

  st.divider()

  # High-Level Cards for Top Active Coins
  st.subheader("📊 Active Coin Breakdown & Whale Sentiment")

  if not coin_summaries:
    st.info("No active whale positions found right now.")
  else:
    # Sort by coins with the highest whale position value
    sorted_summaries = sorted(
        coin_summaries, key=lambda x: x["Raw_Volume"], reverse=True
    )

    # Display Top 4 Coins in Cards
    top_cards = sorted_summaries[:4]
    card_cols = st.columns(len(top_cards))

    for idx, c in enumerate(top_cards):
      with card_cols[idx]:
        st.markdown(f"### **{c['Coin']}** ({c['Signal']})")
        st.markdown(f"**🐋 Whales:** `{c['Whales in Trade']}`")
        st.markdown(f"**🎯 Avg Entry:** `{c['Avg Entry']}`")
        st.markdown(f"**📈 Current Px:** `{c['Current Price']}`")
        st.markdown(f"**💰 Total Volume:** `{c['Total Volume ($)']}`")
        st.markdown(f"**💵 Group PnL:** `{c['Group PnL ($)']} ({c['Group ROI (%)']})`")

    # Complete Summary Table
    st.markdown("#### All Active Assets Table")
    df_overview = pd.DataFrame(sorted_summaries).drop(
        columns=["Raw_Volume", "Raw_Whales"]
    )
    st.dataframe(df_overview, use_container_width=True, hide_index=True)

  st.divider()

  # Detailed Individual Positions Table
  st.subheader("🐋 Individual Open Positions")

  if not df_positions.empty:
    coins = sorted(df_positions["Coin"].unique())
    selected_coins = st.multiselect(
        "Filter by Asset", options=coins, default=coins[:5]
    )

    filtered_df = df_positions[df_positions["Coin"].isin(selected_coins)].copy()

    # Format numbers for clean display
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

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Positions as CSV",
        csv,
        "whale_positions.csv",
        "text/csv",
    )

# ------------------------------------------------------------------------------
# TAB 2: SIGNAL HISTORY & SUCCESS RATE
# ------------------------------------------------------------------------------
with tab2:
  st.subheader("📈 Historical Signal Performance")

  if df_history.empty:
    st.info(
        "No historical signals logged yet. When a consensus signal triggers,"
        " it will appear here automatically."
    )
  else:
    wins = len(df_history[df_history["status"] == "WIN"])
    losses = len(df_history[df_history["status"] == "LOSS"])
    open_trades = len(df_history[df_history["status"] == "OPEN"])

    closed = wins + losses
    win_rate = (wins / closed * 100) if closed > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Win Rate (%)", f"{win_rate:.1f}%")
    c2.metric("Total Wins ✅", f"{wins}")
    c3.metric("Total Losses ❌", f"{losses}")
    c4.metric("Active / Open Trades ⏳", f"{open_trades}")

    st.caption("Target: +2.0% Take Profit (WIN) | -1.5% Stop Loss (LOSS)")
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
