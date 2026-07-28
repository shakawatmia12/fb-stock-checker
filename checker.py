import os
import requests

WORKER_KEY = os.environ.get("WORKER_KEY")
BASE_URL = "https://salva-store-snowy.vercel.app/api/stock-health"

headers = {
    "Authorization": f"Bearer {WORKER_KEY}",
    "Content-Type": "application/json"
}

def run_check():
    if not WORKER_KEY:
        print("Error: WORKER_KEY secret is missing!")
        return

    # 1. Fetch pending checkable items
    try:
        res = requests.get(f"{BASE_URL}/pending?limit=1000", headers=headers)
        if res.status_code != 200:
            print(f"Failed to fetch pending items. Status: {res.status_code}")
            return
        
        data = res.json()
        items = data.get("items", [])
        print(f"Found {len(items)} items to check.")

        dead_payloads = []

        # 2. Check Facebook Liveness for each item
        for item in items:
            payload = item.get("payload") # Facebook UID or Link
            if payload:
                # Basic Facebook URL check
                fb_url = f"https://www.facebook.com/{payload}" if not payload.startswith("http") else payload
                check_res = requests.get(fb_url, headers={"User-Agent": "Mozilla/5.0"})
                
                # If page returns 404 or redirected to login/error, mark as dead
                if check_res.status_code in [404, 400] or "login" in check_res.url:
                    dead_payloads.append(payload)

        # 3. Report results back to Vercel
        report_data = {
            "payloads": dead_payloads,
            "checked": True
        }
        
        report_res = requests.post(f"{BASE_URL}/report", headers=headers, json=report_data)
        print(f"Report status: {report_res.status_code}, Response: {report_res.text}")

    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    run_check()
