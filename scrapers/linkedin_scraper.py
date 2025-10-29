from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import os
import time
from dotenv import load_dotenv

load_dotenv() # Load .env file

class LinkedInScraper:
    def __init__(self, company_url, max_posts=10):
        self.company_url = company_url
        self.max_posts = max_posts
        script_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "linkedin_data.json")

    def scrape(self):
        data = []
        page_title = "Unknown LinkedIn Page"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # Keep False for testing
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()

            try:
                # --- Navigate to the MAIN company page ---
                print(f"🔍 Visiting {self.company_url} ...")
                page.goto(self.company_url, timeout=90000, wait_until='load')
                page.wait_for_timeout(7000)
                # --- End Navigation ---

                # --- START: Handle Popup by Clicking Overlay ---
                print("Checking for modal popup...")
                try:
                    # This selector targets the visible overlay div
                    overlay_selector = 'div.modal__overlay--visible'
                    overlay = page.locator(overlay_selector).first
                    
                    if overlay.is_visible(timeout=10000): # Wait up to 10s for popup
                        print("Popup overlay detected. Attempting to click outside (near top-left corner)...")
                        # Click 10px in from the top-left corner *of the overlay element itself*
                        # This avoids the center dialog box
                        overlay.click(position={'x': 10, 'y': 10}, timeout=5000)
                        print("Clicked overlay.")
                        page.wait_for_timeout(3000) # Wait for dismiss animation
                        
                        if not overlay.is_visible(timeout=1000):
                            print("Popup appears to be closed.")
                        else:
                            print("Warning: Popup still visible after clicking overlay.")
                    else:
                        print("Popup overlay not visible within timeout.")
                except Exception as e:
                    print(f"Did not find or could not dismiss popup: {e}")
                # --- END: Handle Popup ---


                print("Scrolling down to load posts...")
                # --- Basic Scrolling ---
                for i in range(3): 
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(3000)
                    print(f"Scroll attempt {i+1} completed.")

                page_title = page.title()
                print(f"Page title: {page_title}")

                # --- Select Posts ---
                print("Selecting posts...")
                # Selector targets the <article> tag with a 'data-activity-urn'
                post_selector = "article[data-activity-urn]" 
                print(f"Using selector: '{post_selector}'")

                try:
                    posts = page.locator(post_selector).all()
                    posts_to_process = posts[:self.max_posts]
                except Exception as select_e:
                    print(f"🚨 Error finding posts with selector '{post_selector}': {select_e}")
                    posts_to_process = []

                print(f"Found {len(posts_to_process)} potential post elements to process.")

                # --- Post Processing Loop ---
                for i, post in enumerate(posts_to_process, start=1):
                     print(f"\n--- Scraping Post {i} ---")
                     post_text = ""
                     timestamp = ""
                     try:
                         # --- Text Extraction ---
                         # Targets the <p> tag with data-test-id
                         text_selector = 'p[data-test-id="main-feed-activity-card__commentary"]'
                         
                         # Click "…more" button if it exists
                         try:
                             see_more_button = post.locator('button[data-feed-action="see-more-post"]')
                             if see_more_button.is_visible(timeout=1000):
                                 print("  '…more' button found. Clicking to expand text...")
                                 see_more_button.click()
                                 page.wait_for_timeout(500) 
                         except Exception:
                             pass # Normal if no "see more" button

                         text_elements = post.locator(text_selector).all()
                         if text_elements:
                             post_text = "\n".join([elem.inner_text() for elem in text_elements]).strip()
                             print(f"  Extracted text: {post_text[:100]}...")
                         else:
                             print("  Warning: Text selector found no elements.")
                         
                         if not post_text:
                             print("  Warning: Final extracted text is empty.")

                         # --- Extract timestamp ---
                         try:
                             time_elem = post.locator("span.flex > time").first
                             timestamp = time_elem.inner_text().strip()
                             print(f"  Timestamp found: {timestamp}")
                         except Exception as time_e:
                             print(f"  Warning: Could not extract timestamp: {time_e}")
                             timestamp = "" 

                         # --- Save structured post data ---
                         if post_text: 
                             data.append({
                                 "post_number": i,
                                 "post_text": post_text,
                                 "timestamp": timestamp,
                                 "page_title": page_title,
                                 "source_url": self.company_url
                             })
                         else:
                             print("  Skipping post - no text extracted.")

                     except Exception as e:
                         print(f"⚠️ Error scraping details for post {i}: {e}")
                         data.append({
                            "post_number": i, "post_text": "Error scraping post details",
                            "page_title": page_title, "source_url": self.company_url, "error": str(e)
                         })
                # --- End Post Loop ---

            except Exception as page_load_error:
                 print(f"🚨 CRITICAL ERROR during page load or scraping process: {page_load_error}")
                 try: page_title = page.title()
                 except: pass

            finally:
                print("Closing browser...")
                browser.close()

        # --- Save data to JSON file ---
        output = {
            "timestamp": datetime.now().isoformat(),
            "page_title": page_title,
            "posts_scraped": len([item for item in data if "error" not in item and item.get("post_text") not in [None, "", "Error scraping post details"]]),
            "data": data
        }
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"✅ LinkedIn data saved to {self.output_file}: {len(data)} entries processed.")
        except Exception as file_e:
            print(f"🚨 Error saving data to JSON: {file_e}")

        return data

# --- Block to run the scraper directly ---
if __name__ == "__main__":
    print("--- Running LinkedIn Scraper Directly ---")
    linkedin_url = "https://lk.linkedin.com/company/srilankatelecom"
    max_posts_to_scrape = 5 # Start with a small number

    scraper = LinkedInScraper(linkedin_url, max_posts=max_posts_to_scrape)
    scraped_data = scraper.scrape()
    print("--- LinkedIn Scraper Finished ---")