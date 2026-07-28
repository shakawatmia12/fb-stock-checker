import os
import requests

# 1. Environment variables & API configuration
WORKER_KEY = os.environ.get("WORKER_KEY")
BASE_URL = "https://salva-store-snowy.vercel.app/api/stock-health"

HEADERS = {
    "Authorization": f"Bearer {WORKER_KEY}",
    "Content-Type": "application/json"
}

def extract_uid(payload):
    """
    Extracts UID from a line if it contains extra data separated by pipes/spaces
    """
    if not payload:
        return ""
    # Normalize ' | ' or spaces into single '|' and split
    cleaned = payload.replace(" | ", "|").replace(" ", "|").strip()
    return cleaned.split("|")[0]

def is_uid_live(uid):
    """
    Check Facebook UID Liveness using Graph API Redirect Logic
    Rule: Redirect URL containing '100x100' => LIVE, otherwise DIE
    """
    url = f"https://graph.facebook.com/{uid}/picture?type=normal"
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        # Check if the redirected image URL contains 100x100
        if "100x100" in response.url:
            return True
        return False
    except Exception as e:
        print(f"Error probing UID {uid}: {e}")
        return False

def run_checker():
    if not WORKER_KEY:
        print("❌ Error: WORKER_KEY is missing from Environment Variables/Secrets!")
        return

    print("🔄 Fetching pending items from Vercel API...")
    
    # Fetch pending check items
    try:
        res = requests.get(f"{BASE_URL}/pending?limit=1000", headers=HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"❌ Failed to fetch pending items. Status Code: {res.status_code}")
            return
        
        data = res.json()
        items = data.get("items", [])
        print(f"📋 Found {len(items)} item(s) to check.")

        dead_payloads = []

        # Process each item
        for item in items:
            raw_payload = item.get("payload", "")
            uid = extract_uid(raw_payload)

            if not uid:
                continue

            # Perform liveness check
            if is_uid_live(uid):
                print(f"🟢 [LIVE] UID: {uid}")
            else:
                print(f"🔴 [DEAD] UID: {uid}")
                dead_payloads.append(raw_payload)

        # Send report back to Vercel
        report_payload = {
            "payloads": dead_payloads,
            "checked": True
        }

        print("📡 Sending report back to Admin Panel...")
        report_res = requests.post(f"{BASE_URL}/report", headers=HEADERS, json=report_payload, timeout=15)
        
        if report_res.status_code == 200:
            print("✅ Successfully updated stock health report!")
        else:
            print(f"⚠️ Report submission failed. Status: {report_res.status_code}, Response: {report_res.text}")

    except Exception as e:
        print(f"❌ Unexpected error occurred: {e}")

if __name__ == "__main__":
    run_checker()
