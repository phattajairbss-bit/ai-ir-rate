import re
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ======================================
# SETUP DRIVER
# ======================================
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 15)


# ======================================
# SCRAPE FUNCTION
# ======================================
def scrape_ais_rate(country_slug, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country_slug}/{plan}/all"
    driver.get(url)

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    text = driver.find_element(By.TAG_NAME, "body").text

    def safe_search(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    plan_mapping = {
        "postpaid": "sms_ir_pos",
        "prepaid": "sms_ir"
    }

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
# CHARGE CODE MAPPING
# ======================================
charge_mapping = {
    "LOCAL_CALL": ("400001021", "C_IR_MOC_VISIT"),
    "CALL_THAI": ("400001019", "C_IR_MOC_THAI"),
    "GLOBAL_CALL": ("400001020", "C_IR_MOC_3RD"),
    "RECEIVING": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI")
}


# ======================================
# COUNTRY LIST
# ======================================
countries = [
    "afghanistan",
    "albania",
    "algeria"
]

plans = ["prepaid", "postpaid"]

scraped_rows = []

for c in countries:
    for p in plans:
        print(f"Scraping {c.upper()} - {p}")
        try:
            scraped_rows.append(scrape_ais_rate(c, p))
        except Exception as e:
            print(f"Error {c}-{p}: {e}")

driver.quit()

scraped_df = pd.DataFrame(scraped_rows)


# ======================================
# TRANSFORM TO PROMOTION FORMAT
# ======================================
final_rows = []

for _, row in scraped_df.iterrows():

    for rate_type, (charge_code, charge_name) in charge_mapping.items():

        rate_value = row[rate_type]

        if rate_value is None:
            continue  # ถ้าไม่มี rate ไม่ต้องสร้าง row

        final_rows.append({
            "ITEM_NO": None,
            "OFFERING_ID": None,
            "PROMOTION_NAME": None,
            "PROMOTION_TYPE": "normal",
            "SERVICE_TYPE": row["SERVICE_TYPE"],
            "CHARGE_CODE": charge_code,
            "CHARGE_CODE_NAME": charge_name,
            "RATE": rate_value,
            "BLOCK_TYPE": "time",
            "BEGIN_TIME": None,
            "END_TIME": None,
            "USER_TYPE": None,
            "LAUNCH_DATE": None,
            "EXPIRE_DATE": None,
            "COUNTRY_CODE": None,
            "MCC_CODE": None,
            "COUNTRY_NAME": row["COUNTRY_NAME"],
            "USER_ID": "SYSTEM",
            "USER_DATE": datetime.now(),
            "UPDATE_DATE": None
        })

final_df = pd.DataFrame(final_rows)
final_df = final_df.where(pd.notnull(final_df), None)

print("\nDONE ✅")
print("Total rows:", len(final_df))
print(final_df.head())

final_df.to_excel("ais_roaming_full_format.xlsx", index=False)
