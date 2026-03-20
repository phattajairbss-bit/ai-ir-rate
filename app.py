import streamlit as st
import pandas as pd
import requests

st.title("📊 IR Rate AI Dashboard")

url = st.text_input("ใส่ URL ที่ต้องการดึงข้อมูล")

if st.button("ดึงข้อมูล"):
    try:
        response = requests.get(url)
        tables = pd.read_html(response.text)

        st.success(f"เจอ {len(tables)} tables")

        for i, table in enumerate(tables):
            st.write(f"### Table {i+1}")
            st.dataframe(table)

    except Exception as e:
        st.error(f"Error: {e}")
