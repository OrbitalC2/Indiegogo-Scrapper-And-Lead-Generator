import requests
import json

data = {
    "variables": {
        "category_main": None,
        "category_top_level": None,
        "ended_campaigns_included": False,
        "feature_variant": "none",
        "page_num": 5,
        "per_page": 12,
        "product_stage": "all",
        "project_timing": "all",
        "project_type": "campaign",
        "q": None,
        "sort": "trending",
        "tags": []
    }
}

headers = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://www.indiegogo.com",
    "referer": "https://www.indiegogo.com/explore/all?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "x-csrf-token": "juJKQhxIHmZB9K+S+doUq2+gGkXNngJE4o3mQ+vO+e1vf1kQIZMVFE7svz7bxo2T1hSbfEq4nPRIhkhcCsYO/w==",
    "cookie": "romref=dir-XXXX; romref_referer_host=; cohort=%7Cdir-XXXX; visitor_id=210b103356c499719b4e07d30f2a00f343c408bc4bfa48bb5ea4c732ebf7856e; analytics_session_id=238cb416fb63bce48e8cbd71e5ad77f296eb9aefcb9a0c4ea0d0e800f3c19d9b; accessibilityNoticeRenderedOnce=true; recent_project_ids=; _session_id=2d4cb9d50c67239e389dc34effefebad; x-spec-id=3fd2744ae9122d1021c7fa5120ab8023; _fbp=fb.1.1751310377196.234056032430069235; _ga=GA1.1.1299080479.1751310378; _gcl_au=1.1.1465586485.1751310378; _tt_enable_cookie=1; _ttp=01JZ13QAA8KVFV2HC3S5X4H84W*.tt.1; permutive-id=74299d73-25e5-41b3-9c07-9689b26c4c00; __ssid=567c02335be1ee71351d7ea34e6b13b; tcm={\"purposes\":{\"SaleOfInfo\":true,\"Analytics\":true,\"Functional\":true,\"Advertising\":true},\"timestamp\":\"2025-06-30T19:06:24.280Z\",\"confirmed\":true,\"prompted\":true,\"updated\":true}; __stripe_mid=460a7a9c-8a0a-4a8c-a243-9e16f90a67b56f5f75; __stripe_sid=f25de15d-c68c-4f6e-a6b7-e5817f04af48f304c8; newsletterDismissCount=1; newsletterLastDismiss=2025-06-30T19:06:33.619Z; ttcsid=1751310379340::gOBo5Bh4cel8GJOyLT2Q.1.1751311661789; _ga_DTZH7F2EYR=GS2.1.s1751310377$o1$g1$t1751311663$j57$l0$h1615441318; ttcsid_CC37ELBC77UFTO4NIRUG=1751310379340::gQ6TrU4ojJZSSbvs3Ddt.1.1751311694157"
}

# Exact URL from browser
url = "https://www.indiegogo.com/private_api/graph/query?operation_id=discoverables_query"

try:
    response = requests.post(
        url,
        json=data,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            result = response.json()
            print("Success!")
            print(json.dumps(result, indent=2))
        except json.JSONDecodeError:
            print(f"Response is not valid JSON: {response.text}")
    else:
        print(f"Request failed: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")