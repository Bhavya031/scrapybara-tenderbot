# Tender Search Bot

This Telegram bot automates the process of searching for tenders on the India-specific site [https://tender.nprocure.com](https://tender.nprocure.com). It uses a proxy server and a virtual machine to scrape tender data, catering specifically to clients who need access to tenders restricted to Indian IP addresses.

## How It Works

1. **Token Authentication**:

   - The user starts by providing a Scrapybara token, which is essential for accessing the scraping services.

2. **Proxy Server Initialization**:

   - The bot checks if the proxy server is already running. If not, it initiates a proxy server to ensure the requests appear to originate from India, as the tender site is restricted to Indian IPs.

3. **Virtual Machine Startup**:

   - Concurrently, the bot starts a Scrapybara VM if it isn't already operational.

4. **Site Access via Proxy**:

   - The bot accesses [https://tender.nprocure.com](https://tender.nprocure.com) through the proxy server, making it accessible even from outside India.

5. **Client-Specific Search**:

   - Users can input a client name for which the bot searches on the tender site. While advanced search options are planned, the current implementation only searches based on the client name.

6. **Tender Data Scraping**:

   - The bot deploys a scraping agent to extract information about the first four tenders to conserve Scrapybara credits and minimize system load.

7. **Report Generation**:

   - After scraping, an AI agent composes a report suggesting actionable insights for contracting opportunities. This report is initially saved in ODT format but is converted to TXT as specified.

8. **Report Download and Conversion**:

   - The report, written in Markdown, is then converted into a PDF with professional formatting. Example: [output.pdf](https://github.com/Bhavya031/scrapybara-tenderbot/blob/main/output.pdf)

9. **Delivery**:
   - Finally, the PDF report is sent to the user on Telegram. In the current demo version, only text is sent due to previous iterations and limitations on Scrapybara credits.

## Usage

To use this bot:

- Send `/start` followed by your Scrapybara token.
- Follow the prompts to input the client name you wish to search for.
- Receive the tender report directly in your Telegram chat.

## Video Demonstration
[Watch the video](https://drive.google.com/file/d/1H5GpZY7nSa_JsIyfmZzkd-kNZt5EtLKK/view?usp=sharing)

If you wish to see the complete capabilities or use the bot for a live demo, please contact me at [bhavyapatel21999@gmail.com](mailto:bhavyapatel21999@gmail.com) or [https://x.com/Bhavya037](https://x.com/Bhavya037).

Thank you for your interest in our Tender Search Bot!
