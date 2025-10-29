from scrapers.website_scraper import WebsiteScraper
# from scrapers.facebook_scraper import FacebookScraper
# from scrapers.youtube_scraper import YouTubeScraper

from scrapers.linkedin_scraper import LinkedInScraper

if __name__ == "__main__":
    print("Starting Data Collection...")

    # --- Run Website Scraper ---
    website_url = "https://www.slt.lk/home"
    ws = WebsiteScraper(website_url)
    ws.scrape()

    # Run LinkedIn Scraper
    print("\n--- Starting LinkedIn Scraper ---")
    li_url = "https://lk.linkedin.com/company/srilankatelecom"
    li = LinkedInScraper(li_url, max_posts=5)
    li.scrape()

    # Facebook and YouTube are skipped for now
    print("\nSkipping Facebook Scraper.")
    # fb_url = "https://www.facebook.com/SLTMobitel"
    # fb = FacebookScraper(fb_url)
    # fb.scrape()

    print("Skipping YouTube Scraper.")
    # yt_url = "https://www.youtube.com/@SLTMobitel"
    # yt = YouTubeScraper(yt_url)
    # yt.scrape()

    print("\nAll scraping completed successfully!")