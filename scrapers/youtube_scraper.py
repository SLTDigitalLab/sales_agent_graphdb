from playwright.sync_api import sync_playwright
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import json
from datetime import datetime
import re
import time

class YouTubeScraper:
    def __init__(self, channel_url, max_videos=5):
        self.channel_url = channel_url
        self.max_videos = max_videos

    def extract_video_id(self, link):
        """Extract the YouTube video ID from the link"""
        match = re.search(r"v=([a-zA-Z0-9_-]{11})", link)
        if match:
            return match.group(1)
        return None

    def get_transcript(self, video_id):
        """Fetch transcript if available"""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = " ".join([t['text'] for t in transcript])
            return full_text
        except (TranscriptsDisabled, NoTranscriptFound):
            return "Transcript not available"
        except Exception as e:
            return f"Error: {str(e)}"

    def scrape(self):
        data = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # ✅ Navigate to Videos tab to get latest uploads
            videos_tab_url = self.channel_url.rstrip('/') + "/videos"
            page.goto(videos_tab_url, timeout=60000)
            page.wait_for_timeout(5000)

            # ✅ Scroll to load enough videos
            loaded_videos = []
            scroll_attempts = 0
            while len(loaded_videos) < self.max_videos and scroll_attempts < 10:
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2000)
                loaded_videos = page.locator("a#video-title").all()
                scroll_attempts += 1

            # ✅ Select the latest N videos
            videos = loaded_videos[:self.max_videos]

            for v in videos:
                try:
                    title = v.inner_text().strip()
                    link = v.get_attribute("href")
                    if not link:
                        continue
                    full_link = f"https://www.youtube.com{link}"
                    video_id = self.extract_video_id(full_link)

                    transcript = None
                    if video_id:
                        transcript = self.get_transcript(video_id)

                    data.append({
                        "title": title,
                        "link": full_link,
                        "video_id": video_id,
                        "transcript": transcript,
                        "source": self.channel_url
                    })
                except Exception as e:
                    print(f"⚠️ Error scraping video: {e}")

            browser.close()

        # ✅ Save to JSON
        output = {
            "timestamp": datetime.now().isoformat(),
            "videos_scraped": len(data),
            "data": data
        }

        with open("data/youtube_data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ YouTube data saved: {len(data)} videos (with transcripts)")
        return data
