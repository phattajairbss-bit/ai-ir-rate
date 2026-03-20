import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ======================================
st.title("🔥 AIS IR Rate Scraper (Best Version)")

# CONFIG
countries = ["japan", "thailand", "singapore"]
plans = ["postpaid", "prepaid"]

# Mapping keywords → CHARGE_CODE + CHARGE_CODE_NAME
keyword_mapping = {
    "local": ("400001021", "C_IR_MOC_VISIT"),
    "thai": ("400001019", "C_IR_MOC_THAI"),
    "global": ("400001020", "C_IR_MOC_3RD"),
    "receiving": ("400001028", "C_IR_MTC"),
    "sms": ("400001029", "C_IR_SMS_MO_THAI"),
}

# ======================================
# FUNCTION: Scrape HTML
def scrape_ais_html(country, plan):
    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return {"error": f"status {res.status_code}"}

        try:
            tables = pd.read_html(res.text, flavor='lxml')
        except ImportError:
            tables = pd.read_html(res.text, flavor='html5lib')

        if not tables:
            return {"error": "No tables found"}

        df_table = tables[0]
        df_table["COUNTRY_NAME"] = country.upper()
        df_table["SERVICE_TYPE"] = plan

        return df_table

    except Exception as e:
        return {"error": str(e)}

# ======================================
# FUNCTION: Transform & Map CHARGE_CODE
def transform_df_auto(df_table):
    final_rows = []

    for _, row in df_table.iterrows():
        for col in df_table.columns:
            if col in ["COUNTRY_NAME", "SERVICE_TYPE"]:
                continue

            try:
                rate = float(row[col])
            except:
                continue

            col_lower = col.lower()
            code = name = None
            for kw, (c, n) in keyword_mapping.items():
                if kw in col_lower:
                    code = c
                    name = n
                    break

            if code:
                final_rows.append({
                    "PROMOTION_TYPE": "normal",
                    "SERVICE_TYPE": row["SERVICE_TYPE"],
                    "CHARGE_CODE": code,
                    "CHARGE_CODE_NAME": name,
                    "RATE": rate,
                    "COUNTRY_NAME": row["COUNTRY_NAME"],
                    "USER_DATE": datetime.now()
                })

    return pd.DataFrame(final_rows)

# ======================================
# Streamlit Interface
st.subheader("🚀 AIS IR Rate Scraper (Auto Mapping)")

if st.button("▶️ Run Scraper Now"):
    all_rows = []
    logs = []

    for c in countries:
        for p in plans:
            df_table = scrape_ais_html(c, p)
            if isinstance(df_table, dict) and "error" in df_table:
                logs.append(f"❌ {c}-{p}: {df_table['error']}")
            else:
                logs.append(f"✅ {c}-{p}")
                st.subheader(f"Columns for {c}-{p}")
                st.write(list(df_table.columns))
                final_df = transform_df_auto(df_table)
                all_rows.append(final_df)

    # Logs
    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    # Combine all
    if all_rows:
        combined_df = pd.concat(all_rows, ignore_index=True)
        st.success(f"✅ Done: {len(combined_df)} rows")
        st.dataframe(combined_df)

        # Download CSV
        csv = combined_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.error("❌ ยังไม่ได้ data → ตรวจสอบ deeper")
else:
    st.info("💡 กดปุ่ม 'Run Scraper Now' เพื่ออัปเดตข้อมูลล่าสุด")
