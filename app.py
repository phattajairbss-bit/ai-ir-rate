import streamlit as st
import pandas as pd

st.title("🌍 Rate Compare Tool")

# Upload files
file1 = st.file_uploader("Upload File OLD", type=["xlsx"])
file2 = st.file_uploader("Upload File NEW", type=["xlsx"])

if file1 and file2:
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)

    # เลือก column ที่ใช้ compare
    key_cols = ["COUNTRY_NAME", "CHARGE_CODE"]
    
    df1 = df1[key_cols + ["RATE"]].rename(columns={"RATE": "RATE_OLD"})
    df2 = df2[key_cols + ["RATE"]].rename(columns={"RATE": "RATE_NEW"})

    # merge
    df = pd.merge(df1, df2, on=key_cols, how="outer")

    # detect status
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

    # show result
    st.subheader("📊 Compare Result")
    st.dataframe(df)

    # filter diff only
    diff_df = df[df["STATUS"] != "SAME"]

    st.subheader("⚠️ Differences Only")
    st.dataframe(diff_df)

    # download
    st.download_button(
        "📥 Download Result",
        diff_df.to_excel(index=False),
        file_name="rate_diff.xlsx"
    )
