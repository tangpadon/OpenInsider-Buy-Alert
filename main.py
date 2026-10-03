import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
import hashlib
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# File configurations
HISTORY_FILE = "sent_records.txt"
LOCAL_TICKERS_FILE = "tickers.local.txt"

def load_tickers():
    """
    Load target tickers with privacy priority:
    1. Secret Gist URL: TICKERS_URL (Environment variable / GitHub Secret)
    2. Comma-separated string: TARGET_TICKERS (Environment variable / GitHub Secret / .env)
    3. Local private file: tickers.local.txt (ignored by git)
    """
    # 1. From remote private URL (Recommended: Secret GitHub Gist raw URL)
    tickers_url = os.environ.get("TICKERS_URL", "").strip()
    if tickers_url:
        try:
            res = requests.get(tickers_url, timeout=15)
            if res.status_code == 200:
                cleaned = []
                for line in res.text.splitlines():
                    t = line.strip().upper()
                    if t and not t.startswith("#") and t not in cleaned:
                        cleaned.append(t)
                if cleaned:
                    return cleaned, True
            else:
                print(f"Warning: Failed to fetch tickers from TICKERS_URL (HTTP {res.status_code}).")
        except Exception as e:
            print(f"Warning: Error fetching tickers from TICKERS_URL: {e}")

    # 2. From environment variable (e.g. TARGET_TICKERS="NVDA,AMD,PLTR")
    env_tickers = os.environ.get("TARGET_TICKERS", "").strip()
    if env_tickers:
        cleaned = []
        for item in env_tickers.replace(",", "\n").splitlines():
            t = item.strip().upper()
            if t and not t.startswith("#") and t not in cleaned:
                cleaned.append(t)
        if cleaned:
            return cleaned, True

    # 3. From local ignored file (for private testing on PC)
    if os.path.exists(LOCAL_TICKERS_FILE):
        with open(LOCAL_TICKERS_FILE, "r", encoding="utf-8") as f:
            cleaned = []
            for line in f:
                t = line.strip().upper()
                if t and not t.startswith("#") and t not in cleaned:
                    cleaned.append(t)
            if cleaned:
                return cleaned, True

    return [], False

