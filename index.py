import time
import csv
import logging
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
import random
from multiprocessing import Pool, current_process

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_driver():
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    firefox_options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    service = Service('./geckodriver-v0.35.0-win32/geckodriver.exe')
    return webdriver.Firefox(service=service, options=firefox_options)

def scrape_page(url):
    driver = create_driver()
    data = []
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 're__srp-list')))
        logging.info(f"Accessed URL: {url}, Page Title: {driver.title}")

        while True:
            try:
                listings = driver.find_elements(By.CLASS_NAME, 'js__card')
                logging.info(f"Number of listings found: {len(listings)}")

                if not listings:
                    logging.info(f'Found 0 listings on {url}')
                    break

                for listing in listings:
                    try:
                        detail_link = listing.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        logging.info(f"Accessing detail URL: {detail_link}")

                        detail_data = scrape_detail_page(detail_link)
                        if detail_data:
                            data.append(detail_data)

                    except StaleElementReferenceException:
                        logging.warning("Stale element reference encountered while accessing detail link.")
                        break

                    except Exception as e:
                        logging.error(f"Error parsing listing: {e}")

                break

            except StaleElementReferenceException:
                logging.warning("Stale element reference encountered while fetching listings. Retrying...")
                time.sleep(1)

    except TimeoutException:
        logging.error(f"Timeout while accessing page: {url}")
    except Exception as e:
        logging.error(f"Error accessing {url}: {str(e)}")
    finally:
        driver.quit()

    return data

def scrape_detail_page(url):
    driver = create_driver()
    property_details = {}
    project_info = {}

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 're__pr-specs-content'))
        )
        logging.info(f"Accessed URL: {url}, Page Title: {driver.title}")

        specs = driver.find_elements(By.CLASS_NAME, 're__pr-specs-content-item')

        for spec in specs:
            title_element = safe_find_element(spec, (By.CLASS_NAME, 're__pr-specs-content-item-title'))
            value_element = safe_find_element(spec, (By.CLASS_NAME, 're__pr-specs-content-item-value'))
            
            title = title_element.text.strip() if title_element else 'N/A'
            value = value_element.text.strip() if value_element else 'N/A'
            
            property_details[title] = value

        project_card = safe_find_element(driver, (By.CLASS_NAME, 're__project-card-info'))

        if project_card:
            project_title = safe_find_element(project_card, (By.CLASS_NAME, 're__project-title')).text.strip()
            project_info['Project Title'] = project_title

            project_status = safe_find_element(project_card, (By.CLASS_NAME, 're__long-text')).text.strip()
            project_info['Status'] = project_status

            apartments = project_card.find_elements(By.CLASS_NAME, 're__prj-card-config-value')
            if len(apartments) > 1:
                project_info['Number of Apartments'] = apartments[1].text.strip()
            if len(apartments) > 2:
                project_info['Number of Buildings'] = apartments[2].text.strip()

            developer_name = project_card.find_elements(By.CLASS_NAME, 're__long-text')
            if len(developer_name) > 1:
                project_info['Developer'] = developer_name[1].text.strip()

        short_info = driver.find_elements(By.CLASS_NAME, 're__pr-short-info-item')

        for info in short_info:
            title = safe_find_element(info, (By.CLASS_NAME, 'title')).text.strip()
            value = safe_find_element(info, (By.CLASS_NAME, 'value')).text.strip()
            property_details[title] = value

        address_element = safe_find_element(driver, (By.CLASS_NAME, 'js__pr-address'))
        if address_element:
            property_details['Project Address'] = address_element.text.strip()

        property_details.update(project_info)
        for title, value in property_details.items():
            logging.info(f"{title}: {value}")

        write_to_csv(property_details)

    except Exception as e:
        logging.error(f"Error accessing page {url}: {str(e)}")
        
    driver.quit()
    return property_details

def safe_find_element(driver, locator, retries=3):
    for attempt in range(retries):
        try:
            return driver.find_element(*locator)
        except StaleElementReferenceException:
            time.sleep(1)
        except NoSuchElementException:
            logging.warning("Element not found.")
            break
        except Exception as e:
            logging.error(f"Error finding element: {str(e)}")
            break
    return None

def write_to_csv(details):
    csv_file = 'property_listings.csv'

    file_empty = False
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            file_empty = len(list(reader)) == 0
    except FileNotFoundError:
        file_empty = True

    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if file_empty:
            writer.writerow([
                'Title', 'Price', 'Address', 'Price per m2', 'Area', 
                'Bedrooms', 'Toilets', 'Published At', 
                'Diện tích', 'Mức giá', 'Hướng nhà', 'Hướng ban công',
                'Ngày đăng', 'Ngày hết hạn', 'Loại tin', 'Mã tin',
                'Project Title', 'Status', 'Number of Apartments',
                'Number of Buildings', 'Developer', 'Project Address'
            ])

        row = [
            details.get('Project Title', ''),
            details.get('Mức giá', ''),
            details.get('Project Address', ''),
            details.get('Price per m2', ''),
            details.get('Diện tích', ''),
            details.get('Số phòng ngủ', ''),
            details.get('Số toilet', ''),
            details.get('Ngày đăng', ''),
            details.get('Diện tích', ''),
            details.get('Mức giá', ''),
            details.get('Hướng nhà', ''),
            details.get('Hướng ban công', ''),
            details.get('Ngày đăng', ''),
            details.get('Ngày hết hạn', ''),
            details.get('Loại tin', ''),
            details.get('Mã tin', ''),
            details.get('Project Title', ''),
            details.get('Status', ''),
            details.get('Number of Apartments', ''),
            details.get('Number of Buildings', ''),
            details.get('Developer', ''),
            details.get('Project Address', '')
        ]
        writer.writerow(row)

def worker(page_number):
    base_url = 'https://batdongsan.com.vn/nha-dat-ban/p'
    url = f'{base_url}{page_number}'
    logging.info(f'Process {current_process().name} scraping page {page_number}...')
    page_data = scrape_page(url)
    time.sleep(random.randint(3, 7))

num_pages = 9221

if __name__ == '__main__':
    with Pool(processes=5) as pool:  # Start with 2 processes, increase if stable
        pool.map(worker, range(1, num_pages + 1))

    logging.info('Data saved to property_listings.csv')
