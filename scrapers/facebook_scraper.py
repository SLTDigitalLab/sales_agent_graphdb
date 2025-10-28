from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import os
import time

class FacebookScraper:
    def __init__(self, page_url, max_posts=10):
        self.page_url = page_url
        self.max_posts = max_posts
        os.makedirs("data", exist_ok=True)

    def scrape(self):
        data = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            print(f"🔍 Visiting {self.page_url} ...")
            page.goto(self.page_url, timeout=60000)
            page.wait_for_timeout(6000)

            # ✅ Scroll down to load more posts
            for _ in range(3):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(3000)

            # ✅ Page title (page name)
            title = page.title()

            # ✅ Select visible posts
            posts = page.locator("div[role='article']").all()[:self.max_posts]

            for i, post in enumerate(posts, start=1):
                try:
                    # ✅ Extract post text
                    post_text = post.inner_text().strip()

                    # ✅ Detect if post contains media (image, video, link)
                    has_image = len(post.locator("img").all()) > 0
                    has_video = len(post.locator("video").all()) > 0
                    has_link = len(post.locator("a[href*='http']").all()) > 0
                    media_type = []
                    if has_image: media_type.append("image")
                    if has_video: media_type.append("video")
                    if has_link: media_type.append("link")

                    # ✅ Extract timestamp (if available)
                    timestamp = ""
                    try:
                        time_elem = post.locator("a[aria-label*='at'], a[aria-label*='on']").first
                        timestamp = time_elem.get_attribute("aria-label") or ""
                    except:
                        pass

                    # ✅ Extract visible comments (up to 5)
                    comments = []
                    try:
                        comment_divs = post.locator("div[aria-label='Comment']").all()[:5]
                        for c in comment_divs:
                            comment_text = c.inner_text().strip()
                            if comment_text:
                                comments.append(comment_text)
                    except:
                        pass

                    # ✅ Save structured post data
                    data.append({
                        "post_number": i,
                        "post_text": post_text,
                        "comments": comments,
                        "media_type": media_type,
                        "timestamp": timestamp,
                        "page_title": title,
                        "source_url": self.page_url
                    })

                except Exception as e:
                    print(f"⚠️ Error scraping post {i}: {e}")

            browser.close()

        # ✅ Save data to JSON file
        output = {
            "timestamp": datetime.now().isoformat(),
            "page_title": title,
            "posts_scraped": len(data),
            "data": data
        }

        with open("data/facebook_data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Facebook data saved: {len(data)} posts")
        return data
