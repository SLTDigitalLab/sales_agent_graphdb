from playwright.sync_api import sync_playwright
import json
from datetime import datetime

class FacebookScraper:
    def __init__(self, page_url):
        self.page_url = page_url

    def scrape(self):
        data = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.page_url, timeout=60000)
            page.wait_for_timeout(5000)  

            posts = page.locator("div[role='article']").all()[:5]
            for post in posts:
                text = post.inner_text()
                data.append({
                    'post_text': text[:200],  
                    'source': self.page_url
                })

            browser.close()

        output = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open('data/facebook_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Facebook data saved: {len(data)} posts")
        return data
