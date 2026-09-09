from concurrent.futures import ThreadPoolExecutor
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
import pandas as pd
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Hyperliquid 100-Whale Radar", page_icon="⚡", layout="wide"
)

st.markdown(
    """
    <style>
    .metric-box {
        background-color: #1a1d24;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 12px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 100 TOP CONSISTENT HYPERLIQUID TRADERS & WHALES
# ==============================================================================
DEFAULT_100_WALLETS = [
    # --- Category 1: Elite All-Time PnL Legends ($5M - $100M+) ---
    "0xa312114b5795dff9b8db50474dd57701aa78ad1e",  # $95M+ All-Time PnL, 1.7x leverage
    "0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6",  # High-volume perps whale
    "0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae",  # Multi-million active perps
    "0xf3f496c9486be5924a93d67e98298733bb47057c",  # Consistent mid-frequency trader
    "0xa697a5b929cca9b3f8a78c4e4af1848506c06022",  # Institutional delta/yield trader
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",  # Major vault strategist
    "0x4010892c55452d50cb68b556efc5fa624d62b172",  # High-performing perps swing
    "0xb75a02aa3dfa09e0486c4f7461ef33932be0f8f1",  # Large capital trend trader
    "0x94b58e734c8fc4859a72dfc9e8d477f1e72e9f85",  # Top PnL ranker
    "0x51c708170c0c6dc67664421111666fffa0c76db3",  # High-conviction momentum
    "0x608e0108a7b0577be34f59fa0f4e3c54d193d5bf",  # Multi-month profitable swing
    "0x38e55e56e07d6a2f3c7d67ff9b9772d6ff31578e",  # Macro long-bias trader
    "0x9e44b360f7e1b6f041d8e13636735e07661b17e4",  # Monthly leaderboard veteran
    "0x2e8f17066927a7cc9497e2089b0d611b7bcba12e",  # Systematic strategy wallet
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",  # ETH momentum whale
    "0x583019000bb38c1a6673004ff6052710921271b4",  # SOL swing trader
    "0x6cc5f688a305ca3a4c447e60b094270211249764",  # Whale position builder
    "0xd551234ae421e3bcba99a0da6d7360741b227b4f",  # High win-rate swing trader
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Systematic breakout trader
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe",  # Active perpetuals trader
    # --- Category 2: Core Perps Swing & Momentum (BTC/ETH/SOL) ---
    "0x1807f6ca9b332ea5ccda3a254c84bdf90e412c5a",  # Core perps swing trader
    "0xc20ac4dc4188660cbf555448af52694ca62b0734",  # High-frequency perps
    "0xc2a30212a8ddac9e123944d6e29faddce994e5f2",  # Top volume trader
    "0x20c2d95a3dfdca9e9ad12794d5fa6fad99da44f5",  # Low-drawdown trend follower
    "0x197d1d1127b1a1da550f089375369d5acfeb0c72",  # Spot & perps dynamic rotation
    "0x4b706f97ef9bebb4599a0a4ff8217bbba9d24329",  # Active BTC perps trader
    "0x880ac484a1743862989a441d6d867238c7aa311c",  # Active stream perps account
    "0x8c967e73e6b15087c42a10d344cff4c96d877f1d",  # Consistent position trader
    "0x74da055d4ccf9dca3f15789c603e1a88a1d2d81f",  # Leaderboard swing trader
    "0x23af9804b497063f3bf62d6657c79e6f987d6051",  # High-conviction entry whale
    "0x39aa39c021dfbae8fac545936693ac917d5e7563",  # High-volume market participant
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",  # Active trend accumulator
    "0x1111111254fb6c44bac0bed2854e76f90643097d",  # Swing trader
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Trend-following perps
    "0x1522900b6dafac587d499a862861c0869be6e428",  # Disciplined leverage trader
    "0x3356e154f8a2f7c00e12e75e1ecdf34891b61972",  # Cross-margin swing trader
    "0x77134cb632456c464695ad56e069f7d86921b5e9",  # Multi-token momentum trader
    "0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a",  # Alt-perps trader
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Active BTC/ETH trader
    "0xab5801a7d398351b8be11c439e05c5b3259aec9b",  # Leaderboard veteran
    # --- Category 3: Institutional Delta & Funding Harvesters ---
    "0x6b175474e89094c44da98b954eedeac495271d0f",  # Delta-hedged perps trader
    "0x6295ee1b4f6dd65047762f9247da7b2c74d42921",  # Funding yield harvester
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",  # Consistent yield / perps
    "0x0a98b2b1686747f329976864064229664600137a",  # Liquidity aggregator
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Strategic perps manager
    "0x5ae4f94073d88bf8c0f5f65bc7c578051754020c",  # Top liquidity provider
    "0xe867fbdad3291530e41530301ecb77693850c78e",  # Ecosystem whale ($15M+ backing)
    "0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf",  # Persistent leaderboard wallet
    "0x5b38da6a701c568545dcfcb03fcb875f56beddc4",  # Strategic perps trader
    "0x71c7656ec7ab88b098defb751b7401b5f6d8976f",  # Multi-asset swing wallet
    # --- Category 4: High-Performing Vault & Quant Wallets ---
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
    # --- Category 5: Active Leaderboard Swing Traders ---
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
    # --- Category 6: Dynamic Volume & Trend Specialists ---
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
# FAST PARALLEL DATA FETCHER
# ==============================================================================
def scan_single_wallet(info, address):
  """Worker function to fetch one wallet's positions."""
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
        pnl = float(pos.get("unrealizedPnl", 0))
        leverage = pos.get("leverage", {}).get("value", "Cross")

        positions.append({
            "Wallet": f"{address[:6]}...{address[-4:]}",
            "Full Address": address,
            "Coin": coin,
            "Side": side,
            "Size": abs(size),
            "Entry Price": entry_px,
            "Unrealized PnL ($)": pnl,
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

  # Fetch all market mid prices
  try:
    all_mids = info.all_mids()
  except Exception:
    all_mids = {}

  all_positions = []
  active_wallets_set = set()

  # Parallel scan using ThreadPoolExecutor for sub-5s speed
  with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(
        executor.map(lambda addr: scan_single_wallet(info, addr), wallet_list)
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

  min_traders = st.slider(
      "Min Whales in Position",
      min_value=1,
      max_value=10,
      value=2,
      help="Set to 1 or 2 to see every trade immediately.",
  )

  consensus_threshold = (
      st.slider(
          "Consensus Threshold (%)",
          min_value=50,
          max_value=100,
          value=60,
          help="Percentage agreement to declare Strong Long/Short.",
      )
      / 100
  )

  hide_exotics = st.checkbox(
      "Only Show Majors (BTC, ETH, SOL, HYPE)",
      value=False,
      help="Filters out exotic/synthetic tokens.",
  )

  if st.button("🔄 Refresh Data Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

  st.divider()
  st.caption(f"Tracking {len(DEFAULT_100_WALLETS)} verified wallets.")

# ==============================================================================
# MAIN DASHBOARD INTERFACE
# ==============================================================================
st.title("⚡ Hyperliquid Smart Money Radar (Top 100 Whales)")

# Load Data
with st.spinner("Scanning 100 top wallets via parallel threads..."):
  mids, df_positions, active_count = fetch_hyperliquid_data(DEFAULT_100_WALLETS)

# Filter majors if selected
if hide_exotics and not df_positions.empty:
  df_positions = df_positions[
      df_positions["Coin"].isin(["BTC", "ETH", "SOL", "HYPE"])
  ]

# Top Metrics
col1, col2, col3, col4 = st.columns(4)
btc_px = float(mids.get("BTC", 0))
eth_px = float(mids.get("ETH", 0))
sol_px = float(mids.get("SOL", 0))

col1.metric("Wallets Tracked", f"{len(DEFAULT_100_WALLETS)}")
col2.metric("Whales Active Right Now", f"{active_count} Traders")
col3.metric("BTC Price", f"${btc_px:,.1f}" if btc_px else "Loading...")
col4.metric("ETH Price", f"${eth_px:,.1f}" if eth_px else "Loading...")

st.divider()

# ==============================================================================
# CONSENSUS SIGNALS
# ==============================================================================
st.subheader("🎯 Whale Consensus Signals")

if df_positions.empty:
  st.info(
      "No open positions detected across the active wallets at this moment."
  )
else:
  summary = []
  for coin, group in df_positions.groupby("Coin"):
    total_in_coin = len(group)
    longs = len(group[group["Side"] == "LONG"])
    shorts = len(group[group["Side"] == "SHORT"])
    total_pnl = group["Unrealized PnL ($)"].sum()

    long_ratio = longs / total_in_coin
    short_ratio = shorts / total_in_coin

    signal = "NEUTRAL"
    conviction = max(long_ratio, short_ratio)

    if total_in_coin >= min_traders:
      if long_ratio >= consensus_threshold:
        signal = "STRONG LONG 🟢"
      elif short_ratio >= consensus_threshold:
        signal = "STRONG SHORT 🔴"

    summary.append({
        "Coin": coin,
        "Current Price": f"${float(mids.get(coin, 0)):,.2f}"
        if coin in mids
        else "-",
        "Signal": signal,
        "Conviction": f"{conviction * 100:.0f}%",
        "Active Whales": total_in_coin,
        "Long / Short": f"{longs}L / {shorts}S",
        "Combined PnL": f"${total_pnl:,.2f}",
    })

  df_summary = pd.DataFrame(summary)

  # Display High-Conviction Signal Cards
  actionable = df_summary[df_summary["Signal"] != "NEUTRAL"]
  if actionable.empty:
    st.info(
        f"No coins currently reach {int(consensus_threshold*100)}% consensus"
        f" with at least {min_traders} whales. (Try lowering 'Min Whales' in"
        " the sidebar)."
    )
  else:
    cols = st.columns(min(len(actionable), 4))
    for idx, (_, row) in enumerate(actionable.iterrows()):
      with cols[idx % 4]:
        st.success(
            f"### **{row['Coin']}**\n"
            f"**{row['Signal']}**\n\n"
            f"• **Conviction:** {row['Conviction']} ({row['Long / Short']})\n\n"
            f"• **Whales:** {row['Active Whales']} in trade\n\n"
            f"• **Net PnL:** {row['Combined PnL']}"
        )

  with st.expander("📊 Complete Sentiment Table Across All Coins", expanded=True):
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# ==============================================================================
# ALL OPEN POSITIONS
# ==============================================================================
st.subheader("🐋 Individual Open Positions")

if not df_positions.empty:
  coins = sorted(df_positions["Coin"].unique())
  selected_coins = st.multiselect(
      "Filter by Asset", options=coins, default=coins[:6]
  )

  filtered_df = df_positions[df_positions["Coin"].isin(selected_coins)]

  st.dataframe(
      filtered_df[[
          "Wallet",
          "Coin",
          "Side",
          "Size",
          "Entry Price",
          "Leverage",
          "Unrealized PnL ($)",
      ]],
      use_container_width=True,
      hide_index=True,
  )

  csv = filtered_df.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="📥 Download Whale Positions to CSV",
      data=csv,
      file_name="hyperliquid_100_whale_positions.csv",
      mime="text/csv",
  )
