from playwright.sync_api import sync_playwright
import json
from datetime import datetime

class YouTubeScraper:
    def __init__(self, channel_url):
        self.channel_url = channel_url

    def scrape(self):
        data = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.channel_url, timeout=60000)
            page.wait_for_timeout(5000)

            videos = page.locator("a#video-title").all()[:10]
            for v in videos:
                title = v.inner_text().strip()
                link = v.get_attribute("href")
                if title:
                    data.append({
                        'title': title,
                        'link': f"https://www.youtube.com{link}",
                        'source': self.channel_url
                    })

            browser.close()

        output = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open('data/youtube_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"YouTube data saved: {len(data)} videos")
        return data
