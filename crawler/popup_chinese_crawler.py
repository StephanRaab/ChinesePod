import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import time # For adding delays
import json # For saving the summary
import re # For parsing flashvars

# --- Configuration ---
# Base URL for the Wayback Machine archive.
# This ensures all constructed URLs (relative links) correctly point to the archive.
BASE_ARCHIVE_URL = "https://web.archive.org"

# Base path for the archived PopupChinese lessons
BASE_LESSONS_PATH = "/web/20140630222515/https://popupchinese.com/lessons/"

# Directory where the downloaded audio files and the summary JSON will be saved.
DOWNLOAD_DIR = "popup_chinese_audio"

# Create the download directory if it doesn't already exist.
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Helper Functions ---

def get_page_content(url):
    """
    Fetches the HTML content of a given URL.
    Includes a User-Agent header to mimic a web browser, which can help prevent
    some basic blocking mechanisms.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Set a timeout for requests to prevent indefinite waiting.
        response = requests.get(url, headers=headers, timeout=15)
        # Raise an HTTPError for bad responses (4xx client errors or 5xx server errors).
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None 

def parse_lessons_page(html_content, current_page_url):
    """
    Parses a lesson listing page to find individual lesson links (title and URL)
    and the link to the next pagination page.
    Updated with multiple selectors to handle different page layouts.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    lessons_on_page = []
    next_page_link = None

    # --- 1. Find Lesson Items with multiple selector strategies ---
    lesson_elements = []
    
    # Strategy 1: Original selector
    lesson_elements = soup.select('div.archive_teaser')
    if not lesson_elements:
        # Strategy 2: Look for other common lesson containers
        lesson_elements = soup.select('div.lesson_teaser')
    if not lesson_elements:
        # Strategy 3: Look for any div containing lesson links
        lesson_elements = soup.select('div[class*="teaser"]')
    if not lesson_elements:
        # Strategy 4: Find all links that contain lesson URLs
        lesson_links = soup.find_all('a', href=re.compile(r'/lessons/[^/]+/[^/]+/?$'))
        for link in lesson_links:
            # Create pseudo-elements to match the expected structure
            lesson_elements.append(link.parent)
    
    print(f"Found {len(lesson_elements)} potential lesson elements")

    for item in lesson_elements:
        # --- Multiple strategies to find lesson title and URL ---
        lesson_link_tag = None
        title = ""
        lesson_url = ""
        
        # Strategy 1: Original selector
        lesson_link_tag = item.select_one('div.archive_title a')
        
        if not lesson_link_tag:
            # Strategy 2: Look for any link within the item
            lesson_link_tag = item.find('a', href=re.compile(r'/lessons/'))
        
        if not lesson_link_tag:
            # Strategy 3: Check if the item itself is a link
            if item.name == 'a' and item.get('href') and '/lessons/' in item.get('href', ''):
                lesson_link_tag = item
        
        if lesson_link_tag and lesson_link_tag.get('href'):
            # Get title from link text
            title = lesson_link_tag.get_text(strip=True)
            
            # If title is empty, try to get it from nearby elements
            if not title:
                # Look for title in parent or sibling elements
                parent = lesson_link_tag.parent
                if parent:
                    title_candidates = [
                        parent.get_text(strip=True),
                        lesson_link_tag.get('title', ''),
                        lesson_link_tag.get('alt', '')
                    ]
                    for candidate in title_candidates:
                        if candidate and len(candidate) > 3:  # Reasonable title length
                            title = candidate
                            break
            
            # If still no title, extract from URL
            if not title:
                url_parts = lesson_link_tag['href'].strip('/').split('/')
                if len(url_parts) >= 2:
                    title = url_parts[-1].replace('-', ' ').title()
            
            lesson_url = urljoin(current_page_url, lesson_link_tag['href'])
            
            if title and lesson_url:
                print(f"  Found lesson: '{title}' -> {lesson_url}")
                lessons_on_page.append({'title': title, 'url': lesson_url})
            else:
                print(f"  Skipping item - missing title or URL: title='{title}', url='{lesson_url}'")

    # --- 2. Find the "Next Page" Link (unchanged) ---
    paginator_div = soup.select_one('div.paginator#paginator')
    if paginator_div:
        current_page_tag = paginator_div.select_one('a.selected')
        if current_page_tag:
            try:
                current_page_num = int(current_page_tag.get_text(strip=True))
                next_page_num = current_page_num + 1
                next_link_tag = paginator_div.find('a', string=str(next_page_num))
                
                if next_link_tag and next_link_tag.get('href'):
                    absolute_next_url = urljoin(current_page_url, next_link_tag['href'])
                    if absolute_next_url != current_page_url:
                        parsed_current = urlparse(current_page_url)
                        parsed_next = urlparse(absolute_next_url)
                        if parsed_current.path == parsed_next.path and parsed_current.query == parsed_next.query:
                            next_page_link = None
                        else:
                            next_page_link = absolute_next_url
            except ValueError:
                print("Warning: Could not parse current page number from paginator link.")
            except Exception as e:
                print(f"Error while trying to find next page link: {e}")
    
    return lessons_on_page, next_page_link

