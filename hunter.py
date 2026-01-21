import os
import json
import requests
import random
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from datetime import datetime

# CONFIGURATION
BRAND_NAME = os.getenv("BRAND_NAME", "Rolex")  # Default to Rolex for testing
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/"
    }

results = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# --- SOURCE 1: GENERAL SEARCH (DuckDuckGo to avoid Google bans) ---
def hunt_general_web():
    log(f"🔎 Hunting standalone shops for '{BRAND_NAME}'...")
    try:
        query = f'intitle:"{BRAND_NAME}" inurl:"shop" OR inurl:"store" -site:amazon.com -site:ebay.com -site:etsy.com'
        with DDGS() as ddgs:
            # DuckDuckGo is aggressive with rate limits, so we grab just a few
            search_results = list(ddgs.text(query, max_results=10))
            
        for r in search_results:
            results.append({
                "source": "General Web",
                "title": r['title'],
                "price": "N/A",
                "link": r['href'],
                "image": "https://placehold.co/100x100?text=Web", # Placeholder as generic search doesn't always give thumbnails
                "suspicion": "Standalone Storefront"
            })
        log(f"✅ Found {len(search_results)} general sites.")
    except Exception as e:
        log(f"⚠️ General Web search failed: {e}")

# --- SOURCE 2: EBAY ---
def hunt_ebay():
    log(f"🔎 Hunting eBay for '{BRAND_NAME}'...")
    try:
        # Filter for "Buy It Now" to avoid auctions, sort by price low to high
        url = f"https://www.ebay.com/sch/i.html?_nkw={BRAND_NAME}&_sop=15&rt=nc&LH_BIN=1"
        r = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        
        items = soup.select('.s-item__wrapper')
        count = 0
        for item in items[:10]: # Limit to avoid bloat
            try:
                title = item.select_one('.s-item__title').text
                if "Shop on eBay" in title: continue # Skip heuristic header
                
                link = item.select_one('.s-item__link')['href']
                price = item.select_one('.s-item__price').text
                img = item.select_one('.s-item__image-img')['src']
                
                results.append({
                    "source": "eBay",
                    "title": title,
                    "price": price,
                    "link": link,
                    "image": img,
                    "suspicion": "Marketplace Listing"
                })
                count += 1
            except:
                continue
        log(f"✅ Found {count} eBay listings.")
    except Exception as e:
        log(f"⚠️ eBay search failed: {e}")

# --- SOURCE 3: ETSY ---
def hunt_etsy():
    log(f"🔎 Hunting Etsy for '{BRAND_NAME}'...")
    try:
        url = f"https://www.etsy.com/search?q={BRAND_NAME}&explicit=1&order=price_asc"
        r = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Etsy classes change often, targeting robust containers
        cards = soup.select('.v2-listing-card')
        count = 0
        for card in cards[:10]:
            try:
                title = card.select_one('.v2-listing-card__info h3').text.strip()
                link = card.select_one('a')['href']
                price = card.select_one('.currency-value').text.strip()
                img = card.select_one('img')['src']
                
                results.append({
                    "source": "Etsy",
                    "title": title,
                    "price": price,
                    "link": link,
                    "image": img,
                    "suspicion": "Handmade/Replica"
                })
                count += 1
            except:
                continue
        log(f"✅ Found {count} Etsy listings.")
    except Exception as e:
        log(f"⚠️ Etsy search failed: {e}")

# --- SOURCE 4: ALIEXPRESS (Hardest, often blocks) ---
def hunt_aliexpress():
    log(f"🔎 Hunting AliExpress for '{BRAND_NAME}'...")
    try:
        # Using a direct search URL often triggers captcha. 
        # We try a specific endpoint or simple scraper. If this fails, the script continues.
        url = f"https://www.aliexpress.com/wholesale?SearchText={BRAND_NAME}"
        # Note: AliExpress HTML is dynamically loaded via JS. 
        # Without Selenium/Playwright (too heavy for this "zero-cost" request), 
        # we can only get basic meta tags or fail gracefully.
        # We will attempt a request, but expect 0 results often on pure requests.
        r = requests.get(url, headers=get_headers(), timeout=10)
        
        # Simple check for title just to prove we connected
        if r.status_code == 200:
            # parsing logic for Ali is highly volatile due to obfuscation
            pass 
        log(f"ℹ️ AliExpress scraping requires JS rendering (Selenium). Skipped to save resources.")
    except Exception as e:
        log(f"⚠️ AliExpress search failed: {e}")

def main():
    log("🚀 Starting Counterfeit Hunter...")
    
    hunt_general_web()
    time.sleep(2) # Be polite
    hunt_ebay()
    time.sleep(2)
    hunt_etsy()
    
    # Save Data
    with open('data.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"💾 Saved {len(results)} potential fakes to data.json")

if __name__ == "__main__":
    main()
