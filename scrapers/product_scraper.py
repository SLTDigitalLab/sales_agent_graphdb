import time
import json
import csv
import re
import os
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_driver():
    """Setup invisible Chrome browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_price(price_str):
    if not price_str: return 0.0
    clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(clean)
    except ValueError:
        return 0.0

def discover_categories(driver, base_urls):
    """Dynamically finds categories from a list of base URLs."""
    discovered = []
    seen_urls = set()

    for base_url in base_urls:
        if not base_url: continue
        print(f"🕵️  Discovering categories from {base_url}...")
        
        try:
            driver.get(base_url)
            time.sleep(3) 

            elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/categories/')]")
            print(f"   found {len(elements)} links...")

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
            print(f"   ❌ Error scanning {base_url}: {e}")

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
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "price")))
        except:
            pass 

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        h1 = soup.find('h1')
        product_name = h1.text.strip() if h1 else "Unknown"
        if product_name == "Unknown":
            product_name = url.split('/product/')[-1].replace('-', ' ').title()

        sku = ""
        sku_tag = soup.find('span', class_='sku')
        if sku_tag: sku = sku_tag.text.strip()
        if not sku: 
            hash_object = hashlib.md5(url.encode())
            sku = f"GEN-{hash_object.hexdigest()[:8].upper()}"

        price = 0.0
        price_container = soup.select_one('.price')
        if price_container:
            ins_tag = price_container.select_one('ins .amount')
            if ins_tag:
                price = clean_price(ins_tag.text)
            else:
                amount_tag = price_container.select_one('.amount')
                if amount_tag:
                    price = clean_price(amount_tag.text)

        if price == 0.0:
            page_text = soup.get_text()
            matches = re.findall(r'(?:Rs\.?|LKR)\s*([\d,]+(?:\.\d{2})?)', page_text, re.IGNORECASE)
            valid_prices = [clean_price(m) for m in matches if clean_price(m) > 100]
            if valid_prices:
                price = min(valid_prices)

        return {
            "sku": sku,
            "product_name": product_name,
            "price": price,
            "category_name": category_name,
            "url": url
        }
    except Exception:
        return None

def save_csv(data):
    if not data: return
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..') 
    file_path = os.path.join(project_root, 'products.csv')
    keys = ["sku", "product_name", "price", "category_name", "url"]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    return file_path

def scrape_catalog(custom_start_urls=None):
    print("🚀 Starting Production Scraper (Multi-URL Support)...")
    driver = setup_driver()
    all_products = []
    visited_urls = set()

    try:
        target_urls = custom_start_urls if custom_start_urls else ["https://www.lifestore.lk/"]
        
        categories = discover_categories(driver, target_urls)
        
        if not categories:
            if custom_start_urls:
                 print("⚠️ No sub-categories found. Treating provided URLs as direct category pages.")
                 categories = [(url, "Custom Category") for url in custom_start_urls]
            else:
                print("⚠️ Auto-discovery failed. Using fallback.")
                categories = [("https://www.lifestore.lk/categories/offers", "Offers")]

        product_tasks = []
        print(f"\n📡 Scanning {len(categories)} categories...")
        
        for i, (url, cat_name) in enumerate(categories):
            print(f"   [{i+1}/{len(categories)}] {cat_name}...", end="\r")
            links = get_product_links(driver, url)
            for link in links:
                if link not in visited_urls:
                    visited_urls.add(link)
                    product_tasks.append((link, cat_name))

        print(f"\n📦 Found {len(product_tasks)} unique products.")
        
        for i, (link, cat_name) in enumerate(product_tasks):
            print(f"[{i+1}/{len(product_tasks)}] Scraping...", end="\r")
            data = extract_details(driver, link, cat_name)
            if data:
                all_products.append(data)
                if i % 10 == 0: save_csv(all_products) 

        save_csv(all_products)
        print(f"\n✅ DONE! Saved {len(all_products)} products.")
        return all_products

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_catalog()