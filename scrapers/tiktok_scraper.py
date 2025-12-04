from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv() 

class TikTokScraper:
    # Using the TikTok scraper actor
    APIFY_ACTOR_ID = "clockworks/tiktok-scraper" #Apify actor ID

    def __init__(self, profile_url, max_posts=10):
        self.profile_url = profile_url.strip()
        
        # Validate TikTok profile URL format
        valid_prefixes = [
            'https://www.tiktok.com/@',
            'https://tiktok.com/@',
            'https://www.tiktok.com/profile/',
            'https://tiktok.com/profile/',
        ]
        
        if not any(self.profile_url.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Profile URL must start with one of: {', '.join(valid_prefixes)}")
        
        # Extract username for validation
        username = self.profile_url.split('@')[-1].split('/')[0] if '@' in self.profile_url else None
        if not username or len(username) < 2:
            raise ValueError("Invalid TikTok username format. URL should be like: https://www.tiktok.com/@username")
        
        self.max_posts = max_posts
        
        # Get the API token from the environment variable
        self.api_token = os.getenv("APIFY_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_TOKEN not found in environment variables.")

        # Setup output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "tiktok_data.json")

    def scrape(self):
        print(f"📡 Initializing Apify Client for TikTok scraping...")
        client = ApifyClient(self.api_token)

        # Define the input for the apify actor
        run_input = {
            "profiles": [self.profile_url],          # TikTok profile URL
            "resultsPerPage": min(self.max_posts, 50),  # Limit per page (max 50)
            "profileSorting": "latest",              # Get latest posts
            "excludePinnedPosts": True,              # Exclude pinned posts
            "scrapeRelatedVideos": False,            # Don't scrape related videos
            "shouldDownloadAvatars": False,          # Don't download avatars
            "shouldDownloadCovers": False,           # Don't download covers
            "shouldDownloadMusicCovers": False,      # Don't download music covers
            "shouldDownloadSlideshowImages": False,  # Don't download slideshow images
            "shouldDownloadSubtitles": False,        # Don't download subtitles
            "shouldDownloadVideos": False            # Don't download videos
        }

        print(f"🚀 Starting Apify Actor: {self.APIFY_ACTOR_ID} for {self.profile_url} (Max {self.max_posts} posts)...")
        
        try:
            # Run the Actor and wait for it to finish
            run = client.actor(self.APIFY_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=1200  # 20 minute timeout 
            )
            dataset_client = client.dataset(run["defaultDatasetId"])
            dataset_items = dataset_client.list_items().items
            
            # Prepare the final output structure
            output = {
                "timestamp": datetime.now().isoformat(),
                "source_url": self.profile_url,
                "posts_scraped": len(dataset_items),
                "data": dataset_items
            }

            # Save data to JSON file
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            print(f"✅ TikTok data saved to {self.output_file}. Scraped {len(dataset_items)} posts.")
            
            return dataset_items

        except Exception as e:
            print(f"🚨 Error during Apify TikTok scraping process: {e}")
            return []

if __name__ == "__main__":
    print("--- Running TikTok Scraper Directly ---")
    tiktok_profile_url = "https://www.tiktok.com/@sltmobitel"  
    
    try:
        scraper = TikTokScraper(tiktok_profile_url, max_posts=10)  # Limit to 10 posts
        scraped_data = scraper.scrape()
    except ValueError as e:
        print(f"Configuration Error: {e}")

    print("--- TikTok Scraper Finished ---")