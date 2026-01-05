from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv() 

class FacebookScraper:
    # Apify Actor ID for Facebook Posts Scraper
    APIFY_ACTOR_ID = "apify/facebook-posts-scraper" 

    def __init__(self, page_url, max_posts=20, max_comments_per_post=10):
        # NOTE: Make sure the Facebook URL is for a public page, not a profile.
        self.page_url = page_url
        self.max_posts = max_posts
        self.max_comments = max_comments_per_post
        
        # Get the API token from the environment variable
        self.api_token = os.getenv("APIFY_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_TOKEN not found in environment variables.")

        # Setup output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "facebook_data.json")

    def scrape(self):
        print(f"📡 Initializing Apify Client...")
        client = ApifyClient(self.api_token)

        # 1. Define the input for the Apify Actor
        run_input = {
            "startUrls": [{"url": self.page_url}],
            "resultsLimit": self.max_posts,
            "scrapeComments": True,
            "maxCommentsPerPost": self.max_comments,
        }

        print(f"🚀 Starting Apify Actor: {self.APIFY_ACTOR_ID} for {self.page_url} (Max {self.max_posts} posts)...")
        
        try:
            # 2. Run the Actor and wait for it to finish
            run = client.actor(self.APIFY_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=600 # 10 minute timeout
            )

            # 3. Fetch and structure the results using list_items()
            dataset_client = client.dataset(run["defaultDatasetId"])
            
            dataset_items = dataset_client.list_items().items
            
            # 4. Prepare the final output structure
            output = {
                "timestamp": datetime.now().isoformat(),
                "source_url": self.page_url,
                "posts_scraped": len(dataset_items),
                "data": dataset_items
            }

            # 5. Save data to JSON file
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Facebook data saved to {self.output_file}. Scraped {len(dataset_items)} posts.")
            
            return dataset_items

        except Exception as e:
            print(f"🚨 Error during Apify scraping process: {e}")
            return []

if __name__ == "__main__":
    print("--- Running Facebook Scraper Directly ---")
    facebook_page_url = "https://www.facebook.com/SLTMobitel/" 
    
    try:
        scraper = FacebookScraper(facebook_page_url, max_posts=5, max_comments_per_post=2)
        scraped_data = scraper.scrape()
    except ValueError as e:
        print(f"Configuration Error: {e}")

    print("--- Facebook Scraper Finished ---")