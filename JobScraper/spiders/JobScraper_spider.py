import scrapy
import openai
import os
import time
import random
import json

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from scrapy.selector import Selector
from scrapy.http import HtmlResponse

load_dotenv()
# Set your OpenAI API key from the environment variable
openai.api_key = os.getenv("OpenAI_key")

def html_to_json(html_content):
    prompt = f"""
Convert the following HTML job posting to strictly valid JSON with exactly the following keys:
"job_title", "company", "location", "salary", "job_description", "requirements".

The output must be a single JSON object containing only these keys and their corresponding string values extracted from the HTML.
Do not include any additional text, comments, or formatting—output only valid JSON.

For the "job_description" and "requirements" fields, provide a concise summary that captures only the essential key information (do not output the full text).

HTML:
{html_content}
"""
    max_retries = 5
    attempt = 0
    while attempt < max_retries:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that converts HTML into structured JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except openai.error.RateLimitError as e:
            wait_time = 4  # Fixed delay of 4 seconds for rate limit errors
            print(f"RateLimitError encountered. Waiting for {wait_time} seconds before retrying (attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
            attempt += 1
        except openai.error.APIError as e:
            if hasattr(e, "http_status") and e.http_status == 502:
                wait_time = 2 ** attempt  # Exponential backoff for 502 errors
                print(f"502 error encountered. Retrying in {wait_time} seconds... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                attempt += 1
            else:
                raise
    raise Exception("Max retries reached for OpenAI API.")

class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com", "ca.indeed.com"]
    start_urls = [
        "https://ca.indeed.com/jobs?q=front+end+developer&l=montr%C3%A9al%2C+qc&fromage=3&from=searchOnDesktopSerp&vjk=1778a3e399f7f618"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Connect to an existing Chrome instance (manually launched with --remote-debugging-port=9222)
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=chrome_options)

        # Stealth mode
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

    def start_requests(self):
        """Use Selenium to fetch the search results page."""
        for url in self.start_urls:
            self.logger.info(f"Using Selenium to fetch: {url}")
            self.driver.get(url)
            time.sleep(random.uniform(3, 6))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            input("If a captcha appears, please solve it manually, then press Enter...")
            rendered_html = self.driver.page_source
            # Build a fake Scrapy response so Scrapy can use it in parsing
            response = HtmlResponse(url=url, body=rendered_html, encoding='utf-8')
            yield from self.parse(response)

    def closed(self, reason):
        """Quit Selenium when spider closes."""
        self.driver.quit()

    def parse(self, response):
        """
        Parse the main search results page:
        - Extract the unique job keys from the job title elements.
        - For each job key, build the detail URL.
        - Use Selenium to load the detail page, build a fake response,
          and then pass it to parse_job.
        """
        sel = Selector(response)
        # Extract job keys from the data-jk attribute in job title links
        job_keys = sel.css("a.jcs-JobTitle::attr(data-jk)").getall()
        self.logger.info(f"Found {len(job_keys)} job keys.")

        for key in job_keys:
            # Build the detail URL using the job key
            full_url = f"https://ca.indeed.com/viewjob?jk={key}&from=serp&vjs=3"
            self.logger.info(f"Loading job detail page: {full_url}")

            # Use Selenium to load the job detail page
            self.driver.get(full_url)
            time.sleep(random.uniform(3, 6))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            detail_html = self.driver.page_source
            # Build a fake Scrapy response from Selenium’s page_source
            fake_response = HtmlResponse(url=full_url, body=detail_html, encoding="utf-8")
            yield from self.parse_job(fake_response)
        
        # Handle pagination using Selenium:
        next_page = sel.css('a[data-testid="pagination-page-next"]::attr(href)').get()
        if next_page:
            next_url = response.urljoin(next_page)
            self.logger.info(f"Moving to next page: {next_url}")
            self.driver.get(next_url)
            time.sleep(random.uniform(3, 6))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            next_html = self.driver.page_source
            next_response = HtmlResponse(url=next_url, body=next_html, encoding="utf-8")
            yield from self.parse(next_response)

    def parse_job(self, response):
        """
        Process the job detail page (loaded via Selenium):
        - Convert the HTML to JSON using the GPT prompt.
        - Parse the JSON into a Python dict (if needed) before yielding.
        """
        job_html = response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body

        # Delay before making the API call (Token rate limit)
        # time.sleep(4)

        converted_str = html_to_json(job_html)
        try:
            converted_dict = json.loads(converted_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decoding error for {response.url}: {e}")
            converted_dict = {}
        yield {
            "converted_data": converted_dict,
            "source_url": response.url
        }
