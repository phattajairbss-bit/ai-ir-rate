import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Rate Compare Tool", layout="wide")

st.title("🌍 Rate Compare Tool")

# Upload files
file1 = st.file_uploader("Upload File OLD", type=["xlsx"])
file2 = st.file_uploader("Upload File NEW", type=["xlsx"])

if file1 and file2:
    try:
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)

        st.success("✅ Files uploaded successfully")

        # ===== เลือก column =====
        key_cols = ["COUNTRY_NAME", "CHARGE_CODE"]

        # เช็ค column ว่ามีครบไหม
        for col in key_cols + ["RATE"]:
            if col not in df1.columns or col not in df2.columns:
                st.error(f"❌ Missing column: {col}")
                st.stop()

        # ===== เตรียม data =====
        df1 = df1[key_cols + ["RATE"]].rename(columns={"RATE": "RATE_OLD"})
        df2 = df2[key_cols + ["RATE"]].rename(columns={"RATE": "RATE_NEW"})

        # merge
        df = pd.merge(df1, df2, on=key_cols, how="outer")

        # ===== logic compare =====
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

        # ===== summary =====
        st.subheader("📊 Summary")
        summary = df["STATUS"].value_counts()
        st.write(summary)

        # ===== show all =====
        st.subheader("📊 Compare Result")
        st.dataframe(df, use_container_width=True)

        # ===== show diff =====
        diff_df = df[df["STATUS"] != "SAME"]

        st.subheader("⚠️ Differences Only")
        st.dataframe(diff_df, use_container_width=True)

        # ===== download =====
        if not diff_df.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='ALL')
                diff_df.to_excel(writer, index=False, sheet_name='DIFF')

            excel_data = output.getvalue()

            st.download_button(
                "📥 Download Excel Result",
                data=excel_data,
                file_name="rate_compare.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("✅ No differences found")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
