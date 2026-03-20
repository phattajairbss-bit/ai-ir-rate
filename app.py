import streamlit as st
import pandas as pd
from io import BytesIO
import os

st.set_page_config(
    page_title="Rate Compare Tool",
    layout="wide",
    page_icon="🌍"
)

# ===== CSS =====
st.markdown("""
<style>
.big-title {
    font-size:28px !important;
    font-weight:bold;
}
.status-changed {color:red; font-weight:bold;}
.status-new {color:green; font-weight:bold;}
.status-removed {color:orange; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">🌍 Rate Compare Dashboard</p>', unsafe_allow_html=True)

MASTER_FILE = "master_rate.parquet"

# ===== function =====
def load_master():
    if os.path.exists(MASTER_FILE):
        return pd.read_parquet(MASTER_FILE)
    return None

def save_master(df):
    df.to_parquet(MASTER_FILE)

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

# ===== load master =====
master_df = load_master()

# ===== sidebar =====
st.sidebar.header("⚙️ Control Panel")

file = st.sidebar.file_uploader("Upload New File", type=["xlsx"])

show_only_diff = st.sidebar.checkbox("Show Differences Only", value=True)

# ===== main =====
if file:
    df_new_raw = pd.read_excel(file)
    df_new = prepare(df_new_raw, "RATE_NEW")

    if master_df is not None:
        df_old = master_df.rename(columns={"RATE": "RATE_OLD"})
        result = compare(df_old, df_new)

        # ===== summary =====
        st.subheader("📊 Summary")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("🟢 NEW", int((result["STATUS"] == "NEW").sum()))
        col2.metric("🔴 CHANGED", int((result["STATUS"] == "CHANGED").sum()))
        col3.metric("🟠 REMOVED", int((result["STATUS"] == "REMOVED").sum()))
        col4.metric("⚪ SAME", int((result["STATUS"] == "SAME").sum()))

        # ===== filter =====
        if show_only_diff:
            result_display = result[result["STATUS"] != "SAME"]
        else:
            result_display = result

        st.subheader("📋 Result Table")

        # ===== highlight =====
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

        # ===== download =====
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
        st.info("📌 First time → Upload and save as master")

    # ===== save master =====
    if st.button("💾 Save as Master"):
        master_save = df_new.rename(columns={"RATE_NEW": "RATE"})
        save_master(master_save)
        st.success("✅ Saved as Master")
