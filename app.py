import streamlit as st
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
import pytz
import shutil

st.set_page_config(
    page_title="CGV Rate IR Compare Dashboard",
    layout="wide",
    page_icon="🌍"
)

# ===== SESSION =====
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

toggle = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
st.session_state.dark_mode = toggle

# ===== THEME =====
if st.session_state.dark_mode:
    bg = "#0f172a"
    card = "#1e293b"
    text = "#e2e8f0"
else:
    bg = "#f8fafc"
    card = "white"
    text = "#111827"

# ===== CSS =====
st.markdown(f"""
<style>

/* ===== GLOBAL ===== */
.stApp {{
    background: {bg};
    color: {text};
}}

/* ===== HEADER ===== */
.header {{
    padding: 20px;
    border-radius: 12px;
    background: linear-gradient(135deg, #065f46, #047857);
    color: white;
}}

/* ===== CARD ===== */
.card {{
    background: {card};
    padding: 18px;
    border-radius: 12px;
    margin-top: 15px;
}}

/* ===== METRIC ===== */
.metric {{
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    color: white;
}}
.green {{ background:#16a34a; }}
.red {{ background:#dc2626; }}
.orange {{ background:#f59e0b; }}
.gray {{ background:#6b7280; }}

/* ===== DATAFRAME FIX (สำคัญ) ===== */
[data-testid="stDataFrame"] {{
    background-color: {card} !important;
    color: {text} !important;
}}

[data-testid="stDataFrame"] th {{
    background-color: {card} !important;
    color: {text} !important;
}}

[data-testid="stDataFrame"] td {{
    background-color: {card} !important;
    color: {text} !important;
}}

[data-testid="stDataFrame"] td, 
[data-testid="stDataFrame"] th {{
    border: 1px solid #334155;
}}

/* zebra row */
[data-testid="stDataFrame"] tbody tr:nth-child(even) {{
    background-color: rgba(255,255,255,0.03);
}}

</style>
""", unsafe_allow_html=True)

# ===== TIME =====
tz = pytz.timezone("Asia/Bangkok")
run_time = datetime.now(tz).strftime("%d %b %Y %H:%M")

# ===== PATH =====
MASTER_FILE = "master_rate.parquet"
MASTER_META = "master_meta.txt"
BACKUP_FOLDER = "master_backup"
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# ===== HEADER =====
st.markdown(f"""
<div class="header">
    <h2>🌍 IR Rate / CGV Dashboard</h2>
    <p>AI-powered comparison • {run_time}</p>
</div>
""", unsafe_allow_html=True)

# ===== FUNCTIONS =====
def load_master():
    if os.path.exists(MASTER_FILE):
        return pd.read_parquet(MASTER_FILE)
    return None

def get_master_time():
    if os.path.exists(MASTER_META):
        return open(MASTER_META).read()
    return "N/A"

def save_master(df):
    if os.path.exists(MASTER_FILE):
        timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
        shutil.copy(MASTER_FILE, f"{BACKUP_FOLDER}/master_{timestamp}.parquet")
    df.to_parquet(MASTER_FILE)
    with open(MASTER_META, "w") as f:
        f.write(datetime.now(tz).strftime("%d %b %Y %H:%M:%S"))

def rollback_master():
    files = sorted(os.listdir(BACKUP_FOLDER), reverse=True)
    if not files:
        return False
    shutil.copy(f"{BACKUP_FOLDER}/{files[0]}", MASTER_FILE)
    return True

# ===== VALIDATE =====
def validate(df):
    required = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE", "RATE"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {missing}")
        return False
    return True

# ===== PREP =====
def prepare(df, col):
    df["RATE"] = pd.to_numeric(df["RATE"], errors="coerce")
    return df[["COUNTRY_NAME","CHARGE_CODE","SERVICE_TYPE","RATE"]].rename(columns={"RATE": col})

# ===== COMPARE =====
def compare(m, n):
    df = pd.merge(m, n, on=["COUNTRY_NAME","CHARGE_CODE","SERVICE_TYPE"], how="outer")

    def status(r):
        if pd.isna(r["RATE_MASTER"]): return "NEW"
        if pd.isna(r["RATE_NEW"]): return "REMOVED"
        if r["RATE_MASTER"] != r["RATE_NEW"]: return "CHANGED"
        return "SAME"

    df["STATUS"] = df.apply(status, axis=1)
    df["DIFF"] = df["RATE_NEW"] - df["RATE_MASTER"]
    return df

