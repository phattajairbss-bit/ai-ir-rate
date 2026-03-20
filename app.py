import streamlit as st
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
import pytz
import shutil

st.set_page_config(
    page_title="CGV Rate Compare Dashboard",
    layout="wide",
    page_icon="🌍"
)

# ===== TIME =====
tz = pytz.timezone("Asia/Bangkok")
run_time = datetime.now(tz).strftime("%d %b %Y %H:%M:%S")

# ===== PATH =====
MASTER_FILE = "master_rate.parquet"
MASTER_META = "master_meta.txt"
BACKUP_FOLDER = "master_backup"

os.makedirs(BACKUP_FOLDER, exist_ok=True)

# ===== CSS =====
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}
.stApp {
    background: linear-gradient(to right, #f5f7fa, #c3cfe2);
}
.main-title {
    font-size: 34px;
    font-weight: 700;
}
.metric-box {
    background: white;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# ===== HEADER =====
st.markdown('<div class="main-title">🌍 CGV Rate Compare Dashboard</div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:14px; color:gray;">
🕒 Last Run: <b>{run_time}</b>
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
    # backup ก่อน
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

    latest_backup = files[0]
    shutil.copy(f"{BACKUP_FOLDER}/{latest_backup}", MASTER_FILE)
    return True

def prepare(df, rate_col_name):
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE"]
    df = df.copy()
    df["RATE"] = pd.to_numeric(df["RATE"], errors="coerce")
    df = df[key_cols + ["RATE"]].drop_duplicates()
    return df.rename(columns={"RATE": rate_col_name})

def compare(df_old, df_new):
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE"]
    df = pd.merge(df_old, df_new, on=key_cols, how="outer")

    def get_status(row):
        if pd.isna(row["RATE_OLD"]):
            return "NEW"
        elif pd.isna(row["RATE_NEW"]):
            return "REMOVED"
        elif row["RATE_OLD"] != row["RATE_NEW"]:
            return "CHANGED"
        else:
            return "SAME"

    df["STATUS"] = df.apply(get_status, axis=1)
    df["DIFF"] = df["RATE_NEW"] - df["RATE_OLD"]
    return df.sort_values(key_cols)

# ===== SIDEBAR =====
st.sidebar.header("⚙️ Control Panel")
file = st.sidebar.file_uploader("Upload New File", type=["xlsx"])
show_only_diff = st.sidebar.checkbox("Show Differences Only", value=True)

# ===== LOAD MASTER =====
master_df = load_master()
master_time = get_master_time()

st.markdown(f"""
<div style="font-size:14px; color:gray; margin-bottom:10px;">
💾 Master Last Updated: <b>{master_time}</b>
</div>
""", unsafe_allow_html=True)

# ===== VIEW MASTER =====
if master_df is not None:
    with st.expander("📂 View Master Data"):
        st.write(f"Total Records: {len(master_df)}")
        st.dataframe(master_df, use_container_width=True)

# ===== ROLLBACK =====
col_rb1, col_rb2 = st.columns([1,5])
with col_rb1:
    if st.button("🔁 Rollback Master"):
        success = rollback_master()
        if success:
            st.success("✅ Rolled back to previous version")
        else:
            st.warning("⚠️ No backup available")

# ===== MAIN =====
if file:
    df_new_raw = pd.read_excel(file)
    df_new = prepare(df_new_raw, "RATE_NEW")

    if master_df is not None:
        df_old = master_df.rename(columns={"RATE": "RATE_OLD"})
        result = compare(df_old, df_new)

        # ===== SUMMARY =====
        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)

        col1.markdown(f'<div class="metric-box">🟢 NEW<br><h2>{(result["STATUS"]=="NEW").sum()}</h2></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-box">🔴 CHANGED<br><h2>{(result["STATUS"]=="CHANGED").sum()}</h2></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-box">🟠 REMOVED<br><h2>{(result["STATUS"]=="REMOVED").sum()}</h2></div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="metric-box">⚪ SAME<br><h2>{(result["STATUS"]=="SAME").sum()}</h2></div>', unsafe_allow_html=True)

        # ===== FILTER =====
        if show_only_diff:
            result_display = result[result["STATUS"] != "SAME"]
        else:
            result_display = result

        st.markdown("### 📋 Compare Result")

        def highlight_status(row):
            if row["STATUS"] == "CHANGED":
                return ["background-color: #ffe6e6"] * len(row)
            elif row["STATUS"] == "NEW":
                return ["background-color: #e6ffe6"] * len(row)
            elif row["STATUS"] == "REMOVED":
                return ["background-color: #fff3e6"] * len(row)
            else:
                return [""] * len(row)

        st.dataframe(
            result_display.style.apply(highlight_status, axis=1),
            use_container_width=True
        )

        # ===== DOWNLOAD =====
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result.to_excel(writer, index=False, sheet_name="ALL")
            result[result["STATUS"] != "SAME"].to_excel(writer, index=False, sheet_name="DIFF")

        st.download_button(
            "📥 Download Excel",
            data=output.getvalue(),
            file_name="rate_compare.xlsx"
        )

    else:
        st.info("📌 First upload → Save as Master")

    # ===== SAVE MASTER =====
    if st.button("💾 Save as Master"):
        master_save = df_new.rename(columns={"RATE_NEW": "RATE"})
        save_master(master_save)
        st.success("✅ Saved as Master (Backup created)")
