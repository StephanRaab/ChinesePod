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
START_LESSONS_PATH = "/web/20221129182300/https://popupchinese.com/lessons/absolute-beginners?page=1"

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
        lesson_link_tag = item.select_one('div.archive_title a.black.nonlink')
        
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
        # Convert relative audio URLs to absolute URLs using