# ===== LOAD MASTER =====
master_df = load_master()
master_time = get_master_time()

# ===== MASTER =====
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("💾 Master Data")
st.caption(f"Last updated: {master_time}")

col1, col2 = st.columns(2)
if col1.button("🔁 Rollback"):
    if rollback_master():
        st.success("Rollback success")
    else:
        st.warning("No backup")

if master_df is not None:
    st.dataframe(master_df, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ===== UPLOAD =====
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📤 Upload File")
file = st.file_uploader("Upload Excel", type=["xlsx"])
st.markdown('</div>', unsafe_allow_html=True)

if file:
    df_raw = pd.read_excel(file)

    if not validate(df_raw):
        st.stop()

    df_new = prepare(df_raw, "RATE_NEW")

    if master_df is not None:
        df_master = master_df.rename(columns={"RATE":"RATE_MASTER"})
        result = compare(df_master, df_new)

        # ===== FILTER =====
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔍 Filters")

        col1, col2 = st.columns(2)
        country = col1.multiselect("Country", result["COUNTRY_NAME"].dropna().unique())
        charge = col2.multiselect("Charge Code", result["CHARGE_CODE"].dropna().unique())

        if country:
            result = result[result["COUNTRY_NAME"].isin(country)]
        if charge:
            result = result[result["CHARGE_CODE"].isin(charge)]

        st.markdown('</div>', unsafe_allow_html=True)

        # ===== SUMMARY =====
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Summary")

        total_country = result["COUNTRY_NAME"].nunique()

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.markdown(f'<div class="metric gray"><h2>{total_country}</h2>Total Countries</div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric green"><h2>{(result.STATUS=="NEW").sum()}</h2>NEW</div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric red"><h2>{(result.STATUS=="CHANGED").sum()}</h2>CHANGED</div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="metric orange"><h2>{(result.STATUS=="REMOVED").sum()}</h2>REMOVED</div>', unsafe_allow_html=True)
        col5.markdown(f'<div class="metric gray"><h2>{(result.STATUS=="SAME").sum()}</h2>SAME</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # ===== TOP COUNTRY =====
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔥 Top Countries with Most Changes")

        top_country = (
            result[result["STATUS"]=="CHANGED"]
            .groupby("COUNTRY_NAME")
            .size()
            .reset_index(name="CHANGE_COUNT")
            .sort_values("CHANGE_COUNT", ascending=False)
            .head(10)
        )

        if not top_country.empty:
            st.dataframe(top_country, use_container_width=True)
        else:
            st.info("No changed countries")

        st.markdown('</div>', unsafe_allow_html=True)

        # ===== TABLE =====
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Compare Result")

        show_diff = st.toggle("Show differences only", True)

        if show_diff:
            display = result[result["STATUS"]!="SAME"]
        else:
            display = result

        def highlight(row):
            if st.session_state.dark_mode:
                if row["STATUS"] == "CHANGED":
                    return ["background-color:#7f1d1d"]*len(row)
                if row["STATUS"] == "NEW":
                    return ["background-color:#14532d"]*len(row)
                if row["STATUS"] == "REMOVED":
                    return ["background-color:#78350f"]*len(row)
            else:
                if row["STATUS"] == "CHANGED":
                    return ["background-color:#fee2e2"]*len(row)
                if row["STATUS"] == "NEW":
                    return ["background-color:#dcfce7"]*len(row)
                if row["STATUS"] == "REMOVED":
                    return ["background-color:#fef3c7"]*len(row)
            return [""]*len(row)

        st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result.to_excel(writer, index=False)

        st.download_button("📥 Download Excel", output.getvalue(), "compare.xlsx")

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("First upload → Save as Master")

    # ===== SAVE =====
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.button("💾 Save as Master"):
        save_master(df_new.rename(columns={"RATE_NEW":"RATE"}))
        st.success("Saved!")
    st.markdown('</div>', unsafe_allow_html=True)
