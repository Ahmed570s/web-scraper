import scrapy
from JobScraper.items import JobItem
import openai
import os
import time
import random
import undetected_chromedriver as uc

# Import Selenium components
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from scrapy.selector import Selector
from scrapy.http import HtmlResponse

# Set your OpenAI API key
openai.api_key = os.getenv("OpenAI_key")

# Set up proxy
# PROXY = "https://5yBqdV6sDrj9:WtKBkO85VFZB_region-na@superproxy.zenrows.com:1338"


def html_to_json(html_content):
    prompt = f"""
Convert the following HTML job posting to structured JSON format with keys: job_title, company, location, salary, job_description, requirements.

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
    json_output = response.choices[0].message.content.strip()
    return json_output

class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com", "ca.indeed.com"]
    start_urls = [
        "https://ca.indeed.com/jobs?q=junior+developer&l=montr%C3%A9al%2C+qc&fromage=1&radius=25&from=searchOnDesktopSerp&vjk=00894e8dc56751ae"
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # chrome_options = Options()
        chrome_options = uc.ChromeOptions()
        # For testing manual captcha solving, do not add headless mode.
        # chrome_options.add_argument("--headless")
        # chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        # chrome_options.add_argument(f"--proxy-server={PROXY}")
        # chrome_options.add_argument("--no-sandbox")
        service = Service(executable_path=r"G:\WebDriver\chromedriver-win64\chromedriver.exe")
        # self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver = uc.Chrome(options=chrome_options)

        # Apply stealth settings
        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )
    
    def start_requests(self):
        for url in self.start_urls:
            self.logger.info(f"Using Selenium to fetch: {url}")
            self.driver.get(url)
            # Random delay for page load
            time.sleep(random.uniform(3, 6))
            # Mimic human scrolling
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(2, 4))
            # Pause to allow manual captcha solving if needed
            input("If a captcha appears, please solve it manually in the browser, then press Enter to continue...")

            rendered_html = self.driver.page_source
            # Create a fake Scrapy response from the Selenium HTML
            response = HtmlResponse(url=url, body=rendered_html, encoding='utf-8')
            # Yield each request from the parse generator
            for req in self.parse(response):
                yield req

    def closed(self, reason):
        self.driver.quit()

    def parse(self, response):
        sel = Selector(text=response.body)
        # Extract job links using your CSS selector
        for job_link in sel.css('a.jobtitle::attr(href)').getall():
            url = response.urljoin(job_link)
            yield scrapy.Request(url, callback=self.parse_job)
        # Handle pagination
        #next_page = sel.css('a[data-testid="pagination-page-next"]::attr(href)').get()
        #if next_page:
            #next_url = response.urljoin(next_page)
            #yield scrapy.Request(next_url, callback=self.parse)

    def parse_job(self, response):
        self.driver.get(response.url)
        time.sleep(random.uniform(3, 6))
        # Mimic a scroll on the job page
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(2, 4))
        job_html = self.driver.page_source
        structured_json = html_to_json(job_html)
        yield {
            'converted_data': structured_json,
            'source_url': response.url
        }
