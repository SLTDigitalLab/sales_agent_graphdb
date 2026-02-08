import time
import json
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
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- 1. SETUP PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..', '..')
sys.path.append(project_root)

# --- 2. DATABASE IMPORTS ---
from src.api.db.sessions import SessionLocal
from src.api.db.models import Product
# NEW: Import the sync function
from src.api.services.neo4j_service import run_neo4j_ingestion

# --- 3. LOGGER ---
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
    if not price_str: return 0.0
    clean = re.sub(r'[^\d.]', '', str(price_str))
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
        time.sleep(1) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. Product Name
        h1 = soup.find('h1')
        product_name = h1.text.strip() if h1 else "Unknown"
        if product_name == "Unknown":
            product_name = url.split('/product/')[-1].replace('-', ' ').title()

        # 2. SKU
        sku = ""
        sku_tag = soup.find('span', class_='sku')
        if sku_tag: sku = sku_tag.text.strip()
        if not sku: 
            hash_object = hashlib.md5(url.encode())
            sku = f"GEN-{hash_object.hexdigest()[:8].upper()}"

        # 3. Price
        price = 0.0
        price_tag = soup.select_one('.field--name-price') 
        if price_tag:
            price = clean_price(price_tag.get_text())
        
        if price == 0.0:
            # Fallbacks
            price_tags = soup.select('.price, .product-price')
            for tag in price_tags:
                found = clean_price(tag.get_text())
                if found > 100:
                    price = found
                    break

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

        # 5. Description & Specs Extraction
        description_parts = []
        
        # Part A: Overview (Product Description)
        overview_div = soup.select_one("#overview .field--name-body")
        if overview_div:
            text = overview_div.get_text(separator="\n", strip=True)
            if len(text) > 10:
                description_parts.append(f"Overview:\n{text}")

        # Part B: Specifications
        spec_div = soup.select_one("#specification .field--name-field-specification")
        if spec_div:
            text = spec_div.get_text(separator="\n", strip=True)
            if len(text) > 10:
                description_parts.append(f"\nSpecifications:\n{text}")

        # Fallback if both tabs failed
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
            "image_url": image_url,
            "description": full_description
        }
    except Exception:
        return None

def save_products(data_list):
    if not data_list: return

    db = SessionLocal()
    try:
        updated = 0
        added = 0
        
        for item in data_list:
            # Check for existing product by SKU (this matches the Seeded data)
            product = db.query(Product).filter(Product.sku == item['sku']).first()
            
            if product:
                # UPDATE Mode: Fill in the missing descriptions!
                if item['description']: product.description = item['description']
                if item['image_url']: product.image_url = item['image_url']
                
                # Update metadata if needed
                product.product_url = item['url']
                product.category = item['category_name']
                # NOTE: We do NOT update price to 0.0 if scraper fails. 
                # We trust the CSV price more, so only update if scraper found a valid price > 0
                if item['price'] > 0:
                    product.price = item['price']
                    
                updated += 1
            else:
                # CREATE Mode: Found a new product not in CSV
                new_product = Product(
                    sku=item['sku'],
                    name=item['product_name'],
                    price=item['price'],
                    category=item['category_name'],
                    product_url=item['url'],
                    image_url=item['image_url'],
                    description=item['description'],
                    stock_quantity=random.randint(0, 10)
                )
                db.add(new_product)
                added += 1
        
        db.commit()
        logger.info(f"SQL Sync: Added {added}, Updated {updated} products.")
        
    except Exception as e:
        logger.error(f"Failed to save to SQL: {e}")
        db.rollback()
    finally:
        db.close()

def scrape_catalog(custom_start_urls=None):
    logger.info("Starting Scraper (Tab-Aware)...")
    driver = setup_driver()
    all_products = []
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

        logger.info(f"Found {len(product_tasks)} unique products.")
        
        for i, (link, cat_name) in enumerate(product_tasks):
            if i % 10 == 0: logger.info(f"Scraping [{i+1}/{len(product_tasks)}]")
            data = extract_details(driver, link, cat_name)
            if data:
                all_products.append(data)
                if i % 10 == 0 and i > 0: save_products([data]) 
                
        # Final Save
        save_products(all_products)
        logger.info("Scraping Complete.")
        
        # TRIGGER NEO4J SYNC
        logger.info("🔄 Triggering Full Neo4j Synchronization...")
        try:
            run_neo4j_ingestion()
            logger.info("✅ Neo4j Sync Successful!")
        except Exception as e:
            logger.error(f"❌ Neo4j Sync Failed: {e}")

        return all_products

    except Exception as e:
        logger.error(f"Critical Error: {e}", exc_info=True)
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_catalog()