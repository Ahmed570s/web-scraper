import scrapy
import openai
import os
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from scrapy.selector import Selector
from scrapy.http import HtmlResponse

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
        # Example URL; adjust as needed
        "https://ca.indeed.com/jobs?q=junior+developer&l=montr%C3%A9al%2C+qc"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) Connect to an existing Chrome instance:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        # 2) Some optional settings
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # 3) Attach to that running Chrome
        self.driver = webdriver.Chrome(options=chrome_options)

        # 4) Optional stealth mode
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
        """Scrapy entry point: use Selenium to fetch each start_url."""
        for url in self.start_urls:
            self.logger.info(f"Using Selenium to fetch: {url}")
            self.driver.get(url)

            # Let the page load
            time.sleep(random.uniform(3, 6))

            # Optionally scroll a bit
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))

            input("If a captcha appears, please solve it manually, then press Enter...")

            rendered_html = self.driver.page_source
            # Build a fake response so Scrapy can parse it
            response = HtmlResponse(url=url, body=rendered_html, encoding='utf-8')
            yield from self.parse(response)

    def closed(self, reason):
        """Called automatically when spider finishes."""
        self.driver.quit()

    def parse(self, response):
        """
        Parse the main search results page:
        - Extract the job links
        - Yield requests for each job link
        """
        sel = Selector(response)
        # Update: Indeed often uses h2.jobTitle a
        job_links = sel.css("h2.jobTitle a::attr(href)").getall()

        for link in job_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(full_url, callback=self.parse_job)

    def parse_job(self, response):
        """Open the job detail page in the existing Selenium browser, pass to GPT."""
        self.driver.get(response.url)
        time.sleep(random.uniform(3, 6))

        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(2, 4))

        job_html = self.driver.page_source
        converted_data = html_to_json(job_html)

        yield {
            "converted_data": converted_data,
            "source_url": response.url
        }
