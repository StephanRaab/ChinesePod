# How to Run the Popup Chinese Audio Downloader

This guide will walk you through setting up and executing the Python script from your command line.

## Step 1: Ensure Python is Installed

First, you'll need Python on your system.

- Check Installation: Open your command line (Terminal on macOS/Linux, Command Prompt or PowerShell on Windows) and type:

```bash
    python --version
    # or sometimes
    python3 --version
```

You should see a version number (e.g., Python 3.9.7).

- Install if Needed: If Python isn't found, download it from python.org/downloads/. On Windows, make sure to check "Add Python to PATH" during installation.
   

## Step 2: Install Required Libraries

Our script uses two external libraries: requests (for web requests) and BeautifulSoup4 (for HTML parsing).

    Open your command line.
    Run the following command to install them:

    ```Bash

    pip install requests beautifulsoup4
    # If 'pip' fails, try 'pip3':
    # pip3 install requests beautifulsoup4
    ```

    You'll see messages confirming the successful installation of these packages.

## Step 3: Open Your Command Line / Terminal

    Windows: Search for "cmd" or "PowerShell" in the Start Menu and open it.

    macOS: Go to Applications > Utilities > Terminal.

    Linux: Open your preferred terminal emulator.

## Step 5: Navigate to the Script's Directory

`cd` to the directory this file is in `popup_chinese_crawler.py`.

## Step 6: Run the Python Script

Once you're in the correct directory, execute the script:
Bash

```python
python popup_chinese_crawler.py
```
If 'python' doesn't work, try 'python3':
`python3 popup_chinese_crawler.py`

What to Expect When Running:

    Console Output: The script will print messages to your terminal, showing its progress: which lesson listing pages it's visiting, which individual lessons it's found, and the status of audio downloads (downloading or skipping if already exists).
    New Folder: A new folder named popup_chinese_audio will be created in the same directory as your script.
    Downloaded Files: Inside popup_chinese_audio, you'll find the MP3 audio files, named clearly based on the lesson titles.
    Summary File: A popup_chinese_audio_summary.json file will also be saved in the popup_chinese_audio folder. This file contains a JSON summary of all the lessons the script processed, including their original URL, audio URL, and final filename.
