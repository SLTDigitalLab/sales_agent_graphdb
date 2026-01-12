import time
import json
import os
import re
from typing import List, Union
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup 

# IMPORT LOGGER
try:
    from src.utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self, urls: Union[str, List[str]]):
        if isinstance(urls, str):
            self.urls = [urls]
        else:
            self.urls = urls
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(script_dir, '..')
        self.data_dir = os.path.join(project_root, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(self.data_dir, "website_data.json")

    def setup_driver(self):
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

    def extract_clean_content(self, html_source):
        """
        Uses BeautifulSoup to remove navigation, footers, and scripts,
        returning only the meaningful text.
        """
        soup = BeautifulSoup(html_source, 'html.parser')

        # 1. Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript', 'iframe']):
            tag.decompose()

        # 2. Extract text with spacing
        text = soup.get_text(separator='\n')

        # 3. Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text

    def scrape(self):
        logger.info("Starting General Website Scraper (Selenium + Soup)...")
        driver = self.setup_driver()
        all_data = []

        try:
            for url in self.urls:
                if not url: continue
                
                logger.info(f"Visiting: {url}...")
                try:
                    driver.get(url)
                    time.sleep(5) # Wait for JS to load
                    
                    # Get the Title
                    title = driver.title
                    
                    # Pass the raw HTML to our cleaner function
                    clean_text = self.extract_clean_content(driver.page_source)
                    
                    if len(clean_text) > 100:
                        logger.info(f"Successfully scraped {len(clean_text)} chars from {url}")
                        all_data.append({
                            "source": "website",
                            "url": url,
                            "title": title,
                            "content": clean_text,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    else:
                        logger.warning(f"Content too short or empty for {url}.")
                        
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}", exc_info=True)

            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Website scraping complete. Saved to {self.output_file}")
            return all_data

        finally:
            driver.quit()