from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 10)

driver.get("http://quotes.toscrape.com")

title = driver.title
driver.implicitly_wait(0.5)
print('Title:', title)
print()

all_quotes = []
page = 1

while True:
    print(f'Page {page}')
    quotes = driver.find_elements(By.CLASS_NAME, "quote")
    if not quotes:
        break


    for quote in quotes:
        text = quote.find_element(By.CLASS_NAME, "text").text
        author = quote.find_element(By.CLASS_NAME, "author").text
        tags = quote.find_elements(By.CLASS_NAME, "tag")
        all_quotes.append({
            'text': text,
            'author': author,
            'tags': tags
        })

    next_btn = driver.find_elements(By.CSS_SELECTOR, "li.next a") 
    if not next_btn:
        break

    next_btn[0].click()
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quote")))
    page += 1

print(f"Found {len(all_quotes)} quotes")
driver.quit()
print()
print('-' * 100)
print('Done')