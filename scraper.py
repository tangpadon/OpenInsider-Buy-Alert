import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# File configurations
HISTORY_FILE = "sent_records.txt"
TICKERS_FILE = "tickers.txt"

def load_tickers():
    """Load target tickers from the text file."""
    if not os.path.exists(TICKERS_FILE):
        print(f"Warning: File {TICKERS_FILE} not found. Using default tickers.")
        return ["ADMA", "SOFI"]
    
    with open(TICKERS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_sent_records():
    """Load previously sent records to prevent duplicate alerts."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_sent_record(record_id):
    """Save the record ID to the file after successfully sending an alert."""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{record_id}\n")

def check_insider():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    tickers_list = load_tickers()
    sent_records = load_sent_records()
    
    # Define the 90-day threshold
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    print(f"Target tickers loaded: {tickers_list}")
    
    for ticker in tickers_list:
        ticker = ticker.strip()
        print(f"Checking data for {ticker}...")
        
        # OpenInsider URL (fd=90 for last 90 days, xp=1 for purchases)
        url = f"http://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=90&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table', {'class': 'tinytable'})
            if not table:
                print(f"No purchase data found for {ticker} in the past 90 days.\n")
                continue

            rows = table.find('tbody').find_all('tr')
            print(f"Found {len(rows)} records for {ticker}. Validating...")
            
            has_sent_alert = False
            
            for row in rows[:3]: 
                cols = row.find_all('td')
                if len(cols) < 10: continue

                transaction_date_str = cols[2].text.strip()
                row_ticker = cols[3].text.strip()
                insider_name = cols[4].text.strip()
                title = cols[5].text.strip() 
                price = cols[7].text.strip()
                qty = cols[8].text.strip()
                value = cols[11].text.strip()

                # Date Validation
                try:
                    transaction_date = datetime.strptime(transaction_date_str, "%Y-%m-%d")
                    if transaction_date < ninety_days_ago:
                        continue
                except ValueError:
                    pass

                # Duplicate Validation
                record_id = f"{row_ticker}_{insider_name}_{transaction_date_str}_{qty}"
                if record_id in sent_records:
                    continue

                # Prepare Discord payload
                data = {
                    "embeds": [{
                        "title": f"Insider Purchase: {row_ticker}",
                        "url": f"http://openinsider.com/screener?s={row_ticker}",
                        "color": 3066993,
                        "fields": [
                            {"name": "Insider", "value": f"{insider_name} ({title})", "inline": False},
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
                    requests.post(WEBHOOK_URL, json=data)
                    print(f"Alert sent for {row_ticker}.")
                    
                    save_sent_record(record_id)
                    sent_records.add(record_id)
                    has_sent_alert = True
                    time.sleep(1)
                else:
                    print("Error: Webhook URL is missing.")
            
            # Send separator if alerts were sent
            if has_sent_alert and WEBHOOK_URL:
                requests.post(WEBHOOK_URL, json={"content": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"})
                
            print("")
            time.sleep(5) # Delay to prevent rate limiting
            
        except requests.exceptions.Timeout:
            print(f"Timeout error for {ticker}. The website is slow.\n")
        except Exception as e:
            print(f"Error checking {ticker}: {e}\n")

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("Warning: DISCORD_WEBHOOK_URL is not set.")
    check_insider()