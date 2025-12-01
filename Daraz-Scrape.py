# ==============================================================
# Daraz multi-page scraper + PDF exporter
# Fully annotated with step-by-step comments and line-level logic
# ==============================================================

# ---------------------------
# STEP 0: Imports and libraries
# - Import all required external libraries and modules.
# - Each import is explained so you know what it's used for.
# ---------------------------
import time  # standard lib for simple delays (used cautiously)
import requests  # used to fetch product images (HTTP GET)
from io import BytesIO  # used to wrap raw image bytes for ReportLab
from bs4 import BeautifulSoup  # HTML parsing to extract structured data

# Selenium imports for browser automation:
from selenium import webdriver  # main Selenium webdriver module
from selenium.webdriver.common.by import By  # selector strategy constants (By.CSS_SELECTOR, By.ID, etc.)
from selenium.webdriver.common.keys import Keys  # keyboard key constants (e.g., Keys.ENTER)
from selenium.webdriver.chrome.service import Service  # manage chromedriver service lifecycle
from selenium.webdriver.support.ui import WebDriverWait  # explicit wait helper
from selenium.webdriver.support import expected_conditions as EC  # conditions for explicit waits

# webdriver-manager to automatically download/update ChromeDriver
from webdriver_manager.chrome import ChromeDriverManager

# ReportLab imports for PDF generation and layout:
from reportlab.platypus import (
    SimpleDocTemplate,  # high-level PDF document builder
    Paragraph,  # text block element
    Image,  # image element
    Spacer,  # vertical spacer
    Table,  # layout table
    TableStyle,  # styling for table elements
)
from reportlab.lib.pagesizes import letter  # standard page size
from reportlab.lib.styles import getSampleStyleSheet  # default paragraph styles
from reportlab.lib import colors  # color constants for table borders/fills


