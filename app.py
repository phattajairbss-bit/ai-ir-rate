import streamlit as st
import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

st.title("🌍 AI IR Rate Scraper")

def run_scraping():

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    def scrape(country, plan):
        url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
        driver.get(url)
        time.sleep(5)

        text = driver.find_element(By.TAG_NAME, "body").text

        def find(x):
            m = re.search(x, text)
            return m.group(1) if m else None

        return {
            "country": country,
            "plan": plan,
            "local_call": find(r"Local Call\s+([\d.]+)"),
            "sms": find(r"SMS Roaming\s+([\d.]+)")
        }

    rows = []
    for c in ["afghanistan", "albania"]:
        for p in ["prepaid", "postpaid"]:
            rows.append(scrape(c, p))

    driver.quit()
    return pd.DataFrame(rows)


if st.button("🚀 Run Scraping"):
    df = run_scraping()
    st.dataframe(df)

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False),
        "result.csv"
    )