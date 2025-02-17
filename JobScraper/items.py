# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobItem(scrapy.Item):
    title = scrapy.Field()
    full_description = scrapy.Field()
    estimated_salary = scrapy.Field()
    location = scrapy.Field()
    company_name = scrapy.Field()