def parse_lesson_page_for_audio(html_content, lesson_detail_url):
    """
    Parses a single lesson detail page to find the main audio file URL.
    Updated to handle both <audio> tags and Flash player flashvars.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    audio_url = None

    # Strategy 1: Look for HTML5 audio tag (for absolute beginners)
    audio_tag = soup.find('audio') 
    
    if audio_tag:
        source_tag = audio_tag.find('source')
        if source_tag and source_tag.get('src'):
            audio_url = source_tag['src']
        elif audio_tag.get('src'): 
            audio_url = audio_tag['src']
    
    # Strategy 2: Look for Flash player with flashvars (for higher levels)
    if not audio_url:
        # Look for ruffle-embed or embed tags with flashvars
        flash_elements = soup.find_all(['ruffle-embed', 'embed', 'object'])
        
        for element in flash_elements:
            flashvars = element.get('flashvars', '')
            if flashvars and 'mp3url=' in flashvars:
                # Extract mp3url from flashvars
                # Format: "mp3url=http://popupchinese.com/data/1382/audio.mp3"
                match = re.search(r'mp3url=([^&\s]+)', flashvars)
                if match:
                    audio_url = match.group(1)
                    print(f"    Found audio URL in flashvars: {audio_url}")
                    break
    
    # Strategy 3: Look for direct links to audio files
    if not audio_url:
        audio_links = soup.find_all('a', href=re.compile(r'\.(mp3|wav|m4a)(\?|$)', re.I))
        if audio_links:
            audio_url = audio_links[0]['href']
            print(f"    Found direct audio link: {audio_url}")

    if audio_url:
        # Convert relative audio URLs to absolute URLs
        absolute_url = urljoin(lesson_detail_url, audio_url)
        print(f"    Final audio URL: {absolute_url}")
        return absolute_url
        
    return None

def file_already_exists(folder, filename):
    """
    Quick check if a file already exists without any processing.
    Returns True if file exists, False otherwise.
    """
    filepath = os.path.join(folder, filename)
    return os.path.exists(filepath)

def download_file(url, folder, filename):
    """
    Downloads a file from a given URL and saves it to a specified local folder.
    Includes basic error handling and a check to skip existing files.
    """
    filepath = os.path.join(folder, filename)
    
    # Skip download if the file already exists locally.
    if os.path.exists(filepath):
        print(f"  - Skipping: {filename} already exists in {folder}.")
        return True  # Return True to indicate successful handling

    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  - Retry attempt {attempt + 1} for: {filename}")
                time.sleep(retry_delay * attempt)  # Exponential backoff
            
            print(f"  - Downloading: {filename} from {url}")
            # Use stream=True for potentially large files to avoid loading entire file into memory at once.
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            with requests.get(url, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status() # Will raise an exception for 4xx/5xx responses.
                with open(filepath, 'wb') as f:
                    # Write content in chunks.
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"  - Successfully downloaded: {filename}\n")
            return True  # Success, exit the retry loop
            
        except requests.exceptions.HTTPError as e:
            if r.status_code == 404:
                print(f"  - Audio file not found in archive for {filename} (404 error)")
                return False  # Return False to indicate failure
            else:
                print(f"  - HTTP error downloading {filename} (attempt {attempt + 1}): {e}")
        except requests.exceptions.RequestException as e:
            print(f"  - Network error downloading {filename} (attempt {attempt + 1}): {e}")
        except Exception as e:
            print(f"  - Unexpected error downloading {filename} (attempt {attempt + 1}): {e}")
    
    print(f"  - Failed to download {filename} after {max_retries} attempts")
    return False  # Return False to indicate failure

def get_user_input():
    """
    Prompts the user for the lesson category and starting page.
    Returns the complete URL path to start crawling from.
    """
    print("=== PopupChinese Audio Crawler ===")
    print("Available lesson categories:")
    print("1. absolute-beginners")
    print("2. elementary")
    print("3. intermediate")
    print("4. upper-intermediate")
    print("5. advanced")
    print("6. media")
    print("7. academic")
    print("8. custom (enter your own)")
    
    while True:
        choice = input("\nSelect a category (1-8): ").strip()
        
        if choice == "1":
            category = "absolute-beginners"
            break
        elif choice == "2":
            category = "elementary"
            break
        elif choice == "3":
            category = "intermediate"
            break
        elif choice == "4":
            category = "upper-intermediate"
            break
        elif choice == "5":
            category = "advanced"
            break
        elif choice == "6":
            category = "media"
            break
        elif choice == "7":
            category = "academic"
            break
        elif choice == "8":
            category = input("Enter custom category: ").strip()
            if category:
                break
            else:
                print("Please enter a valid category name.")
                continue
        else:
            print("Please enter a number between 1-8.")
            continue
    
    while True:
        try:
            page_num = input(f"\nEnter starting page number (default: 1): ").strip()
            if not page_num:
                page_num = 1
            else:
                page_num = int(page_num)
            
            if page_num < 1:
                print("Page number must be 1 or greater.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
            continue
    
    # Construct the full path
    lessons_path = f"{BASE_LESSONS_PATH}{category}?page={page_num}"
    full_url = urljoin(BASE_ARCHIVE_URL, lessons_path)
    
    print(f"\nStarting URL: {full_url}")
    confirm = input("Continue with this URL? (y/n): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        return lessons_path
    else:
        print("Cancelled by user.")
        return None

def sanitize_filename(title):
    """
    Converts a lesson title into a safe filename by replacing/removing invalid characters.
    Appends '.mp3' extension.
    """
    # Replace spaces with underscores for readability.
    s = title.strip().replace(' ', '_')
    # Remove any character that is not alphanumeric, an underscore, or a hyphen.
    s = ''.join(c for c in s if c.isalnum() or c in ('_', '-'))
    # Ensure the filename is not empty after sanitization.
    if not s:
        s = "untitled_lesson"
    return s + '.mp3'

# --- Main Crawler Logic ---

def main():
    """
    The main function that orchestrates the crawling process.
    It iterates through lesson listing pages, fetches individual lesson pages,
    extracts audio links and titles, and downloads the audio files.
    """
    # Get user input for starting URL
    start_lessons_path = get_user_input()
    if not start_lessons_path:
        return
    
    # Start the crawling process from the user-specified lessons listing page.
    current_page_full_url = urljoin(BASE_ARCHIVE_URL, start_lessons_path)
    # List to store a summary of all lessons processed (useful for logging/debugging).
    all_lessons_summary = []

    print(f"Starting crawl from: {current_page_full_url}")

    # Loop as long as there's a valid next page to visit.
    while current_page_full_url:
        print(f"\n--- Processing lesson listing page: {current_page_full_url} ---")
        # Fetch the HTML content of the current listing page.
        page_html = get_page_content(current_page_full_url)

        if not page_html:
            print(f"Failed to get content for {current_page_full_url}. Stopping crawl.")
            break

        # Parse the listing page to get lessons and the next page link.
        lessons_on_current_page, next_page_full_url = parse_lessons_page(page_html, current_page_full_url)

        # Handle cases where no lessons are found on a page.
        if not lessons_on_current_page and not next_page_full_url:
            print("No lessons found on this page and no next page link. Assuming end of crawl.")
            break
        elif not lessons_on_current_page:
            print(f"No lessons found on {current_page_full_url}, but a next page link was found. Proceeding to next page.")

        # Process each lesson found on the current listing page.
        for lesson_info in lessons_on_current_page:
            lesson_title_from_listing = lesson_info['title'] # Title extracted from the listing page.
            lesson_detail_url = lesson_info['url'] # URL to the individual lesson detail page.
            
            # Quick pre-check: generate potential filename and see if it already exists
            potential_filename = sanitize_filename(lesson_title_from_listing)
            if file_already_exists(DOWNLOAD_DIR, potential_filename):
                print(f"  - Skipping (already downloaded): '{lesson_title_from_listing}'")
                # Still add to summary for completeness
                all_lessons_summary.append({
                    'title': lesson_title_from_listing,
                    'lesson_url': lesson_detail_url,
                    'audio_url': 'skipped - already exists',
                    'filename': potential_filename
                })
                continue  # Skip to next lesson without fetching detail page
            
            print(f"  - Processing lesson: '{lesson_title_from_listing}' at {lesson_detail_url}")

            # Fetch the HTML content of the individual lesson detail page.
            lesson_html = get_page_content(lesson_detail_url)
            if lesson_html:
                lesson_detail_soup = BeautifulSoup(lesson_html, 'html.parser')
                
                # --- Extract the specific lesson title from the detail page for accurate filename ---
                main_title_element = lesson_detail_soup.find('div', class_='lesson_title')
                
                lesson_title_for_file = lesson_title_from_listing # Default to listing title

                if main_title_element:
                    full_title_text = main_title_element.get_text(strip=True)
                    # The title format is "Category: Actual Lesson Title" (e.g., "Absolute Beginners: Pulling a Car").
                    # We split by ": " to get just the "Actual Lesson Title".
                    if ": " in full_title_text:
                        lesson_title_for_file = full_title_text.split(": ", 1)[1].strip()
                    else:
                        lesson_title_for_file = full_title_text.strip()
                else:
                    print(f"    Warning: Main lesson title 'div.lesson_title' not found. Using title from listing page.")

                # Check again with the refined title
                refined_filename = sanitize_filename(lesson_title_for_file)
                if file_already_exists(DOWNLOAD_DIR, refined_filename):
                    print(f"    - Skipping (already downloaded with refined title): '{lesson_title_for_file}'")
                    all_lessons_summary.append({
                        'title': lesson_title_for_file,
                        'lesson_url': lesson_detail_url,
                        'audio_url': 'skipped - already exists',
                        'filename': refined_filename
                    })
                    continue

                # --- Extract the Audio Link from the lesson detail page ---
                audio_link = parse_lesson_page_for_audio(lesson_html, lesson_detail_url)
                if audio_link:
                    # Add lesson details to the summary list.
                    all_lessons_summary.append({
                        'title': lesson_title_for_file,
                        'lesson_url': lesson_detail_url,
                        'audio_url': audio_link,
                        'filename': refined_filename
                    })
                    # Download the audio file.
                    download_success = download_file(audio_link, DOWNLOAD_DIR, refined_filename)
                    if not download_success:
                        print(f"    Failed to download audio for '{lesson_title_for_file}'")
                else:
                    print(f"    No audio found for '{lesson_title_for_file}' at {lesson_detail_url}")
                    # Still add to summary for tracking
                    all_lessons_summary.append({
                        'title': lesson_title_for_file,
                        'lesson_url': lesson_detail_url,
                        'audio_url': 'not found',
                        'filename': refined_filename
                    })
            else:
                print(f"    Could not fetch detail page for '{lesson_title_from_listing}' at {lesson_detail_url}")

            # Be polite: add a small delay between fetching individual lesson pages.
            time.sleep(3) # Wait 3 seconds to avoid overwhelming the server (increased from 2)

        # Move to the next lesson listing page if a link was found.
        current_page_full_url = next_page_full_url
        if current_page_full_url:
            print(f"Moving to next lesson listing page: {current_page_full_url}")
            # Add a longer delay before moving to the next listing page.
            time.sleep(5) # Wait 5 seconds before next listing page request.
        else:
            print("No more listing pages to crawl. Crawl completed.")

    print("\n--- Final Crawling Summary ---")
    print(f"Total lessons with audio identified and attempted download: {len(all_lessons_summary)}")

    # Save a summary of all processed lessons to a JSON file in the download directory.
    summary_filename = os.path.join(DOWNLOAD_DIR, 'popup_chinese_audio_summary.json')
    try:
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(all_lessons_summary, f, indent=4, ensure_ascii=False)
        print(f"Detailed summary saved to {summary_filename}")
    except Exception as e:
        print(f"Error saving summary file: {e}")

# Entry point for the script when executed.
if __name__ == "__main__":
    main()