import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import time # For adding delays
import json # For saving the summary

# --- Configuration ---
# Base URL for the Wayback Machine archive.
# This ensures all constructed URLs (relative links) correctly point to the archive.
BASE_ARCHIVE_URL = "https://web.archive.org"

# The specific archived URL of the lesson listing page.
# We're starting from page 1 as it's common practice.
# This URL points to the "Absolute Beginners" category.
START_LESSONS_PATH = "/web/20221129182300/https://popupchinese.com/lessons/absolute-beginners?page=4"

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
    Selectors in this function are specifically tailored to the provided HTML for listing pages.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    lessons_on_page = []
    next_page_link = None

    # --- 1. Find Lesson Items ---
    # Each lesson block is contained within a <div> with the class 'archive_teaser'.
    lesson_elements = soup.select('div.archive_teaser')
    if not lesson_elements:
        print("Warning: No 'archive_teaser' lesson elements found on this listing page. Check selector or page content.")

    for item in lesson_elements:
        # --- 1a. Find Lesson Title and URL within each lesson item ---
        # The direct link to the lesson page and its title are found in an <a> tag
        # within a <div> with class 'archive_title'.
        lesson_link_tag = item.select_one('div.archive_title a')
        
        if lesson_link_tag and lesson_link_tag.get('href'):
            title = lesson_link_tag.get_text(strip=True)
            # urljoin correctly constructs an absolute URL from a relative one.
            lesson_url = urljoin(current_page_url, lesson_link_tag['href'])
            lessons_on_page.append({'title': title, 'url': lesson_url})

    # --- 2. Find the "Next Page" Link ---
    # The pagination links are located within a <div> with class 'paginator' and id 'paginator'.
    paginator_div = soup.select_one('div.paginator#paginator')
    if paginator_div:
        # Find the currently selected page link (e.g., '2' with class 'selected').
        current_page_tag = paginator_div.select_one('a.selected')
        if current_page_tag:
            try:
                current_page_num = int(current_page_tag.get_text(strip=True))
                # Calculate the next page number.
                next_page_num = current_page_num + 1
                # Find the <a> tag whose text content is the next page number.
                next_link_tag = paginator_div.find('a', string=str(next_page_num))
                
                if next_link_tag and next_link_tag.get('href'):
                    absolute_next_url = urljoin(current_page_url, next_link_tag['href'])
                    # Basic check to ensure it's not linking back to the current page
                    # (important with Wayback Machine URLs that can be complex).
                    if absolute_next_url != current_page_url:
                        parsed_current = urlparse(current_page_url)
                        parsed_next = urlparse(absolute_next_url)
                        # If paths and queries are identical, it's not a truly distinct next page.
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
    This function's selectors are tailored to the provided HTML for detail pages.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    audio_url = None

    # The audio player is within an <audio> tag.
    audio_tag = soup.find('audio') 
    
    if audio_tag:
        # The actual audio source URL is within a <source> tag inside the <audio> tag.
        source_tag = audio_tag.find('source')
        if source_tag and source_tag.get('src'):
            audio_url = source_tag['src']
        # Fallback if the src attribute was directly on the <audio> tag itself (less common when <source> is used).
        elif audio_tag.get('src'): 
            audio_url = audio_tag['src']

    if audio_url:
        # Convert relative audio URLs to absolute URLs using the lesson detail page's URL as base.
        return urljoin(lesson_detail_url, audio_url)
        
    return None

def download_file(url, folder, filename):
    """
    Downloads a file from a given URL and saves it to a specified local folder.
    Includes basic error handling and a check to skip existing files.
    """
    filepath = os.path.join(folder, filename)
    
    # Skip download if the file already exists locally.
    if os.path.exists(filepath):
        print(f"  - Skipping: {filename} already exists in {folder}.")
        return

    max_retries = 3
    retry_delay = 2  # seconds
    
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
            print(f"  - Successfully downloaded: {filename}")
            return  # Success, exit the retry loop
            
        except requests.exceptions.HTTPError as e:
            if r.status_code == 404:
                print(f"  - Audio file not found in archive for {filename} (404 error)")
                return  # Don't retry 404s - the file simply doesn't exist in the archive
            else:
                print(f"  - HTTP error downloading {filename} (attempt {attempt + 1}): {e}")
        except requests.exceptions.RequestException as e:
            print(f"  - Network error downloading {filename} (attempt {attempt + 1}): {e}")
        except Exception as e:
            print(f"  - Unexpected error downloading {filename} (attempt {attempt + 1}): {e}")
    
    print(f"  - Failed to download {filename} after {max_retries} attempts")

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
    # Start the crawling process from the initial lessons listing page.
    current_page_full_url = urljoin(BASE_ARCHIVE_URL, START_LESSONS_PATH)
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
            # This might happen if a page is unexpectedly empty or a selector is subtly wrong.

        # Process each lesson found on the current listing page.
        for lesson_info in lessons_on_current_page:
            lesson_title_from_listing = lesson_info['title'] # Title extracted from the listing page.
            lesson_detail_url = lesson_info['url'] # URL to the individual lesson detail page.
            print(f"  - Found lesson in listing: '{lesson_title_from_listing}' at {lesson_detail_url}")

            # Fetch the HTML content of the individual lesson detail page.
            lesson_html = get_page_content(lesson_detail_url)
            if lesson_html:
                lesson_detail_soup = BeautifulSoup(lesson_html, 'html.parser')
                
                # --- Extract the specific lesson title from the detail page for accurate filename ---
                # Based on the provided HTML: <div class="lesson_title">...</div>
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
                    print(f"    Warning: Main lesson title 'div.lesson_title' not found on {lesson_detail_url}. Using title from listing page.")

                # --- Extract the Audio Link from the lesson detail page ---
                audio_link = parse_lesson_page_for_audio(lesson_html, lesson_detail_url)
                if audio_link:
                    # Sanitize the title and prepare the filename.
                    sanitized_name = sanitize_filename(lesson_title_for_file)
                    # Add lesson details to the summary list.
                    all_lessons_summary.append({
                        'title': lesson_title_for_file, # Store the potentially more accurate title.
                        'lesson_url': lesson_detail_url,
                        'audio_url': audio_link,
                        'filename': sanitized_name
                    })
                    # Download the audio file.
                    download_file(audio_link, DOWNLOAD_DIR, sanitized_name)
                else:
                    print(f"    No audio found for '{lesson_title_for_file}' at {lesson_detail_url}")
            else:
                print(f"    Could not fetch detail page for '{lesson_title_from_listing}' at {lesson_detail_url}")

            # Be polite: add a small delay between fetching individual lesson pages.
            time.sleep(2) # Wait 2 seconds to avoid overwhelming the server.

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