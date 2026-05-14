# OpenInsider Discord Alert Bot 📈

A simple Python scraper that monitors [OpenInsider](http://openinsider.com/) for recent insider purchases of your favorite stocks and sends automated alerts directly to your Discord channel via Webhooks.

## Features
- **Targeted Tracking:** Monitor specific stock tickers by adding them to a text file.
- **Recent Purchases Only:** Fetches only "Purchase" transactions from the last 90 days.
- **Duplicate Prevention:** Remembers previously sent alerts to prevent spamming your Discord channel.
- **100% Free Automation:** Designed to run automatically using GitHub Actions.

## Setup Instructions (GitHub Actions)

You can run this bot 24/7 for free using GitHub Actions without needing a dedicated server.

### 1. Fork this repository
Click the **Fork** button at the top right of this page to copy this project to your own GitHub account.

### 2. Configure Target Stocks

1. Open the `tickers.txt` file in your repository.

2. Edit the file to include the stock tickers you want to monitor (one ticker per line).
   NVDA
   MSFT
   AMD

3. Commit the changes.

### 3. Setup Discord Webhook
1. Go to your Discord server > Channel Settings > Integrations > Webhooks.

2. Create a new Webhook and copy the Webhook URL.

3. Go to your GitHub Repository Settings > Secrets and variables > Actions.

4. Click New repository secret.

5. Name: DISCORD_WEBHOOK_URL

6. Secret: Paste your Discord Webhook URL here.

7. Click Add secret.

### 4. Enable GitHub Actions
1. Go to the Actions tab in your repository.

2. You might see a warning saying workflows are disabled. Click I understand my workflows, go ahead and enable them.

3. The bot is scheduled to run every 2 hours automatically. You can also trigger it manually by clicking the OpenInsider Discord Alert workflow on the left, then clicking Run workflow.

## Local Installation (For testing on your PC)

If you want to run the script manually on your computer:

1. Clone the repository:
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
    cd YOUR_REPOSITORY_NAME

2. Install the required libraries:
    pip install -r requirements.txt

3. Create a `.env` file in the root directory and add your Webhook URL:
    DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/your_webhook_url"

4. Run the script:
    python scraper.py


## Disclaimer
This project is for educational and informational purposes only. It is not financial advice. Please ensure you comply with OpenInsider's terms of service regarding web scraping.