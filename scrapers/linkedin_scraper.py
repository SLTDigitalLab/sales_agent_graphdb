from playwright.async_api import async_playwright
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

class LinkedInScraper:
    def __init__(self, company_url, max_posts=10):
        self.company_url = company_url
        self.max_posts = max_posts
        script_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "linkedin_data.json")

    async def scrape(self):
        data = []
        page_title = "Unknown LinkedIn Page"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            try:
                print(f"🔍 Visiting {self.company_url} ...")
                await page.goto(self.company_url, timeout=90000)
                await page.wait_for_timeout(7000)

                # Handle pop-up
                try:
                    overlay = page.locator('div.modal__overlay--visible').first
                    if await overlay.is_visible():
                        print("Popup found. Clicking overlay...")
                        await overlay.click(position={'x': 10, 'y': 10})
                        await page.wait_for_timeout(3000)
                except:
                    print("No popup found.")

                # Scroll to load posts
                print("Scrolling page...")
                for i in range(3):
                    await page.mouse.wheel(0, 3000)
                    await page.wait_for_timeout(3000)

                page_title = await page.title()
                print(f"Page title: {page_title}")

                # Select posts
                post_selector = "article[data-activity-urn]"
                posts = await page.locator(post_selector).all()
                posts_to_process = posts[:self.max_posts]
                print(f"Found {len(posts_to_process)} posts.")

                # Extract posts
                for i, post in enumerate(posts_to_process, start=1):
                    print(f"\n--- Scraping Post {i} ---")
                    post_text = ""
                    timestamp = ""

                    try:
                        # Expand …more
                        see_more_button = post.locator('button[data-feed-action="see-more-post"]')
                        if await see_more_button.is_visible():
                            await see_more_button.click()
                            await page.wait_for_timeout(500)

                        # Extract text
                        text_elements = await post.locator(
                            'p[data-test-id="main-feed-activity-card__commentary"]'
                        ).all()

                        if text_elements:
                            texts = [await elem.inner_text() for elem in text_elements]
                            post_text = "\n".join(texts).strip()
                            print(f"Extracted text: {post_text[:100]}...")

                        # Extract timestamp
                        try:
                            time_elem = post.locator("span.flex > time").first
                            timestamp = await time_elem.inner_text()
                        except:
                            timestamp = ""

                        if post_text:
                            data.append({
                                "post_number": i,
                                "post_text": post_text,
                                "timestamp": timestamp,
                                "page_title": page_title,
                                "source_url": self.company_url
                            })

                    except Exception as e:
                        print(f"Error scraping post {i}: {e}")
                        data.append({
                            "post_number": i,
                            "post_text": "Error scraping",
                            "error": str(e)
                        })

            except Exception as e:
                print(f"CRITICAL ERROR: {e}")

            finally:
                print("Closing browser...")
                await browser.close()

        # Save JSON
        output = {
            "timestamp": datetime.now().isoformat(),
            "page_title": page_title,
            "posts_scraped": len([item for item in data if item.get("post_text") not in ["", None]]),
            "data": data
        }

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved LinkedIn data → {self.output_file}")
        return data


# Run directly (optional)
if __name__ == "__main__":
    scraper = LinkedInScraper("https://lk.linkedin.com/company/srilankatelecom", max_posts=5)
    asyncio.run(scraper.scrape())