# ---------------------------
# STEP 1: DarazScraper class definition
# - Encapsulates browser setup, searching, scrolling, parsing, pagination
# - Allows instantiation and use in a linear script flow
# ---------------------------
class DarazScraper:
    def __init__(self, headless=False):
        """
        STEP 1.1 - Initialize WebDriver and options
        - headless: whether to run Chrome without a visible UI
        """
        chrome_options = webdriver.ChromeOptions()  # create Chrome options object

        # If headless requested, add modern headless flag (keeps browser invisible)
        if headless:
            chrome_options.add_argument("--headless=new")  # run in new headless mode

        # Add stability & performance related flags:
        chrome_options.add_argument("--disable-gpu")  # disable GPU usage (legacy flag, safe)
        chrome_options.add_argument("--start-maximized")  # maximize window to reduce responsive layout surprises
        chrome_options.add_argument("log-level=3")  # reduce chromedriver logs (info/warnings)
        # set a realistic user agent to reduce bot detection risk
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/131.0.0.0 Safari/537.36"
        )

        # STEP 1.2 - Create the webdriver instance using webdriver-manager to auto-install driver.
        # Service(ChromeDriverManager().install()) ensures the driver binary is available.
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

        # STEP 1.3 - Create an explicit wait helper
        # WebDriverWait will be used throughout to wait for elements or conditions reliably.
        self.wait = WebDriverWait(self.driver, 15)

    # ---------------------------------------------------------
    # STEP 2: Smooth scrolling
    # - Scroll the page in chunks to trigger lazy-loading and ensure all products are loaded.
    # ---------------------------------------------------------
    def slow_scroll(self, delay=0.3, chunk=800):
        """
        Scroll down the page in increments.
        - delay: pause between scroll increments (seconds)
        - chunk: pixel step size for each scroll
        Logic:
        1. Query the current full document height.
        2. Scroll from top to bottom in fixed increments.
        3. Stop when the incremental position reaches or exceeds the computed document height.
        """
        # STEP 2.1 - Get the current height of the document (total scrollable height)
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        # STEP 2.2 - Start scrolling from position 0
        current_position = 0

        # STEP 2.3 - Loop until we reach the bottom (or no more growth)
        while True:
            # Execute JS to set window scroll to the current position
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            # Wait briefly to allow lazy-loaded content to appear
            time.sleep(delay)
            # Move the current position forward by the defined chunk
            current_position += chunk

            # Recompute the document height to detect if new content extended the page
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # If we've reached or exceeded the new height, break the loop (we're at bottom)
            if current_position >= new_height:
                break

            # Update last_height for completeness (not strictly necessary here, but keeps logic clear)
            last_height = new_height

    # ---------------------------------------------------------
    # STEP 3: Search
    # - Open Daraz homepage and perform a search for the given query.
    # - Uses explicit waits to avoid racing the page load.
    # ---------------------------------------------------------
    def search(self, query):
        """
        Steps:
        1. Navigate to daraz.pk homepage
        2. Wait for the search input to appear
        3. Type the query and press ENTER
        4. Call slow_scroll to let results start loading
        """
        # STEP 3.1 - Navigate browser to Daraz home
        self.driver.get("https://www.daraz.pk/")

        # STEP 3.2 - Use explicit wait to find the search input by id "q"
        try:
            search_box = self.wait.until(EC.presence_of_element_located((By.ID, "q")))
            # If found, clear any pre-filled content
            search_box.clear()
            # Type the query string into the input
            search_box.send_keys(query)
            # Press ENTER to submit the search
            search_box.send_keys(Keys.ENTER)
        except Exception:
            # If anything fails, print helpful message (do not crash)
            print("Search bar not found!")

        # STEP 3.3 - Give the page a bit of time to load results and perform an initial scroll
        self.slow_scroll()

    # ---------------------------------------------------------
    # STEP 4: Parse products on current page
    # - Parse HTML using BeautifulSoup for stable parsing and simpler extraction.
    # ---------------------------------------------------------
    def parse_products(self):
        """
        Returns a list of product dicts from the current page.
        Each dict: { title, price, link, img_bytes }
        Logic:
        1. Parse page_source with BeautifulSoup
        2. Select product containers by CSS selector (updateable)
        3. Extract title, price, link, and image bytes (download)
        """
        # STEP 4.1 - Build BeautifulSoup object from current DOM HTML
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        # STEP 4.2 - Select product container elements.
        # NOTE: Daraz uses generated class names and these may change; update this selector if needed.
        # <<< MODIFY HERE IF DARAZ CHANGES PRODUCT CONTAINER CLASS >>>
        products = soup.select(".Bm3ON")

        results = []  # STEP 4.3 - Prepare a results list to accumulate product dicts

        # STEP 4.4 - Iterate over each raw product element and extract structured fields
        for p in products:
            # Extract title safely - if missing, fallback to "N/A"
            try:
                title = p.select_one(".RfADt").text.strip()
            except:
                title = "N/A"

            # Extract price safely - if missing, fallback to "N/A"
            try:
                price = p.select_one(".ooOxS").text.strip()
            except:
                price = "N/A"

            # Extract product link (href). Normalize scheme if necessary.
            try:
                link = p.find("a")["href"]
                # If link is protocol-relative (starts with //), prepend https:
                if link.startswith("//"):
                    link = "https:" + link
            except:
                link = None

            # Extract image URL and download the bytes for embedding in PDF.
            try:
                img_url = p.find("img")["src"]
                img_bytes = requests.get(img_url).content if img_url else None
            except:
                # If download fails, set None. PDFs will use placeholders.
                img_bytes = None

            # STEP 4.5 - Append the structured product entry to results
            results.append(
                {
                    "title": title,
                    "price": price,
                    "link": link,
                    "img_bytes": img_bytes,
                }
            )

        # STEP 4.6 - Return the list of product dicts for this page
        return results

    # ---------------------------------------------------------
    # STEP 5: Pagination logic — find and click next page
    # - Locate the <li> that represents the "Next Page" button,
    # - Ensure aria-disabled is "false", then click its child clickable element.
    # ---------------------------------------------------------
    def click_next_page(self):
        """
        Steps:
        1. Wait for the 'li' container that represents the next page control
           using a specific CSS selector that requires:
             - class 'ant-pagination-next'
             - title attribute equal to 'Next Page'
             - aria-disabled attribute equal to 'false'
        2. Execute a JS click on the li element (which triggers the child button)
           - This avoids reliance on the internal button's class or tag.
        3. Return True if navigation succeeded, False otherwise.
        """
        try:
            # STEP 5.1 - Wait for the next-page <li> that is enabled (aria-disabled='false')
            next_li = self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "li.ant-pagination-next[title='Next Page'][aria-disabled='false']",
                    )
                )
            )

            # STEP 5.2 - Click using JavaScript on the found <li> element
            # We intentionally click the container instead of a specific inner button
            # because inner tags/classes can be volatile. Clicking the container lets the browser
            # dispatch the event to the actual control inside.
            self.driver.execute_script("arguments[0].click();", next_li)

            # STEP 5.3 - Small delay to allow new page to load and render
            time.sleep(2)
            return True

        except Exception:
            # STEP 5.4 - If wait times out or an exception occurs, interpret as no next page
            print("No Next Page button found or disabled. Reached last page.")
            return False

    # ---------------------------------------------------------
    # STEP 6: Loop pages: scroll, parse, click next until the last page
    # - This orchestrates the per-page steps into a full crawl over pagination.
    # ---------------------------------------------------------
    def scrape_all_pages(self):
        """
        Returns a combined list of product dicts from all pages.
        Loop structure:
        1. On each iteration: scroll, parse products, extend master list
        2. Attempt to click 'Next'. If click fails, break the loop (last page).
        """
        all_results = []  # master accumulator for all pages

        while True:
            # STEP 6.1 - Informational log (helps debugging in console)
            print("Scraping current page...")

            # STEP 6.2 - Make sure page loaded content by scrolling slowly
            self.slow_scroll()

            # STEP 6.3 - Parse the products available on this page
            page_items = self.parse_products()

            # STEP 6.4 - Extend the global list with this page's items
            all_results.extend(page_items)

            # STEP 6.5 - Attempt to navigate to the next page
            print("Trying next page...")
            has_next = self.click_next_page()

            # STEP 6.6 - If there is no next page, exit the loop
            if not has_next:
                break

        # STEP 6.7 - Return the complete aggregated results after finishing pagination
        return all_results

    # ---------------------------------------------------------
    # STEP 7: Clean shutdown
    # - Close the webdriver to free resources.
    # ---------------------------------------------------------
    def close(self):
        # Quit the webdriver cleanly (closes all windows and stops background process)
        self.driver.quit()


