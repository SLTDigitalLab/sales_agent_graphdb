from scrapers.website_scraper import WebsiteScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.youtube_scraper import YouTubeScraper

if __name__ == "__main__":
    print("Starting Data Collection...")

    website_url = "https://www.slt.lk"
    ws = WebsiteScraper(website_url)
    ws.scrape()

    fb_url = "https://www.facebook.com/SLTMobitel"
    fb = FacebookScraper(fb_url)
    fb.scrape()

    yt_url = "https://www.youtube.com/@SLTMobitel"
    yt = YouTubeScraper(yt_url)
    yt.scrape()

    print("All scraping completed successfully!")
