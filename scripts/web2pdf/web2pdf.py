from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import pdfkit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Firefox()

def clean_html(page):
    soup = BeautifulSoup(page, 'html.parser')

    header = soup.find('header')
    if header:
        header.extract()

    footer = soup.find('footer')
    if footer:
        footer.extract()

    pictures  = soup.find_all('picture')
    for picture in pictures:
        picture.extract()

    return soup

def generate_pdf(html, out):
    pdfkit.from_string(html, out,  verbose=True)

if __name__ == '__main__':
    driver.implicitly_wait(10)
    driver.get('https://www.dnb.no/forsikring/bilforsikring')
    

    driver.find_element(By.CLASS_NAME, 'consent-accept').click()
    time.sleep(10)
    # driver.find_element(By.ID, 'hva-er-bonus-og-hvordan-fungerer-det').click()
    # driver.implicitly_wait(10)


    # driver.find_element_by_css_id("hva-er-bonus-og-hvordan-fungerer-det").click()

    # expandables = driver.find_elements(By.XPATH, "//div[@role='button']")
    # for expandable in expandables:
    #     try:
    #         # Scroll the button into view
    #         driver.execute_script("arguments[0].scrollIntoView(true);", expandable)
    #         # Click the button
    #         expandable.click()
    #     except Exception as e:
    #         print(f"Failed to click button: {e}")
            # WebDriverWait(driver, 10).until(EC.element_to_be_clickable(expandable))
            # expandable.click()
        
    # expandables = driver.find_elements(By.XPATH, "//div")
    # print(len(expandables))

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    # req = Request('https://www.dnb.no/forsikring/bilforsikring')
    # html_page = urlopen(req).read()

    # print(driver.page_source)
    cleaned_html = clean_html(driver.page_source)

    driver.quit()
    print(cleaned_html.prettify())
    generate_pdf(str(cleaned_html.prettify()),  'out.pdf')
