import time
import json
import csv
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Configuration
START_URLS = [
    ("https://www.lifestore.lk/categories/offers", "Offers"), 
    ("https://www.lifestore.lk/categories/wi-fi-devices", "Wi-Fi Devices"),
    ("https://www.lifestore.lk/categories/powerbackup", "Power Backup"),
    ("https://www.lifestore.lk/categories/telephones", "Telephones"),
    ("https://www.lifestore.lk/categories/mobile-routers", "Mobile Routers"),
]

def setup_driver():
    """Setup invisible Chrome browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run invisible
    chrome_options.add_argument("--log-level=3") # Suppress warnings
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Using webdriver_manager to automatically handle the driver installation
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def clean_price(price_str):
    if not price_str: return 0.0
    # Clean "Rs. 5,595.00" -> 5595.0
    clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(clean)
    except ValueError:
        return 0.0

def get_product_links(driver, category_url):
    """Get all product links from a category page"""
    print(f"📂 Scanning: {category_url}")
    driver.get(category_url)
    
    # Scroll down to trigger lazy loading images/products
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3) # Wait for JS to load items
    
    links = []
    # Find all 'a' tags
    elements = driver.find_elements(By.TAG_NAME, 'a')
    
    for elem in elements:
        try:
            href = elem.get_attribute('href')
            if href and '/product/' in href:
                links.append(href)
        except:
            continue
            
    # Remove duplicates
    return list(set(links))

def extract_details(driver, url, category_name):
    """Visit product page and extract visible data"""
    try:
        driver.get(url)
        # Wait up to 5 seconds for the price to appear
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "price"))
            )
        except:
            pass # Continue even if timeout, we'll try brute force

        # Get the page source after JS has run
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. Product Name (Real H1 text)
        h1 = soup.find('h1')
        product_name = h1.text.strip() if h1 else "Unknown"
        if product_name == "Unknown":
            # Fallback to URL
            product_name = url.split('/product/')[-1].replace('-', ' ').title()

        # 2. SKU
        sku = ""
        sku_tag = soup.find('span', class_='sku')
        if sku_tag: sku = sku_tag.text.strip()
        if not sku: sku = f"GEN-{product_name[:3].upper()}{str(len(product_name))}"

        # 3. Price (Brute Force Text Search)
        # Since class names change, we search the whole text for "Rs. 5000"
        price = 0.0
        
        # Method A: Look for specific price structure (WooCommerce)
        price_container = soup.select_one('.price')
        if price_container:
            # Check for Sale Price first
            ins_tag = price_container.select_one('ins .amount')
            if ins_tag:
                price = clean_price(ins_tag.text)
            else:
                # Regular price
                amount_tag = price_container.select_one('.amount')
                if amount_tag:
                    price = clean_price(amount_tag.text)

        # Method B: Regex on the whole page text (The "Nuclear" Option)
        if price == 0.0:
            page_text = soup.get_text()
            # Find all patterns like "Rs 5,000" or "Rs.5000.00"
            matches = re.findall(r'(?:Rs\.?|LKR)\s*([\d,]+(?:\.\d{2})?)', page_text, re.IGNORECASE)
            
            valid_prices = []
            for m in matches:
                val = clean_price(m)
                if val > 100: # Filter out tiny numbers
                    valid_prices.append(val)
            
            if valid_prices:
                # usually the minimum valid price is the real price (others might be 'save Rs 200')
                price = min(valid_prices)

        return {
            "sku": sku,
            "product_name": product_name,
            "price": price,
            "category_name": category_name,
            "url": url
        }

    except Exception as e:
        print(f"⚠️ Error on {url}: {e}")
        return None

def scrape_catalog():
    print("🚀 Starting Selenium Scraper (Chrome)...")
    driver = setup_driver()
    
    all_products = []
    visited_urls = set()

    try:
        # Phase 1: Gather Links
        product_tasks = []
        for url, cat_name in START_URLS:
            links = get_product_links(driver, url)
            new_links = 0
            for link in links:
                if link not in visited_urls:
                    visited_urls.add(link)
                    product_tasks.append((link, cat_name))
                    new_links += 1
            print(f"   ✅ Found {new_links} new products in {cat_name}")

        print(f"\n📦 Processing {len(product_tasks)} products...")

        # Phase 2: Extract Details
        for i, (link, cat_name) in enumerate(product_tasks):
            print(f"[{i+1}/{len(product_tasks)}] Visiting...", end="\r")
            
            data = extract_details(driver, link, cat_name)
            
            if data:
                all_products.append(data)
                status = "✅" if data['price'] > 0 else "❌"
                # Clear line and print result
                print(f"{status} Rs. {data['price']:<9} | {data['product_name'][:40]}")
            
            # Save incrementally (in case script crashes)
            if i % 5 == 0:
                save_csv(all_products)

        # Final Save
        save_csv(all_products)
        print("\n✅ DONE! Data saved to products.csv")

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
    finally:
        driver.quit()

def save_csv(data):
    if not data: return
    keys = ["sku", "product_name", "price", "category_name", "url"]
    with open('products.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    scrape_catalog()