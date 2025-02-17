from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Set up Chrome options
options = Options()
options.add_argument("--headless")  # Optional: run Chrome in headless mode

# Initialize the driver.
# If ChromeDriver is in your PATH, you can simply do:
driver = webdriver.Chrome(options=options)
# Otherwise, specify the full path:
# driver = webdriver.Chrome(executable_path=r"G:\WebDriver\chromedriver-win64\chromedriver.exe", options=options)

# Open a webpage
driver.get("https://www.sheldonbrown.com/web_sample1.html")

# Print the title of the page
print(driver.title)

# Quit the driver
driver.quit()
