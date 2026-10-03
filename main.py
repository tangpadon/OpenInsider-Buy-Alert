"""OpenInsider Discord Alert Bot.

Monitors OpenInsider for recent insider purchases of target stocks and sends
automated Discord notifications via Webhook.
"""

from datetime import datetime, timedelta
import hashlib
import os
import time
from typing import Any

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Configuration constants
HISTORY_FILE = "sent_records.txt"
LOCAL_TICKERS_FILE = "tickers.local.txt"
OPENINSIDER_BASE_URL = "http://openinsider.com/screener"
DEFAULT_TIMEOUT = 15
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def load_tickers() -> tuple[list[str], bool]:
    """Load target stock tickers with privacy priority.

    Checks configuration in the following order:
    1. Secret Gist URL via TICKERS_URL (Environment variable / Secret)
    2. Comma-separated string via TARGET_TICKERS (Env variable / Secret)
    3. Local private file via tickers.local.txt (ignored by git)

    Returns:
        tuple[list[str], bool]: A list of uppercase ticker symbols and a
        boolean flag indicating whether privacy mode is enabled.
    """
    # 1. From remote private URL (Recommended: Secret GitHub Gist raw URL)
    tickers_url = os.environ.get("TICKERS_URL", "").strip()
    if tickers_url:
        try:
            res = requests.get(tickers_url, timeout=DEFAULT_TIMEOUT)
            if res.status_code == 200:
                cleaned: list[str] = []
                for line in res.text.splitlines():
                    t = line.strip().upper()
                    if t and not t.startswith("#") and t not in cleaned:
                        cleaned.append(t)
                if cleaned:
                    return cleaned, True
            else:
                print(
                    "Warning: Failed to fetch tickers from TICKERS_URL "
                    f"(HTTP {res.status_code})."
                )
        except requests.RequestException as e:
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


def load_sent_records() -> set[str]:
    """Load previously sent record hashes to prevent duplicate alerts.

    Returns:
        set[str]: A set of processed transaction record hashes.
    """
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def hash_record(record_id: str) -> str:
    """Hash the record ID using SHA-256 to anonymize git history.

    Args:
        record_id (str): Raw string identifier for a transaction.

    Returns:
        str: 64-character hexadecimal SHA-256 hash.
    """
    return hashlib.sha256(record_id.encode("utf-8")).hexdigest()


def save_sent_record(record_hash: str) -> None:
    """Save the hashed record ID to the history file.

    Args:
        record_hash (str): The SHA-256 hash of the sent transaction.
    """
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{record_hash}\n")


