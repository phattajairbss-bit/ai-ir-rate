def scrape_ais_rate(country, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
    res = requests.get(url)

    # DEBUG ดู status
    print("URL:", url, "STATUS:", res.status_code)

    # หา NEXT DATA
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        res.text
    )

    if not match:
        print("❌ NO NEXT DATA:", country, plan)
        return None

    data = json.loads(match.group(1))

    # DEBUG ดูโครงสร้าง
    print("✅ FOUND DATA:", country, plan)

    text = json.dumps(data)

    def extract(label):
        m = re.search(label + r'[^0-9]*([\d.]+)', text, re.IGNORECASE)
        return m.group(1) if m else None

    result = {
        "COUNTRY_NAME": country.upper(),
        "SERVICE_TYPE": plan_mapping.get(plan, plan),
        "LOCAL_CALL": extract("Local"),
        "CALL_THAI": extract("Thai"),
        "GLOBAL_CALL": extract("Global"),
        "RECEIVING": extract("Receiving"),
        "SMS": extract("SMS")
    }

    print("DATA:", result)

    return result
