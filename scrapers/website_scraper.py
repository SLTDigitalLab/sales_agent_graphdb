import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import os

class WebsiteScraper:
    def __init__(self, base_url, max_pages=15):
        self.base_url = base_url
        self.visited = set()
        self.max_pages = max_pages
        self.data = []
        os.makedirs("data", exist_ok=True)

    def scrape_page(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Skipping {url} (status {response.status_code})")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.title.string.strip() if soup.title else ""

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            headings = {
                "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                "h3": [h.get_text(strip=True) for h in soup.find_all("h3")]
            }

            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]

            all_text = " ".join(paragraphs)

            self.data.append({
                "url": url,
                "title": title,
                "meta_description": meta_desc,
                "headings": headings,
                "paragraphs": paragraphs,
                "full_text": all_text
            })

            for a_tag in soup.find_all('a', href=True):
                full_url = urljoin(url, a_tag['href'])
                if self.is_internal_link(full_url):
                    if full_url not in self.visited and len(self.visited) < self.max_pages:
                        self.visited.add(full_url)
                        self.scrape_page(full_url)

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    def is_internal_link(self, url):
        return urlparse(url).netloc == urlparse(self.base_url).netloc

    def scrape(self):
        print(f"Starting crawl from {self.base_url} ...")
        self.visited.add(self.base_url)
        self.scrape_page(self.base_url)

        output = {
            'timestamp': datetime.now().isoformat(),
            'pages_scraped': len(self.data),
            'data': self.data
        }

        with open('data/website_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Completed. Scraped {len(self.data)} pages.")
        return self.data
