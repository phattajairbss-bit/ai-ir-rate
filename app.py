import streamlit as st
import pandas as pd
from io import BytesIO
import os

st.set_page_config(page_title="Rate Compare Tool", layout="wide")
st.title("🌍 Rate Compare Tool (with Master)")

MASTER_FILE = "master_rate.parquet"

# ===== โหลด master =====
def load_master():
    if os.path.exists(MASTER_FILE):
        return pd.read_parquet(MASTER_FILE)
    return None

# ===== save master =====
def save_master(df):
    df.to_parquet(MASTER_FILE)

# ===== prepare =====
def prepare(df, rate_col_name):
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE", "SERVICE_TYPE"]

    df = df.copy()
    df["RATE"] = pd.to_numeric(df["RATE"], errors="coerce")

    df = df[key_cols + ["RATE"]].drop_duplicates()

    df = df.rename(columns={"RATE": rate_col_name})
    return df

# ===== compare =====
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

# ===== UI =====
master_df = load_master()

if master_df is None:
    st.warning("⚠️ No master file found → Upload initial file")

file = st.file_uploader("Upload NEW File", type=["xlsx"])

if file:
    df_new_raw = pd.read_excel(file)
    df_new = prepare(df_new_raw, "RATE_NEW")

    if master_df is not None:
        df_old = master_df.rename(columns={"RATE": "RATE_OLD"})
        result = compare(df_old, df_new)

        st.subheader("📊 Compare Result")
        st.dataframe(result, use_container_width=True)

        diff_df = result[result["STATUS"] != "SAME"]

        st.subheader("⚠️ Differences Only")
        st.dataframe(diff_df, use_container_width=True)

        st.subheader("📊 Summary")
        st.write(result["STATUS"].value_counts())

    else:
        st.info("ℹ️ First upload → will become MASTER")

    # ===== save as master =====
    if st.button("💾 Save as Master"):
        # save clean version (ใช้ RATE เดียว)
        master_save = df_new.rename(columns={"RATE_NEW": "RATE"})
        save_master(master_save)
        st.success("✅ Saved as master file")
