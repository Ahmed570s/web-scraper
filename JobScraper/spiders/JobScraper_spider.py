import scrapy
from JobScraper.items import JobItem
import openai
import os
import time
import random

# Import Selenium components
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from scrapy.selector import Selector
from scrapy.http import HtmlResponse

# Set your OpenAI API key
openai.api_key = os.getenv("OpenAI_key")

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
        "https://ca.indeed.com/jobs?q=software+developer&l=montr%C3%A9al%2C+qc&radius=25&vjk=048245a80f2aff0a"
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        service = Service(executable_path=r"G:\WebDriver\chromedriver-win64\chromedriver.exe")
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

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
            time.sleep(random.uniform(3, 6))
            rendered_html = self.driver.page_source
            # Create a fake Scrapy response from the Selenium HTML
            response = HtmlResponse(url=url, body=rendered_html, encoding='utf-8')
            
            # Iterate over the generator returned by self.parse(response)
            for req in self.parse(response):
                yield req

    
    def closed(self, reason):
        self.driver.quit()

    def parse(self, response):
        sel = Selector(text=response.body)
        
        for job_link in sel.css('a.jobtitle::attr(href)').getall():
            url = response.urljoin(job_link)
            yield scrapy.Request(url, callback=self.parse_job)
        
        next_page = sel.css('a[data-testid="pagination-page-next"]::attr(href)').get()
        if next_page:
            next_url = response.urljoin(next_page)
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_job(self, response):
        self.driver.get(response.url)
        time.sleep(3)
        job_html = self.driver.page_source
        structured_json = html_to_json(job_html)
        yield {
            'converted_data': structured_json,
            'source_url': response.url
        }
