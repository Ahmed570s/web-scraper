# Indeed Job Scraper with Selenium & OpenAI

This project is an experimental scraper for Indeed job postings. It uses Selenium (attached to an already‐running Chrome session) to load job detail pages and then leverages OpenAI’s GPT‑4o‑mini model to convert the raw HTML into structured JSON.

## Features

- **Selenium Integration:**  
  Attaches to an existing Chrome instance (launched with remote debugging) to preserve cookies and bypass anti-scraping challenges (e.g., CAPTCHA).

- **OpenAI Conversion:**  
  Sends the job posting HTML to GPT‑4o‑mini using a strict prompt so that only valid JSON is returned with the keys:  
  `"job_title"`, `"company"`, `"location"`, `"salary"`, `"job_description"`, `"requirements"`.  
  For the job description and requirements, the output is a concise summary.

- **Scrapy Framework:**  
  Uses Scrapy as the overall framework for managing requests, parsing the search results, and exporting the final data to JSON.

## Prerequisites

- **Python 3.7+**
- **Google Chrome** (manually launched with remote debugging)
- **Chromedriver** (compatible with your Chrome version)
- An **environment file (.env)** containing your OpenAI API key (set as `OPENAI_API_KEY`)
- Required Python packages (see `requirements.txt`):
  - `scrapy`
  - `selenium`
  - `selenium-stealth`
  - `openai`
  - `python-dotenv`

## Setup Instructions

1. **Clone the Repository:**
```bash
git clone https://github.com/yourusername/web-scraper.git
cd web-scraper
```

2. **Create and Activate a Virtual Environment**
- On Windows:
```bash
python -m venv env
env\Scripts\activate
```
- On Linux/macOS:
```bash
python -m venv env
source env/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
    Create a file named `.env` in the project root with the following content:
```ini
OPENAI_API_KEY=your_openai_api_key_here
```

5. **Launch Chrome Manually with Remote Debugging**
    Close all Chrome instances, then run:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
```
(Ensure the path to `chrome.exe` is correct for your system. e.g., `"C:\Program Files\Google\Chrome\Application\Chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"`)

## Running the Scraper

From within the activated virtual environment (e.g., `(env) PS G:\Scrapers\web-scraper>`), run:

```bash
scrapy crawl indeed -o jobs.json
```
During the run, if a CAPTCHA appears, the script will pause with a prompt so you can solve it manually. Once solved, press Enter to continue.

## What It Does

- **Search Results:**
    The spider attaches to the existing Chrome session and loads the Indeed search results page.

- **Job Detail Extraction:
It extracts unique job keys from the search page, constructs the job detail URLs (using the format `https://ca.indeed.com/viewjob?jk=<job_key>&from=serp&vjs=3`), and uses Selenium to load each detail page.

- **HTML to JSON Conversion:
The HTML of each job detail page is sent to OpenAI’s GPT‑4o‑mini with a strict prompt, which returns a single valid JSON object. This output is parsed into a Python dictionary and exported to a JSON file.

## Known Issues & Future Improvements

- **Rate Limiting:**
    OpenAI API rate limits may be reached if too many tokens are processed in a short time. Consider adding exponential backoff or further delay adjustments.

- **Site Structure Changes:**
    CSS selectors for extracting job keys or links are specific to Indeed. If Indeed updates its HTML structure, adjust these selectors accordingly.

- **Extending to Other Sites:**
    To adapt this scraper for other job sites (e.g., LinkedIn), update:
    - `allowed_domains` and `start_urls`
    - CSS (or XPath) selectors for extracting job links/details
    - URL construction for job detail pages

## Additional Notes

- The scraper uses Selenium to load pages and preserve session cookies, which is essential for bypassing anti-scraping mechanisms.
- The output JSON file is formatted with a 2-space indent (`-s FEED_EXPORT_INDENT=2`).