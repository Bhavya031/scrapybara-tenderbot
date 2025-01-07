from scrapybara import Scrapybara
from playwright.async_api import async_playwright
import time
import base64
from dotenv import load_dotenv
import os

load_dotenv()

async def perform_tender_search(search_term, external_ip, scrapy):
    # Initialize the client
    client = Scrapybara(
        api_key=scrapy, timeout=200.0)
    instance = client.start(instance_type="small")
    print(f"Instance {instance.id} is running")
    cdp_url = instance.browser.start().cdp_url

    p = await async_playwright().start()
    browser = await p.chromium.connect_over_cdp(cdp_url)

    # Create a new context with proxy
    context = await browser.new_context(
        proxy={
            "server": f"http://{external_ip}:3128",
            "username": os.getenv("PROXY_USERNAME"),
            "password": os.getenv("PROXY_PASSWORD"),
        },
        ignore_https_errors=True,
    )
    page = await context.new_page()
    print("done onto next")
    await page.goto("https://tender.nprocure.com", timeout=60000)
    print("done onto next")
    time.sleep(2)

    # Use the search term provided
    response = instance.agent.act(
        cmd=f"first press esc because our focus will be stuck on search bar then Use SEARCH on the site, select ‘{
            search_term}’ under Client Name, then press search.",
        include_screenshot=True,  # Optional: include screenshot in response
        model="claude"  # Optional: specify model (defaults to claude)
    )
    print("search done")
    time.sleep(10)

    schema = {
        "tenders": [  # A list of tenders
            {
                # Sub-department name (top-right in the tender brief)
                "sub_department": "string",
                "name_of_work": "string",    # The name of the work
                "tender_id": "string",       # The tender ID
                "estimated_contract_value": "string",  # Estimated Contract Value
                "submission_deadline": "string",  # Last Date & Time for Submission
            }
        ]
    }
    response = instance.agent.scrape(
        cmd="Extract all tender details from the search results page. For each tender, gather the following information: sub-department, name of work, tender ID, estimated contract value, and submission deadline. If multiple tenders are listed, ensure you extract all of them. Scroll down to view additional tenders until you reach the “Next Page” button. Continue extracting tenders until you either find 4 or more tenders or reach the bottom of the results where fewer than 10 tenders are available. Stop extracting if there are fewer than 4 tenders on the final page.",
        schema=schema,
        include_screenshot=True,
        model="claude"
    )

    # Access the scraped data
    data = response.data  # List of dictionaries with tender details
    screenshot = response.screenshot  # Optional: Use for debugging
    print(data)
    formatted_data = "\n".join(
        f"Tender ID: {tender['tender_id']}, Name of Work: {
            tender['name_of_work']}, "
        f"Estimated Contract Value: {tender['estimated_contract_value']}, Submission Deadline: {
            tender['submission_deadline']}"
        for tender in data["tenders"]
    )

    # Command to ask the agent to write a report
    response = instance.agent.act(
        cmd=(
            f"Based on the following tender data:\n{formatted_data}\n\n"
            "Write a detailed report that identifies the suitable contractor type for each tender based on the 'Name of Work'.\n"
            "Write the report in markdown format with the following guidelines:\n"
            "Follow this format for the report:\n\n"
            "# report tittle"
            "### Tender ID: <Tender ID>\n"
            "- **Suitable Contractor**: <Type of Contractor>\n"
            "- **Explanation**:\n"
            "  <Brief explanation of the work and expertise required>\n\n"
            "Ensure the final output follows this format."
            "- Use **bold styling** for headings and key terms (e.g., **Tender ID**, **Suitable Contractor**).\n"
            "- Ensure good formatting with new lines for readability.\n\n"
            "Follow these steps when saving the file:\n"
            "Save this report as a text file in the 'Downloads' folder with the file name 'Report'. "
            "1. Clear any pre-filled text in the file name input field (e.g., 'untitled').\n"
            "2. Ensure the file name is exactly 'Report' and the format is '.txt'.\n"
            "3. Double-check that the file name does not repeat (e.g., avoid 'ReportReport.txt').\n\n"
            "4. last time make sure saved file is Report.txt"
        ),
        model="claude",
        include_screenshot=False  # Optional
    )

    # Output the agent's report
    report = response.output
    print(report)
    # Download a file from the instance
    response = instance.file.download(
        path="/home/scrapybara/Downloads/Report.txt"
    )
    downloaded_content = response.content

    # The base64-encoded content
    encoded_content = response.content

    # Decode the base64 content
    decoded_content = base64.b64decode(encoded_content)

    # Save it to a file

    # Ensure proper cleanup
    await context.close()
    await browser.close()
    await p.stop()
    instance.stop()
    return decoded_content.decode('utf-8')
# Remember to call this function with await and from an asynchronous context
