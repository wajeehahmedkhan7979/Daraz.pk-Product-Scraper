Daraz Multi-Page Web Scraper (Selenium + BeautifulSoup + PDF Generator)

This project automates product scraping from Daraz.pk using Selenium.
It performs a full search → scrolls each results page → extracts product data → navigates pagination until the last page → and finally generates a PDF report with product details and images.

📌 Features

Opens Daraz.pk automatically

Searches for a given keyword

Smooth auto-scroll to load lazy content

Extracts:

Product title

Product price

Product link

Product image

Auto-detects and clicks Next Page until pagination ends

Saves all scraped products into a PDF with images

Fully automated end-to-end workflow

📦 Requirements

Install required libraries:

pip install selenium webdriver-manager beautifulsoup4 requests reportlab


Ensure you have Google Chrome installed.

🚀 How It Works

Selenium launches Chrome and opens Daraz.pk

Enters a search keyword

Scrolls down gradually to load all items

Parses the loaded HTML using BeautifulSoup

Scrapes product info + downloads images

Detects the Next Page <li> element using:

li.ant-pagination-next[title='Next Page'][aria-disabled='false']


Clicks the <li> element directly using JavaScript

Repeats scrolling + scraping on every page

Stops automatically at the last page (when aria-disabled="true")

Generates a PDF (daraz_products.pdf) containing all products

🧠 Project Structure
.
├── scraper.py       # Main automation and scraping logic
├── PDFBuilder       # PDF generator class
├── README.md        # Project documentation
└── daraz_products.pdf

📄 Output PDF Example

Each product row contains:

Product image (resized)

Title (bold)

Price

Clickable product link

📝 Usage

Run the script:

python scraper.py


Edit the keyword inside:

scraper.search("Usman")


Replace "Usman" with your desired product search term.

⚠️ Notes

Daraz layout may change over time — update CSS selectors if needed.

Running with images disabled results in faster scraping.

Use headless mode for server-side execution:

scraper = DarazScraper(headless=True)

🤝 Contribution

PRs and improvements are welcome — especially for:

Speed optimizations

Better error handling

PDF styling improvements

Alternative export formats (CSV, Excel, JSON)

📜 License

This project is released under the MIT License.
