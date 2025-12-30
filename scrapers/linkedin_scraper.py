from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv() 

class LinkedInScraper:
    APIFY_ACTOR_ID = "supreme_coder/linkedin-post" 

    def __init__(self, company_url, max_posts=20):
        self.company_url = company_url.strip()
        
        valid_prefixes = [
            'https://www.linkedin.com/company/',    # Main domain
            'https://linkedin.com/company/',        # Main domain without www
            'http://www.linkedin.com/company/',     # HTTP main domain
            'http://linkedin.com/company/',         # HTTP main domain without www
            'https://lk.linkedin.com/company/',     # Sri Lanka regional domain
            'https://in.linkedin.com/company/',     # India regional domain
            'https://ca.linkedin.com/company/',     # Canada regional domain
            'https://au.linkedin.com/company/',     # Australia regional domain
            'https://fr.linkedin.com/company/',     # France regional domain
            'https://de.linkedin.com/company/',     # Germany regional domain
            'https://jp.linkedin.com/company/',     # Japan regional domain
            'https://br.linkedin.com/company/',     # Brazil regional domain
        ]
        
        if not any(self.company_url.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Company URL must start with one of: {', '.join(valid_prefixes)}")
        
        self.max_posts = max_posts
        
        self.api_token = os.getenv("APIFY_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_TOKEN not found in environment variables.")

        # Setup output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "linkedin_data.json")

    def scrape(self):
        print(f"📡 Initializing Apify Client for LinkedIn scraping...")
        client = ApifyClient(self.api_token)

        run_input = {
            "urls": [self.company_url],          
            "limitPerSource": self.max_posts,    
            "maxComments": 2,                    
            "maxLikes": 2,                       
            "rawData": False,                    
        }

        print(f"🚀 Starting Apify Actor: {self.APIFY_ACTOR_ID} for {self.company_url} (Max {self.max_posts} posts)...")
        
        try:
            # Run the Actor and wait for it to finish
            run = client.actor(self.APIFY_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=900 # 15 minute timeout
            )

            dataset_client = client.dataset(run["defaultDatasetId"])
            dataset_items = dataset_client.list_items().items
            
            # Prepare the final output structure
            output = {
                "timestamp": datetime.now().isoformat(),
                "source_url": self.company_url,
                "posts_scraped": len(dataset_items),
                "data": dataset_items
            }

            # Save data to JSON file
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            print(f"✅ LinkedIn data saved to {self.output_file}. Scraped {len(dataset_items)} posts.")
            
            return dataset_items

        except Exception as e:
            print(f"🚨 Error during Apify LinkedIn scraping process: {e}")
            return []

if __name__ == "__main__":
    print("--- Running LinkedIn Scraper Directly ---")
    linkedin_company_url = "https://www.linkedin.com/company/srilankatelecom"  
    
    try:
        scraper = LinkedInScraper(linkedin_company_url, max_posts=20)  # Limit to 20 posts
        scraped_data = scraper.scrape()
    except ValueError as e:
        print(f"Configuration Error: {e}")

    print("--- LinkedIn Scraper Finished ---")