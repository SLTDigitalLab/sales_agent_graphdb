import time
import csv
import re
import os
import sys
import hashlib
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- 1. SETUP PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__)) 
project_root = os.path.dirname(script_dir)              

DATA_DIR = os.path.join(project_root, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

CSV_PATH = os.path.join(DATA_DIR, 'products.csv')

# --- 2. LOGGER ---
try:
    from src.utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

BASE_DOMAIN = "https://lifestore.lk"

def setup_driver():
    """Setup invisible Chrome browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_price(price_str):
    """Extracts the last numeric price found in a string (ignores old prices)."""
    if not price_str: return 0.0
    
    # Find all numeric patterns (e.g., 12,890.00 or 5000)
    prices = re.findall(r'[\d,.]+\d', str(price_str))
    
    if not prices:
        return 0.0
        
    # Take the LAST price found 
    last_price = prices[-1]
    
    # Remove commas/non-numeric chars and convert to float
    clean = re.sub(r'[^\d.]', '', last_price)
    try:
        return float(clean)
    except ValueError:
        return 0.0

def discover_categories(driver, base_urls):
    discovered = []
    seen_urls = set()
    for base_url in base_urls:
        if not base_url: continue
        logger.info(f"Discovering categories from {base_url}...")
        try:
            driver.get(base_url)
            time.sleep(3) 
            elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/categories/')]")
            for elem in elements:
                try:
                    url = elem.get_attribute('href')
                    name = elem.get_attribute('innerText').strip()
                    if url and name and url not in seen_urls:
                        if len(name) > 2 and "http" in url:
                            name = re.sub(r'\(\d+\)', '', name).strip()
                            seen_urls.add(url)
                            discovered.append((url, name))
                except:
                    continue
        except Exception as e:
            logger.error(f"Error scanning {base_url}: {e}")
    return list(set(discovered))

def get_product_links(driver, category_url):
    driver.get(category_url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    links = []
    elements = driver.find_elements(By.TAG_NAME, 'a')
    for elem in elements:
        try:
            href = elem.get_attribute('href')
            if href and '/product/' in href:
                links.append(href)
        except:
            continue
    return list(set(links))

def extract_details(driver, url, category_name):
    try:
        driver.get(url)
        
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_element(By.CSS_SELECTOR, ".field--name-price").text.strip()) > 2
            )
        except Exception:
            time.sleep(1) # Final fallback wait if condition fails
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. Product Name
        h1 = soup.find('h1')
        product_name = h1.text.strip() if h1 else "Unknown"
        if product_name == "Unknown":
            product_name = url.split('/product/')[-1].replace('-', ' ').title()

        # 2. SKU (Hashed by name to prevent duplicates)
        sku = ""
        sku_tag = soup.find('span', class_='sku')
        if sku_tag: sku = sku_tag.text.strip()
        if not sku: 
            hash_object = hashlib.md5(product_name.lower().encode())
            sku = f"GEN-{hash_object.hexdigest()[:8].upper()}"

        # 3. Price using precise selectors
        price = 0.0
        
        # Using selector 
        current_price_tag = soup.select_one('.field--name-price')
        if current_price_tag:
            price = clean_price(current_price_tag.get_text())

        # Fallback 1: custom m-price-details logic
        if price == 0.0:
            price_area = soup.select_one('.m-price-details')
            if price_area:
                h4_tag = price_area.select_one('h4.strong')
                if h4_tag:
                    price = clean_price(h4_tag.get_text())

        # Final Fallback Strategy: Search for "Rs." explicitly ignoring old prices
        if price == 0.0:
            candidates = soup.find_all(string=re.compile(r'Rs\.'))
            for cand in candidates:
                parent = cand.parent
                # Skip strikethrough classes
                if parent and ('line-through' in parent.get('class', []) or 'old-price' in parent.get('class', [])):
                    continue
                
                text = parent.get_text().strip()
                if any(char.isdigit() for char in text) and len(text) < 50:
                    found_price = clean_price(text)
                    if found_price > 0:
                        price = found_price
                        break

        if price == 0.0:
            logger.warning(f"⚠️ Could not find price for {product_name} ({url})")

        # 4. Image Extraction
        image_url = None
        target_img = soup.select_one("img.image-style-product-image-large")
        if target_img:
            image_url = target_img.get('src')
        if not image_url:
            main_imgs = soup.select(".region-content img")
            for img in main_imgs:
                src = img.get('src', '')
                if 'product' in src or 'styles' in src:
                    image_url = src
                    break
        if image_url and image_url.startswith('/'):
            image_url = BASE_DOMAIN + image_url

        # 5. Description
        description_parts = []
        overview_div = soup.select_one("#overview .field--name-body")
        if overview_div:
            text = overview_div.get_text(separator="\n", strip=True)
            if len(text) > 10: description_parts.append(f"Overview:\n{text}")

        spec_div = soup.select_one("#specification .field--name-field-specification")
        if spec_div:
            text = spec_div.get_text(separator="\n", strip=True)
            if len(text) > 10: description_parts.append(f"\nSpecifications:\n{text}")

        if not description_parts:
             meta_desc = soup.find("meta", {"name": "description"})
             if meta_desc: description_parts.append(meta_desc.get("content"))

        full_description = "\n".join(description_parts)

        return {
            "sku": sku,
            "product_name": product_name,
            "price": price,
            "category_name": category_name,
            "url": url,
            "image_url": image_url or "",
            "description": full_description or ""
        }
    except Exception as e:
        logger.error(f"Error extracting {url}: {e}")
        return None

def save_to_csv(data_list):
    if not data_list: return
    fieldnames = ["sku", "product_name", "price", "category_name", "url", "image_url", "description"]
    try:
        logger.info(f"Saving CSV to: {CSV_PATH}")
        with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_list)
        logger.info(f"CSV Saved: {len(data_list)} unique products written.")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")

def scrape_catalog(custom_start_urls=None):
    logger.info("Starting Scraper (CSV Mode)...")
    driver = setup_driver()
    all_products = {} 
    visited_urls = set()

    try:
        target_urls = custom_start_urls if custom_start_urls else ["https://www.lifestore.lk/"]
        categories = discover_categories(driver, target_urls)
        if not categories:
             categories = [("https://www.lifestore.lk/categories/offers", "Offers")]

        product_tasks = []
        logger.info(f"Scanning {len(categories)} categories...")
        for i, (url, cat_name) in enumerate(categories):
            links = get_product_links(driver, url)
            for link in links:
                if link not in visited_urls:
                    visited_urls.add(link)
                    product_tasks.append((link, cat_name))

        logger.info(f"Found {len(product_tasks)} total product links.")
        
        for i, (link, cat_name) in enumerate(product_tasks):
            if i % 10 == 0: logger.info(f"Scraping [{i+1}/{len(product_tasks)}]")
            data = extract_details(driver, link, cat_name)
            if data:
                all_products[data['sku']] = data 

        unique_products_list = list(all_products.values())
        save_to_csv(unique_products_list)
        logger.info("Scraping Complete. Data saved to products.csv")
        return unique_products_list

    except Exception as e:
        logger.error(f"Critical Error: {e}", exc_info=True)
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_catalog()