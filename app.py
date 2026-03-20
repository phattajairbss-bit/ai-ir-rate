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
    background: linear-gradient(to right, #fff9e6, #fff2cc);
}
.header {
    display: flex;
    align-items: center;
    justify-content: left;
    padding: 10px 40px;
    background-color: #047857;
    border-radius: 12px;
}
.main-title {
    font-size: 42px;
    font-weight: 800;
    color: white;
}
.step-box {
    display: flex;
    align-items: center;
    margin-top: 20px;
    margin-bottom: 10px;
    background-color: #065f46;
    padding: 10px 15px;
    border-radius: 12px;
}
.step {
    font-size: 34px;
    font-weight: 700;
    width: 60px;
    height: 60px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 50%;
    background-color: #ffffff;
    color: #065f46;
    margin-right: 15px;
}
.step-title {
    font-size: 22px;
    font-weight: 600;
    color: #e0f2f1;
}
.metric-box {
    background: white;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
}
.dataframe {
    background-color: white;
}
</style>
""", unsafe_allow_html=True)

# ===== HEADER =====
st.markdown(f"""
<div class="header">
    <div class="main-title">🌍 AI-powered IR Rate / CGV</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:14px; color:#065f46;">
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
    latest = files[0]
    shutil.copy(f"{BACKUP_FOLDER}/{latest}", MASTER_FILE)
    return True

def prepare(df, rate_col_name, date=None):
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE"]
    df = df.copy()
    
    # ตรวจสอบคอลัมน์ RATE
    if "RATE" not in df.columns:
        st.error("❌ คอลัมน์ 'RATE' ไม่พบในไฟล์ Excel กรุณาตรวจสอบชื่อคอลัมน์")
        return None
    
    df["RATE_NUM"] = pd.to_numeric(df["RATE"], errors="coerce")  # เก็บ numeric สำหรับคำนวณ
    df = df[key_cols + ["RATE_NUM"]].drop_duplicates()
    if date is not None:
        df[rate_col_name] = df["RATE_NUM"].apply(lambda x: f"{x} ({date})")
    else:
        df[rate_col_name] = df["RATE_NUM"]
    return df[key_cols + [rate_col_name, "RATE_NUM"]]

def compare(df_master, df_new):
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE"]
    df = pd.merge(df_master, df_new, on=key_cols, how="outer", suffixes=('_MASTER', '_NEW'))
    
    def get_status(row):
        if pd.isna(row["RATE_NUM_MASTER"]):
            return "NEW"
        elif pd.isna(row["RATE_NUM_NEW"]):
            return "REMOVED"
        elif row["RATE_NUM_MASTER"] != row["RATE_NUM_NEW"]:
            return "CHANGED"
        else:
            return "SAME"
    
    df["STATUS"] = df.apply(get_status, axis=1)
    df["DIFF"] = df["RATE_NUM_NEW"].fillna(0) - df["RATE_NUM_MASTER"].fillna(0)
    return df.sort_values(key_cols)

# ===== LOAD MASTER =====
master_df = load_master()
master_time = get_master_time()

st.markdown(f"""
<div style="font-size:14px; color:#065f46;">
💾 Master Last Updated: <b>{master_time}</b>
</div>
""", unsafe_allow_html=True)

# ===== VIEW MASTER =====
if master_df is not None:
    with st.expander("📂 View Master Data"):
        st.write(f"Total Records: {len(master_df)}")
        st.dataframe(master_df, use_container_width=True)

# ===== ROLLBACK =====
if st.button("🔁 Rollback Master"):
    if rollback_master():
        st.success("✅ Rolled back to previous version")
    else:
        st.warning("⚠️ No backup available")

# ===== STEP 1 =====
st.markdown("""
<div class="step-box">
    <div class="step">1</div>
    <div class="step-title">Upload New File</div>
</div>
""", unsafe_allow_html=True)

file = st.file_uploader("", type=["xlsx"])

# ===== MAIN =====
if file:
    df_new_raw = pd.read_excel(file)
    df_new = prepare(df_new_raw, "RATE_NEW", date=datetime.now(tz).strftime("%d %b %Y"))
    if df_new is None:
        st.stop()

    if master_df is not None:
        df_master = prepare(master_df.rename(columns={"RATE":"RATE_MASTER"}), "RATE_MASTER", date=master_time)
        result = compare(df_master, df_new)

        # ===== SUMMARY =====
        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="metric-box">🟢 NEW<br><h2>{(result["STATUS"]=="NEW").sum()}</h2></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-box">🔴 CHANGED<br><h2>{(result["STATUS"]=="CHANGED").sum()}</h2></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-box">🟠 REMOVED<br><h2>{(result["STATUS"]=="REMOVED").sum()}</h2></div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="metric-box">⚪ SAME<br><h2>{(result["STATUS"]=="SAME").sum()}</h2></div>', unsafe_allow_html=True)

        if st.checkbox("Show Differences Only", value=True):
            result_display = result[result["STATUS"] != "SAME"]
        else:
            result_display = result

        st.markdown("### 📋 Compare Result")
        def highlight(row):
            if row["STATUS"] == "CHANGED":
                return ["background-color: #ffe6e6"]*len(row)
            elif row["STATUS"] == "NEW":
                return ["background-color: #e6ffe6"]*len(row)
            elif row["STATUS"] == "REMOVED":
                return ["background-color: #fff3e6"]*len(row)
            return [""]*len(row)
        st.dataframe(result_display.style.apply(highlight, axis=1), use_container_width=True)

        # ===== STEP 2 =====
        st.markdown("""
        <div class="step-box">
            <div class="step">2</div>
            <div class="step-title">Download Compare Result</div>
        </div>
        """, unsafe_allow_html=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_cols = ["COUNTRY_NAME","CHARGE_CODE","SERVICE_TYPE","RATE_MASTER","RATE_NEW","DIFF","STATUS"]
            result.to_excel(writer, index=False, columns=export_cols)
        st.download_button("📥 Download Excel", data=output.getvalue(), file_name="rate_compare.xlsx")

    else:
        st.info("📌 First upload → Save as Master")

    # ===== STEP 3 =====
    st.markdown("""
    <div class="step-box">
        <div class="step">3</div>
        <div class="step-title">Save as Master</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("💾 Save as Master"):
        master_save = df_new.rename(columns={"RATE_NEW":"RATE"})[["COUNTRY_NAME","CHARGE_CODE","SERVICE_TYPE","RATE"]]
        save_master(master_save)
        st.success("✅ Saved as Master (Backup created)")
