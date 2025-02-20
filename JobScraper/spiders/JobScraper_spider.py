import scrapy
import openai
import os
import time
import random

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from scrapy.selector import Selector
from scrapy.http import HtmlResponse

load_dotenv()
# Set your OpenAI API key
openai.api_key = os.getenv("OpenAI_key")

def html_to_json(html_content):
    prompt = f"""
Convert the following HTML job posting to structured JSON format with keys:
job_title, company, location, salary, job_description, requirements.

HTML:
{html_content}
"""
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

class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com", "ca.indeed.com"]
    start_urls = [
        "https://ca.indeed.com/jobs?q=junior+developer&l=montr%C3%A9al%2C+qc"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Connect to an existing Chrome instance (manually launched with --remote-debugging-port=9222)
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Attach to the running Chrome
        self.driver = webdriver.Chrome(options=chrome_options)

        # Optional stealth settings
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
        """Fetch the search results page using Selenium."""
        for url in self.start_urls:
            self.logger.info(f"Using Selenium to fetch: {url}")
            self.driver.get(url)
            time.sleep(random.uniform(3, 6))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            input("If a captcha appears, please solve it manually, then press Enter...")

            rendered_html = self.driver.page_source
            response = HtmlResponse(url=url, body=rendered_html, encoding='utf-8')
            yield from self.parse(response)

    def closed(self, reason):
        self.driver.quit()

    def parse(self, response):
        """
        Parse the main search results page:
        - Extract the unique job keys from the job title elements.
        - Build the correct detail URL.
        - Use Selenium to load each detail page and create a fake response.
        """
        sel = Selector(response)
        # Extract job keys from the data-jk attribute
        job_keys = sel.css("a.jcs-JobTitle::attr(data-jk)").getall()

        for key in job_keys:
            full_url = f"https://ca.indeed.com/viewjob?jk={key}&from=serp&vjs=3"
            self.logger.info(f"Loading job detail page: {full_url}")
            # Use Selenium to load the detail page
            self.driver.get(full_url)
            time.sleep(random.uniform(3, 6))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            detail_html = self.driver.page_source
            # Build a fake Scrapy response using the Selenium page source
            fake_response = HtmlResponse(url=full_url, body=detail_html, encoding="utf-8")
            # Process the job detail page using parse_job
            yield from self.parse_job(fake_response)

    def parse_job(self, response):
        """
        Process the job detail page (already loaded via Selenium):
        - Convert the page HTML to JSON using the GPT prompt.
        """
        # Here, response.body is already the HTML from Selenium
        job_html = response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body
        converted_data = html_to_json(job_html)

        yield {
            "converted_data": converted_data,
            "source_url": response.url
        }
