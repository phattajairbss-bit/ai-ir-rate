import pandas as pd
import requests
import json
import re
from datetime import datetime

# ======================================
# CONFIG
# ======================================
countries = ["japan", "albania", "afghanistan"]
plans = ["postpaid", "prepaid"]

plan_mapping = {
    "postpaid": "sms_ir_pos",
    "prepaid": "sms_ir"
}

charge_mapping = {
    "LOCAL_CALL": ("400001021", "C_IR_MOC_VISIT"),
    "CALL_THAI": ("400001019", "C_IR_MOC_THAI"),
    "GLOBAL_CALL": ("400001020", "C_IR_MOC_3RD"),
    "RECEIVING": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI")
}


# ======================================
# 🔥 CORE FUNCTION (ไม่ใช้ selenium)
# ======================================
def scrape_ais_rate(country, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
    res = requests.get(url)

    # 👉 ดึง JSON จาก Next.js
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)

    if not match:
        return None

    data = json.loads(match.group(1))

    # 👉 หา rates จาก structure
    text = json.dumps(data)

    def extract(label):
        m = re.search(label + r'[^0-9]*([\d.]+)', text, re.IGNORECASE)
        return m.group(1) if m else None

    return {
        "COUNTRY_NAME": country.upper(),
        "SERVICE_TYPE": plan_mapping.get(plan, plan),
        "LOCAL_CALL": extract("Local Call"),
        "CALL_THAI": extract("Call to Thai"),
        "GLOBAL_CALL": extract("Global Call"),
        "RECEIVING": extract("Receiving"),
        "SMS": extract("SMS")
    }


# ======================================
# LOOP
# ======================================
rows = []

for c in countries:
    for p in plans:
        print(f"Scraping {c} - {p}")
        try:
            r = scrape_ais_rate(c, p)
            if r:
                rows.append(r)
        except Exception as e:
            print("ERROR:", e)

df = pd.DataFrame(rows)

# ======================================
# TRANSFORM (เหมือนเดิม)
# ======================================
final_rows = []

for _, row in df.iterrows():
    for rate_type, (code, name) in charge_mapping.items():

        rate = row[rate_type]

        if not rate:
            continue

        final_rows.append({
            "PROMOTION_TYPE": "normal",
            "SERVICE_TYPE": row["SERVICE_TYPE"],
            "CHARGE_CODE": code,
            "CHARGE_CODE_NAME": name,
            "RATE": rate,
            "COUNTRY_NAME": row["COUNTRY_NAME"],
            "USER_DATE": datetime.now()
        })

final_df = pd.DataFrame(final_rows)

# ======================================
# SAVE
# ======================================
final_df.to_excel("ais_ir_rate.xlsx", index=False)

print("DONE ✅", len(final_df))