def load_sent_records():
    """Load previously sent record hashes to prevent duplicate alerts."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def hash_record(record_id: str) -> str:
    """Hash the record ID using SHA-256 to anonymize history in public git commits."""
    return hashlib.sha256(record_id.encode("utf-8")).hexdigest()

def save_sent_record(record_hash: str):
    """Save the hashed record ID to the file after successfully sending an alert."""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{record_hash}\n")

def check_insider():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    tickers_list, is_private = load_tickers()
    if not tickers_list:
        print("Warning: No target tickers found.")
        print("Please configure TICKERS_URL (Secret Gist URL) or TARGET_TICKERS in GitHub Secrets.")
        print("See tickers.txt or readme.md for instructions.\n")
        return

    sent_records = load_sent_records()
    
    # Define the 90-day threshold
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    # Hide ticker names in console logs if using private tickers or running in GitHub Actions
    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    mask_logs = is_private or is_ci
    
    if mask_logs:
        print(f"Loaded {len(tickers_list)} target tickers (Names hidden for privacy).")
    else:
        print(f"Target tickers loaded: {tickers_list}")
    
    for idx, ticker in enumerate(tickers_list, 1):
        ticker = ticker.strip()
        log_label = f"Stock [{idx}/{len(tickers_list)}]" if mask_logs else ticker
        print(f"Checking data for {log_label}...")
        
        # OpenInsider URL (fd=90 for last 90 days, xp=1 for purchases)
        url = f"http://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=90&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table', {'class': 'tinytable'})
            if not table or not table.find('tbody'):
                print(f"No purchase data found for {log_label} in the past 90 days.\n")
                continue

            # Dynamically map headers to prevent index errors
            th_elements = table.find_all('th')
            header_map = {th.text.strip().replace('\xa0', ' '): i for i, th in enumerate(th_elements)}

            def get_cell(cols, col_name, fallback_idx=None):
                if col_name in header_map and header_map[col_name] < len(cols):
                    return cols[header_map[col_name]].text.strip()
                if fallback_idx is not None and fallback_idx < len(cols):
                    return cols[fallback_idx].text.strip()
                return ""

            rows = table.find('tbody').find_all('tr')
            print(f"Found {len(rows)} records for {log_label}. Validating...")
            
            has_sent_alert = False
            
            for row in rows: 
                cols = row.find_all('td')
                if len(cols) < 8:
                    continue

                transaction_date_str = get_cell(cols, 'Trade Date', fallback_idx=2)
                row_ticker = get_cell(cols, 'Ticker', fallback_idx=3) or ticker
                company_name = get_cell(cols, 'Company Name')
                insider_name = get_cell(cols, 'Insider Name', fallback_idx=4)
                title = get_cell(cols, 'Title', fallback_idx=5) 
                price = get_cell(cols, 'Price', fallback_idx=7)
                qty = get_cell(cols, 'Qty', fallback_idx=8)
                value = get_cell(cols, 'Value', fallback_idx=11)

                # Date Validation
                try:
                    transaction_date = datetime.strptime(transaction_date_str, "%Y-%m-%d")
                    if transaction_date < ninety_days_ago:
                        continue
                except ValueError:
                    pass

                # Duplicate Validation via SHA-256 Hash
                record_id = f"{row_ticker}_{insider_name}_{transaction_date_str}_{qty}"
                record_hash = hash_record(record_id)
                if record_hash in sent_records or record_id in sent_records:
                    continue

                embed_title = f"Insider Purchase: {row_ticker}"
                if company_name:
                    embed_title += f" ({company_name})"

                # Prepare Discord payload
                data = {
                    "embeds": [{
                        "title": embed_title,
                        "url": f"http://openinsider.com/screener?s={row_ticker}",
                        "color": 3066993,
                        "fields": [
                            {"name": "Insider", "value": f"{insider_name} ({title})" if title else insider_name, "inline": False},
                            {"name": "Price", "value": price, "inline": True},
                            {"name": "Quantity", "value": qty, "inline": True},
                            {"name": "Total Value", "value": value, "inline": True},
                            {"name": "Date", "value": transaction_date_str, "inline": False}
                        ],
                        "footer": {"text": "Data from OpenInsider"}
                    }]
                }

                # Send Webhook
                if WEBHOOK_URL:
                    try:
                        res = requests.post(WEBHOOK_URL, json=data, timeout=10)
                        if res.status_code in [200, 204]:
                            print(f"Alert sent for {log_label}.")
                            save_sent_record(record_hash)
                            sent_records.add(record_hash)
                            has_sent_alert = True
                            time.sleep(1)
                        elif res.status_code == 429:
                            retry_after = res.json().get("retry_after", 5)
                            print(f"Rate limited by Discord. Retrying after {retry_after}s...")
                            time.sleep(retry_after)
                            retry_res = requests.post(WEBHOOK_URL, json=data, timeout=10)
                            if retry_res.status_code in [200, 204]:
                                print(f"Alert sent for {log_label} on retry.")
                                save_sent_record(record_hash)
                                sent_records.add(record_hash)
                                has_sent_alert = True
                                time.sleep(1)
                            else:
                                print(f"Failed to send alert for {log_label} after retry: HTTP {retry_res.status_code}")
                        else:
                            print(f"Failed to send alert for {log_label}: HTTP {res.status_code} - {res.text}")
                    except Exception as err:
                        print(f"Error sending webhook for {log_label}: {err}")
                else:
                    print(f"[No Webhook URL] Found purchase for {row_ticker}: {insider_name} ({title}) - {qty} @ {price} = {value}")
            
            # Send separator if alerts were sent
            if has_sent_alert and WEBHOOK_URL:
                try:
                    requests.post(WEBHOOK_URL, json={"content": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"}, timeout=10)
                except Exception:
                    pass
                
            print("")
            time.sleep(5) # Delay to prevent rate limiting
            
        except requests.exceptions.Timeout:
            print(f"Timeout error for {log_label}. The website is slow.\n")
        except Exception as e:
            print(f"Error checking {log_label}: {e}\n")

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("Warning: DISCORD_WEBHOOK_URL is not set.")
    check_insider()