# ---------------------------
# STEP 8: PDF Builder class
# - Responsible for turning scraped data into a nicely formatted PDF
# ---------------------------
class PDFBuilder:
    def __init__(self, filename="daraz_products.pdf"):
        """
        STEP 8.1 - Initialize PDF document builder
        - filename: output file path for the generated PDF
        """
        self.file = filename
        # Create a SimpleDocTemplate object that manages the PDF build lifecycle
        self.doc = SimpleDocTemplate(self.file, pagesize=letter)
        # Grab the sample styles (for Paragraph formatting)
        self.styles = getSampleStyleSheet()
        # Elements array will hold flowable elements (Paragraph, Image, Table, etc.)
        self.elements = []

    # ---------------------------------------------------------
    # STEP 9: Add a product entry to the PDF
    # - Builds a two-column table row: [image | details]
    # - Uses fallback placeholders if image or link is missing.
    # ---------------------------------------------------------
    def add_product(self, item):
        """
        Steps to add one product:
        1. Convert raw image bytes to ReportLab Image if available
        2. Create Paragraphs for title and price
        3. Optionally add a clickable link Paragraph
        4. Compose a Table row [image, [title, price, link]]
        5. Append to elements list (and spacer)
        """
        # STEP 9.1 - Build left column: image or placeholder text
        if item["img_bytes"]:
            try:
                # Wrap bytes in BytesIO so ReportLab can read it as an image file
                img = Image(BytesIO(item["img_bytes"]))
                # Restrict display size to keep table consistent
                img._restrictSize(120, 120)
                left_col = img
            except:
                # If ReportLab can't process image bytes, use a placeholder Paragraph
                left_col = Paragraph("Image error", self.styles["Normal"])
        else:
            # No image bytes were found, use placeholder text
            left_col = Paragraph("No Image", self.styles["Normal"])

        # STEP 9.2 - Build right column contents: title and price paragraphs
        right = [
            Paragraph(f"<b>{item['title']}</b>", self.styles["Normal"]),  # bold title
            Paragraph(f"Price: {item['price']}", self.styles["Normal"]),  # price info
        ]

        # STEP 9.3 - Add link paragraph if link exists; else fallback text
        if item["link"]:
            right.append(
                Paragraph(
                    f"<link href='{item['link']}' color='blue'><u>View Product</u></link>",
                    self.styles["Normal"],
                )
            )
        else:
            right.append(Paragraph("No product link available", self.styles["Normal"]))

        # STEP 9.4 - Place left_col and right (list of paragraphs) into a single-row Table
        table = Table([[left_col, right]], colWidths=[130, 400])
        # STEP 9.5 - Apply simple table styling for border, padding, and alignment
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),  # top-align cells
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),  # outer border
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),  # inner cell grid
                    ("PADDING", (0, 0), (-1, -1), 6),  # uniform padding
                ]
            )
        )

        # STEP 9.6 - Append the table row and a spacer to the elements list
        self.elements.append(table)
        self.elements.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # STEP 10: Save PDF file to disk
    # - Build the document using the accumulated flowables
    # ---------------------------------------------------------
    def save(self):
        # This triggers ReportLab to compose pages and write the PDF to self.file
        self.doc.build(self.elements)
        print(f"PDF saved as {self.file}")


# ---------------------------
# STEP 11: Main execution flow
# - Orchestrates the scraper and PDF generation end-to-end
# ---------------------------
if __name__ == "__main__":
    # STEP 11.1 - Instantiate the scraper (headless=False for visible browser during development)
    scraper = DarazScraper(headless=False)

    # STEP 11.2 - Perform search on Daraz for your keyword
    # Replace "Usman" with any keyword you want to crawl
    scraper.search("Usman")  # change keyword as needed

    # STEP 11.3 - Run the full pagination scrape (scroll → parse → next) across all pages
    all_data = scraper.scrape_all_pages()

    # STEP 11.4 - Gracefully close the WebDriver (important to free resources)
    scraper.close()

    # STEP 11.5 - Instantiate the PDF builder and populate it with scraped data
    builder = PDFBuilder("daraz_products.pdf")
    for item in all_data:
        builder.add_product(item)

    # STEP 11.6 - Save the final PDF to disk
    builder.save()
