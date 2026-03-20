import streamlit as st
import pandas as pd
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

st.title("🔥 AIS IR Rate Scraper (Selenium UI)")

# ======================================
# CONFIG
# ======================================
countries = [
    "afghanistan",
    "albania",
    "algeria"
]
plans = ["prepaid", "postpaid"]

charge_mapping = {
    "LOCAL_CALL": ("400001021", "C_IR_MOC_VISIT"),
    "CALL_THAI": ("400001019", "C_IR_MOC_THAI"),
    "GLOBAL_CALL": ("400001020", "C_IR_MOC_3RD"),
    "RECEIVING": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI")
}

plan_mapping = {
    "postpaid": "sms_ir_pos",
    "prepaid": "sms_ir"
}

# ======================================
# FUNCTION: Selenium Scrape
# ======================================
def scrape_ais_rate(country_slug, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country_slug}/{plan}/all"
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    wait = WebDriverWait(driver, 15)
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    text = driver.find_element(By.TAG_NAME, "body").text

    def safe_search(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    driver.quit()

    return {
        "COUNTRY_NAME": country_slug.replace("-", " ").upper(),
        "SERVICE_TYPE": plan_mapping.get(plan, plan),
        "LOCAL_CALL": safe_search(r"Local Call\s+([\d.]+)"),
        "CALL_THAI": safe_search(r"Call to Thai\s+([\d.]+)"),
        "GLOBAL_CALL": safe_search(r"Global Call\s+([\d.]+)"),
        "RECEIVING": safe_search(r"Receiving calls\s+([\d.]+)"),
        "SMS": safe_search(r"SMS Roaming\s+([\d.]+)")
    }

# ======================================
# Streamlit button
# ======================================
if st.button("▶️ Run Scraper"):

    st.info("⏳ Scraping data... กรุณารอซักครู่")
    scraped_rows = []
    logs = []

    for c in countries:
        for p in plans:
            st.text(f"Scraping {c.upper()} - {p}")
            try:
                row = scrape_ais_rate(c, p)
                scraped_rows.append(row)
                logs.append(f"✅ {c}-{p}")
            except Exception as e:
                logs.append(f"❌ {c}-{p}: {e}")

    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    if scraped_rows:
        scraped_df = pd.DataFrame(scraped_rows)
        final_rows = []
        for _, row in scraped_df.iterrows():
            for rate_type, (charge_code, charge_name) in charge_mapping.items():
                rate_value = row[rate_type]
                if rate_value is None:
                    continue
                final_rows.append({
                    "PROMOTION_TYPE": "normal",
                    "SERVICE_TYPE": row["SERVICE_TYPE"],
                    "CHARGE_CODE": charge_code,
                    "CHARGE_CODE_NAME": charge_name,
                    "RATE": rate_value,
                    "COUNTRY_NAME": row["COUNTRY_NAME"],
                    "USER_DATE": datetime.now()
                })
        final_df = pd.DataFrame(final_rows)
        st.success(f"✅ Done: {len(final_df)} rows")
        st.dataframe(final_df)

        # CSV download
        csv = final_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.error("❌ ยังไม่ได้ data")