def fetch_openinsider_soup(
    ticker: str, headers: dict[str, str]
) -> BeautifulSoup | None:
    """Fetch OpenInsider screener page and parse into BeautifulSoup.

    Args:
        ticker (str): Stock ticker symbol.
        headers (dict[str, str]): HTTP request headers.

    Returns:
        BeautifulSoup | None: Parsed HTML soup if successful, None otherwise.
    """
    params = {
        "s": ticker,
        "fd": "90",
        "xp": "1",
        "sortcol": "0",
        "cnt": "100",
        "page": "1",
    }
    try:
        response = requests.get(
            OPENINSIDER_BASE_URL,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.Timeout:
        print(f"Timeout error for {ticker}. The website is slow.\n")
    except requests.RequestException as e:
        print(f"Network error checking {ticker}: {e}\n")
    return None


def parse_table_records(
    soup: BeautifulSoup,
    ticker: str,
    ninety_days_ago: datetime,
) -> list[dict[str, str]]:
    """Extract valid purchase transaction records from OpenInsider HTML table.

    Args:
        soup (BeautifulSoup): Parsed HTML of the OpenInsider screener page.
        ticker (str): Target stock ticker.
        ninety_days_ago (datetime): Date threshold for 90 days ago.

    Returns:
        list[dict[str, str]]: List of extracted record dictionaries.
    """
    table = soup.find("table", {"class": "tinytable"})
    if not table or not table.find("tbody"):
        return []

    th_elements = table.find_all("th")
    header_map = {
        th.text.strip().replace("\xa0", " "): i
        for i, th in enumerate(th_elements)
    }

    def get_cell(
        cols: list[Any], col_name: str, fallback_idx: int | None = None
    ) -> str:
        if col_name in header_map and header_map[col_name] < len(cols):
            return cols[header_map[col_name]].text.strip()
        if fallback_idx is not None and fallback_idx < len(cols):
            return cols[fallback_idx].text.strip()
        return ""

    records: list[dict[str, str]] = []
    rows = table.find("tbody").find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        trade_date_str = get_cell(cols, "Trade Date", fallback_idx=2)
        row_ticker = get_cell(cols, "Ticker", fallback_idx=3) or ticker
        company_name = get_cell(cols, "Company Name")
        insider_name = get_cell(cols, "Insider Name", fallback_idx=4)
        title = get_cell(cols, "Title", fallback_idx=5)
        price = get_cell(cols, "Price", fallback_idx=7)
        qty = get_cell(cols, "Qty", fallback_idx=8)
        value = get_cell(cols, "Value", fallback_idx=11)

        # Date validation
        try:
            trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
            if trade_date < ninety_days_ago:
                continue
        except ValueError:
            pass

        records.append(
            {
                "ticker": row_ticker,
                "company_name": company_name,
                "insider_name": insider_name,
                "title": title,
                "price": price,
                "qty": qty,
                "value": value,
                "date": trade_date_str,
            }
        )

    return records


def build_discord_payload(record: dict[str, str]) -> dict[str, Any]:
    """Create a Discord Embed payload dictionary for a transaction.

    Args:
        record (dict[str, str]): Transaction details dictionary.

    Returns:
        dict[str, Any]: Discord webhook JSON payload.
    """
    row_ticker = record["ticker"]
    company_name = record["company_name"]
    insider_name = record["insider_name"]
    title = record["title"]

    embed_title = f"Insider Purchase: {row_ticker}"
    if company_name:
        embed_title += f" ({company_name})"

    insider_value = (
        f"{insider_name} ({title})" if title else insider_name
    )

    return {
        "embeds": [
            {
                "title": embed_title,
                "url": f"http://openinsider.com/screener?s={row_ticker}",
                "color": 3066993,
                "fields": [
                    {
                        "name": "Insider",
                        "value": insider_value,
                        "inline": False,
                    },
                    {
                        "name": "Price",
                        "value": record["price"],
                        "inline": True,
                    },
                    {
                        "name": "Quantity",
                        "value": record["qty"],
                        "inline": True,
                    },
                    {
                        "name": "Total Value",
                        "value": record["value"],
                        "inline": True,
                    },
                    {
                        "name": "Date",
                        "value": record["date"],
                        "inline": False,
                    },
                ],
                "footer": {"text": "Data from OpenInsider"},
            }
        ]
    }


def send_discord_alert(
    webhook_url: str,
    payload: dict[str, Any],
    log_label: str,
) -> bool:
    """Send an alert payload to Discord via Webhook with rate-limit handling.

    Args:
        webhook_url (str): The Discord Webhook URL.
        payload (dict[str, Any]): Discord webhook JSON payload.
        log_label (str): Masked or plain label for logging.

    Returns:
        bool: True if alert was sent successfully, False otherwise.
    """
    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        if res.status_code in (200, 204):
            print(f"Alert sent for {log_label}.")
            return True

        if res.status_code == 429:
            retry_after = res.json().get("retry_after", 5)
            print(
                f"Rate limited by Discord. Retrying after {retry_after}s..."
            )
            time.sleep(retry_after)
            retry_res = requests.post(webhook_url, json=payload, timeout=10)
            if retry_res.status_code in (200, 204):
                print(f"Alert sent for {log_label} on retry.")
                return True
            print(
                f"Failed to send alert for {log_label} after retry: "
                f"HTTP {retry_res.status_code}"
            )
            return False

        print(
            f"Failed to send alert for {log_label}: "
            f"HTTP {res.status_code} - {res.text}"
        )
    except requests.RequestException as err:
        print(f"Error sending webhook for {log_label}: {err}")

    return False


def check_insider() -> None:
    """Check target tickers on OpenInsider and send alerts for purchases."""
    headers = {"User-Agent": USER_AGENT}

    tickers_list, is_private = load_tickers()
    if not tickers_list:
        print("Warning: No target tickers found.")
        print(
            "Please configure TICKERS_URL (Secret Gist URL) or "
            "TARGET_TICKERS in GitHub Secrets."
        )
        print("See tickers.txt or readme.md for instructions.\n")
        return

    sent_records = load_sent_records()
    ninety_days_ago = datetime.now() - timedelta(days=90)

    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    mask_logs = is_private or is_ci

    if mask_logs:
        print(
            f"Loaded {len(tickers_list)} target tickers "
            "(Names hidden for privacy)."
        )
    else:
        print(f"Target tickers loaded: {tickers_list}")

    for idx, ticker in enumerate(tickers_list, 1):
        ticker = ticker.strip()
        log_label = (
            f"Stock [{idx}/{len(tickers_list)}]" if mask_logs else ticker
        )
        print(f"Checking data for {log_label}...")

        soup = fetch_openinsider_soup(ticker, headers)
        if not soup:
            continue

        records = parse_table_records(soup, ticker, ninety_days_ago)
        if not records:
            print(
                f"No purchase data found for {log_label} "
                "in the past 90 days.\n"
            )
            continue

        print(f"Found {len(records)} records for {log_label}. Validating...")
        has_sent_alert = False

        for rec in records:
            record_id = (
                f"{rec['ticker']}_{rec['insider_name']}_"
                f"{rec['date']}_{rec['qty']}"
            )
            record_hash = hash_record(record_id)

            if record_hash in sent_records or record_id in sent_records:
                continue

            payload = build_discord_payload(rec)

            if WEBHOOK_URL:
                success = send_discord_alert(WEBHOOK_URL, payload, log_label)
                if success:
                    save_sent_record(record_hash)
                    sent_records.add(record_hash)
                    has_sent_alert = True
                    time.sleep(1)
            else:
                print(
                    f"[No Webhook URL] Found purchase for {rec['ticker']}: "
                    f"{rec['insider_name']} ({rec['title']}) - "
                    f"{rec['qty']} @ {rec['price']} = {rec['value']}"
                )

        if has_sent_alert and WEBHOOK_URL:
            try:
                requests.post(
                    WEBHOOK_URL,
                    json={"content": SEPARATOR_LINE},
                    timeout=10,
                )
            except requests.RequestException:
                pass

        print("")
        time.sleep(5)  # Delay between tickers to prevent rate limiting


if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("Warning: DISCORD_WEBHOOK_URL is not set.")
    check_insider()