# OpenInsider Discord Alert Bot 📈

A simple, serverless Python bot that monitors [OpenInsider](http://openinsider.com/) for recent insider purchases of your favorite stocks and sends automated, rich alerts directly to your Discord channel via Webhooks.

Designed to run **100% free 24/7** using GitHub Actions, with **built-in privacy protection** so you can safely host it on a public repository without revealing your watchlist to anyone.

---

## ✨ Features

- **🔒 Built-in Privacy Protection:**
  - **Secret Watchlist:** Keep your monitored stocks private using GitHub Secrets (`TARGET_TICKERS`).
  - **Hashed History:** Processed alerts are stored as SHA-256 hashes in `sent_records.txt`, preventing public commits from exposing what stocks or insiders were alerted.
  - **Masked Logs:** GitHub Actions execution logs mask ticker names (e.g. `Stock [1/5]...`) to prevent public log leaks.
- **🎯 Private Tracking:** Configure tickers securely via GitHub Secrets (`TARGET_TICKERS`) or local `.env` / `tickers.local.txt`.
- **🕒 Recent Purchases Only:** Automatically tracks Form 4 "Purchase" transactions filed within the last 90 days.
- **🛡️ Duplicate Prevention:** Remembers previously sent transactions to ensure zero spam.
- **⚡ Dynamic Column Parsing:** Automatically maps OpenInsider table headers dynamically to prevent format breakages.
- **💸 100% Free Automation:** Runs automatically on GitHub Actions without needing a dedicated VPS or server.

---

## 🚀 Setup Instructions (GitHub Actions)

You can run this bot 24/7 for free using GitHub Actions without needing a dedicated server.

### 1. Fork this repository
Click the **Fork** button at the top right of this repository to copy it to your own GitHub account.

---

### 2. Configure Discord Webhook & Private Watchlist (Secrets)

To keep your watchlist private while maintaining a public repository:

1. **Get Discord Webhook URL:**
   - In Discord, go to **Server Settings** > **Integrations** > **Webhooks**.
   - Click **New Webhook**, select the target channel, and click **Copy Webhook URL**.

2. **Add Secrets to your GitHub Repository:**
   - Go to your forked GitHub repository > **Settings** > **Secrets and variables** > **Actions**.
   - Click **New repository secret** and add:
     - **Name:** `DISCORD_WEBHOOK_URL`
     - **Secret:** *(Paste your Discord Webhook URL)*
   - Click **New repository secret** again to add your private watchlist:
     - **Name:** `TARGET_TICKERS`
     - **Secret:** Comma-separated list of stock tickers you want to monitor:
       ```text
       NVDA,AMD,PLTR,TSLA,SMCI
       ```

> [!TIP]
> **Why this keeps your stocks private:**
> - `tickers.txt` is strictly an instructional template and is **never** read by the bot, preventing accidental commits of private tickers.
> - The bot reads `TARGET_TICKERS` securely from your GitHub Secrets.
> - GitHub automatically hides Secrets from visitors and masks console logs.

---

### 3. Enable GitHub Actions
1. Go to the **Actions** tab in your repository.
2. If prompted, click **"I understand my workflows, go ahead and enable them"**.
3. The bot is scheduled to run automatically **every 2 hours**.
4. You can test it immediately by clicking **OpenInsider Discord Alert** on the left menu, then clicking **Run workflow**.

---

## 💻 Local Installation (Testing on your PC)

If you want to run or test the script on your local computer:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/OpenInsider-Buy-Alert.git
   cd OpenInsider-Buy-Alert
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment (Private):**
   Create a `.env` file in the project directory (this file is already in `.gitignore` and will never be committed):
   ```env
   DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/your_webhook_url"
   TARGET_TICKERS="NVDA,AMD,PLTR"
   ```
   *(Alternatively, you can create a `tickers.local.txt` file with one ticker per line, which is also ignored by git).*

4. **Run the bot:**
   ```bash
   python main.py
   ```

---

## 🔒 How Privacy Protection Works (Under the Hood)

If you keep your GitHub repository **Public**, this bot protects your privacy through 3 layers:

1. **Secret Ticker Input:** The bot checks the `TARGET_TICKERS` environment variable before reading any text files. Your watchlist stays in GitHub Secrets, which only you can view or modify.
2. **SHA-256 Hashed History:** When an alert is sent, the bot commits a SHA-256 hash (e.g. `a3b89f02...`) to `sent_records.txt`. Anyone inspecting the commit history on GitHub will only see random hashes, not your tickers or insider names.
3. **Log Masking:** GitHub Actions console outputs are public on open-source repositories. When running in CI or with private tickers, the bot masks ticker names in standard logs (`Checking data for Stock [1/5]...`) to avoid revealing watched symbols.

---

## ⚠️ Disclaimer
This project is for educational and informational purposes only. It is not financial advice. Please ensure you comply with OpenInsider's terms of service regarding web scraping.