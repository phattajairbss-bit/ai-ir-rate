import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ======================================
# Streamlit Title
# ======================================
st.title("🔥 AIS IR Rate (HTML Scrape Mode)")

# ======================================
# CONFIG
# ======================================
# กำหนดประเทศและแพลนที่ต้องการ scrape
countries = ["japan", "thailand", "singapore"]
plans = ["postpaid", "prepaid"]

# Mapping column กับ charge code เดิม
charge_mapping = {
    "Local": ("400001021", "C_IR_MOC_VISIT"),
    "Call Thai": ("400001019", "C_IR_MOC_THAI"),
    "Global": ("400001020", "C_IR_MOC_3RD"),
    "Receiving": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI")
}

# ======================================
# FUNCTION: Scrape HTML จากเว็บ AIS
# ======================================
def scrape_ais_html(country, plan):
    """
    ดึง IR Rate จากหน้าเว็บ AIS โดยตรง
    fallback ใช้ html5lib ถ้า lxml ไม่ติดตั้ง
    """
    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return {"error": f"status {res.status_code}"}

        # พยายามใช้ parser lxml ก่อน
        try:
            tables = pd.read_html(res.text, flavor='lxml')
        except ImportError:
            # fallback ไป html5lib
            tables = pd.read_html(res.text, flavor='html5lib')

        if not tables:
            return {"error": "No tables found"}

        # สมมติ table แรกเป็นราคาหลัก
        df_table = tables[0]

        # เพิ่ม info country + plan
        df_table["COUNTRY_NAME"] = country.upper()
        df_table["SERVICE_TYPE"] = plan

        return df_table

    except Exception as e:
        return {"error": str(e)}

# ======================================
# FUNCTION: Transform table เป็น final DataFrame
# ======================================
def transform_df(df_table):
    final_rows = []
    for _, row in df_table.iterrows():
        for col, (code, name) in charge_mapping.items():
            if col in row and pd.notna(row[col]):
                final_rows.append({
                    "PROMOTION_TYPE": "normal",
                    "SERVICE_TYPE": row["SERVICE_TYPE"],
                    "CHARGE_CODE": code,
                    "CHARGE_CODE_NAME": name,
                    "RATE": row[col],
                    "COUNTRY_NAME": row["COUNTRY_NAME"],
                    "USER_DATE": datetime.now()
                })
    return pd.DataFrame(final_rows)

# ======================================
# Streamlit Interface
# ======================================
st.subheader("🚀 AIS IR Rate Scraper (HTML)")

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
                final_df = transform_df(df_table)
                all_rows.append(final_df)

    # แสดง log
    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    # รวมผลลัพธ์ทั้งหมด
    if all_rows:
        combined_df = pd.concat(all_rows, ignore_index=True)
        st.success(f"✅ Done: {len(combined_df)} rows")
        st.dataframe(combined_df)

        # ดาวน์โหลด CSV
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
