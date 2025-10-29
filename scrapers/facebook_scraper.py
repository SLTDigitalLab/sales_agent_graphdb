from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import os
import time

class FacebookScraper:
    def __init__(self, page_url, max_posts=10):
        self.page_url = page_url
        self.max_posts = max_posts
        # Ensure the output directory exists relative to the script
        script_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(script_dir, '..', 'data') # Assumes data is one level up
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "facebook_data.json")

    def scrape(self):
        data = []
        title = "Unknown Facebook Page" # Default title

        with sync_playwright() as p:
            # Run headed for easier debugging initially
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                # Add a common user agent to look less like a bot
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()

            try:
                print(f"🔍 Visiting {self.page_url} ...")
                # Increased timeout and wait_until might help
                page.goto(self.page_url, timeout=90000, wait_until='networkidle')
                page.wait_for_timeout(5000) # Initial wait for content

                # --- START: Handle Login/Signup Popup ---
                print("Checking for login/signup popup...")
                # --- Use the selector targeting the aria-label ---
                popup_close_selector = 'div[aria-label="Close"]' # <-- CORRECTED SELECTOR
                try:
                    close_button = page.locator(popup_close_selector).first
                    if close_button.is_visible(timeout=10000): # Wait up to 10s for popup
                        print("Login/signup popup detected. Attempting to close...")
                        close_button.click()
                        print("Popup close button clicked.")
                        page.wait_for_timeout(3000) # Wait a bit for popup to disappear
                    else:
                        print("Popup close button not visible within timeout.")
                except Exception as e:
                    print(f"Did not find or could not close popup using selector '{popup_close_selector}': {e}")
                # --- END: Handle Login/Signup Popup ---

                # --- Handle potential cookie consent popup (Keep this or refine) ---
                print("Checking for cookie popup...")
                cookie_button_selector = "div[aria-label='Allow all cookies']" # Example selector
                try:
                    cookie_button = page.locator(cookie_button_selector).first
                    if cookie_button.is_visible(timeout=5000):
                        print("Attempting to close cookie popup...")
                        cookie_button.click()
                        page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"Cookie popup not found or couldn't be closed: {e}")
                # --- End Cookie Handling ---

                print("Scrolling down to load posts...")
                # --- Improved Scrolling ---
                last_height = page.evaluate("document.body.scrollHeight")
                scroll_attempts = 0
                max_scroll_attempts = 5 # Limit scrolls to avoid infinite loops

                while scroll_attempts < max_scroll_attempts:
                    page.mouse.wheel(0, 5000) # Scroll down further
                    page.wait_for_timeout(4000) # Wait for content to potentially load
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        # If height didn't change, we might be at the bottom or stuck
                        print("Scroll height didn't change, stopping scroll.")
                        break
                    last_height = new_height
                    scroll_attempts += 1
                    print(f"Scroll attempt {scroll_attempts} completed.")
                    # Optional: Check if enough posts are loaded early
                    # post_count = len(page.locator("div[role='article']").all())
                    # if post_count >= self.max_posts:
                    #     print(f"Found {post_count} potential posts, stopping scroll early.")
                    #     break

                title = page.title()
                print(f"Finished scrolling. Page title: {title}")

                # Select posts *after* scrolling
                posts = page.locator("div[role='article']").all()
                print(f"Found {len(posts)} potential post elements.")
                posts_to_process = posts[:self.max_posts] # Limit after finding all

                for i, post in enumerate(posts_to_process, start=1):
                    print(f"\n--- Scraping Post {i} ---")
                    post_text = "" # Initialize default
                    comments = []
                    media_type = []
                    timestamp = ""

                    try:
                        # --- START: MODIFIED TEXT EXTRACTION ---
                        try:
                            # Try finding the specific div with dir="auto"
                            text_elements = post.locator('div[dir="auto"]').all()
                            if text_elements:
                                potential_texts = [elem.inner_text() for elem in text_elements]
                                # Filter out potential noise
                                valid_texts = [text for text in potential_texts if text and len(text) > 10]
                                post_text = "\n".join(valid_texts).strip()
                                print(f"  Extracted text using div[dir='auto']: {post_text[:100]}...")
                            else:
                                print("  Selector 'div[dir=\"auto\"]' found no elements.")

                        except Exception as e:
                            print(f"  Error extracting text with specific selector: {e}")
                            post_text = ""

                        # Fallback if the specific selector didn't yield text
                        if not post_text:
                            print(f"  Warning: Specific selector yielded no text. Falling back to article inner_text.")
                            try:
                                full_article_text = post.inner_text().strip()
                                lines = full_article_text.split('\n')
                                filtered_lines = [line for line in lines if len(line) > 15 and not any(kw in line for kw in ['Like', 'Comment', 'Share', 'ago', ' hrs', 'View reactions'])]
                                post_text = "\n".join(filtered_lines).strip()
                                print(f"  Extracted text using fallback: {post_text[:100]}...")
                            except Exception as fallback_e:
                                print(f"  Error during fallback text extraction: {fallback_e}")
                                post_text = ""
                        # --- END: MODIFIED TEXT EXTRACTION ---

                        if not post_text:
                             print(f"  Warning: Extracted empty text for post {i}.")

                        # Extract media types
                        has_image = len(post.locator("img").all()) > 0
                        has_video = len(post.locator("video").all()) > 0
                        has_link = len(post.locator("a[href*='http']").all()) > 0
                        if has_image: media_type.append("image")
                        if has_video: media_type.append("video")
                        if has_link: media_type.append("link")
                        print(f"  Media types found: {media_type}")

                        # Extract timestamp
                        try:
                            # Attempt to find timestamp using common patterns
                            # Combined selector for relative time (e.g., '5h') or absolute time links
                            time_elem = post.locator("span > a > span[aria-label], a[aria-label*='at'], a[aria-label*='on']").first
                            timestamp_text = time_elem.get_attribute("aria-label") or time_elem.inner_text() or ""
                            timestamp = timestamp_text.strip()
                            print(f"  Timestamp found: {timestamp}")
                        except Exception as time_e:
                            print(f"  Warning: Could not extract timestamp: {time_e}")
                            timestamp = ""

                        # Extract comments
                        try:
                            comment_divs = post.locator("div[aria-label='Comment']").all()[:5]
                            for c_idx, c in enumerate(comment_divs):
                                comment_text = c.inner_text().strip()
                                if comment_text:
                                    comments.append(comment_text)
                            print(f"  Found {len(comments)} comments.")
                        except Exception as comment_e:
                            print(f"  Warning: Error extracting comments: {comment_e}")


                        # Save structured post data
                        data.append({
                            "post_number": i,
                            "post_text": post_text,
                            "comments": comments,
                            "media_type": media_type,
                            "timestamp": timestamp,
                            "page_title": title, # Use title captured after page load
                            "source_url": self.page_url
                        })

                    except Exception as e:
                        # Catch errors specific to processing a single post
                        print(f"⚠️ MAJOR Error scraping post {i}: {e}")
                        # Optionally, add a placeholder entry to know a post failed
                        data.append({
                            "post_number": i,
                            "post_text": "Error during scraping",
                            "comments": [], "media_type": [], "timestamp": "",
                            "page_title": title, "source_url": self.page_url, "error": str(e)
                        })

            except Exception as page_load_error:
                 print(f"🚨 CRITICAL ERROR during page load or scraping process: {page_load_error}")
                 # Try to get title even if scraping fails
                 try:
                     title = page.title()
                 except:
                     pass # Keep default title

            finally:
                # Ensure browser closes even if errors occur
                print("Closing browser...")
                browser.close()

        # Save data to JSON file
        output = {
            "timestamp": datetime.now().isoformat(),
            "page_title": title,
            "posts_scraped": len([item for item in data if "error" not in item]), # Count successful scrapes
            "data": data
        }

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"✅ Facebook data saved to {self.output_file}: {len(data)} entries processed.")
        except Exception as file_e:
            print(f"🚨 Error saving data to JSON: {file_e}")

        return data

# --- Block to run the scraper directly ---
if __name__ == "__main__":
    print("--- Running Facebook Scraper Directly ---")
    fb_page_url = "https://www.facebook.com/SLTMobitel"
    max_posts_to_scrape = 5 # Adjust as needed for testing

    scraper = FacebookScraper(fb_page_url, max_posts=max_posts_to_scrape)
    scraped_data = scraper.scrape()
    print("--- Facebook Scraper Finished ---")