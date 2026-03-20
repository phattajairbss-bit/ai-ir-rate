import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Rate Compare Tool", layout="wide")

st.title("🌍 Rate Compare Tool")

# Upload
file1 = st.file_uploader("Upload File OLD", type=["xlsx"])
file2 = st.file_uploader("Upload File NEW", type=["xlsx"])

if file1 and file2:
    try:
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)

        st.success("✅ Files uploaded")

        # ===== CONFIG =====
        key_cols = ["COUNTRY_NAME", "CHARGE_CODE"]

        # ===== CHECK COLUMN =====
        for col in key_cols + ["RATE"]:
            if col not in df1.columns or col not in df2.columns:
                st.error(f"❌ Missing column: {col}")
                st.stop()

        # ===== CLEAN + DEDUP (สำคัญ🔥) =====
        def prepare(df, rate_col_name):
            df = df[key_cols + ["RATE"]].copy()

            # แปลง RATE เป็น numeric กัน error
            df["RATE"] = pd.to_numeric(df["RATE"], errors="coerce")

            # เอา 1 row ต่อ COUNTRY + CHARGE
            df = (
                df.groupby(key_cols, as_index=False)
                  .agg({"RATE": "max"})   # 🔥 ใช้ max หรือเปลี่ยนเป็น min/mean ได้
            )

            df = df.rename(columns={"RATE": rate_col_name})
            return df

        df1 = prepare(df1, "RATE_OLD")
        df2 = prepare(df2, "RATE_NEW")

        # ===== MERGE =====
        df = pd.merge(df1, df2, on=key_cols, how="outer")

        # ===== COMPARE =====
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

        # ===== DIFF =====
        df["DIFF"] = df["RATE_NEW"] - df["RATE_OLD"]

        # ===== SORT =====
        df = df.sort_values(key_cols)

        # ===== SUMMARY =====
        st.subheader("📊 Summary")
        st.write(df["STATUS"].value_counts())

        # ===== SHOW ALL =====
        st.subheader("📊 Compare Result")
        st.dataframe(df, use_container_width=True)

        # ===== SHOW DIFF ONLY =====
        diff_df = df[df["STATUS"] != "SAME"]

        st.subheader("⚠️ Differences Only")
        st.dataframe(diff_df, use_container_width=True)

        # ===== DOWNLOAD =====
        if not df.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="ALL")
                diff_df.to_excel(writer, index=False, sheet_name="DIFF")

            st.download_button(
                "📥 Download Excel",
                data=output.getvalue(),
                file_name="rate_compare.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
