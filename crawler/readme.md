# How to Run the Popup Chinese Audio Downloader

This guide will walk you through setting up and executing the Python script from your command line.

## Step 1: Ensure Python is Installed

First, you'll need Python on your system.

- Check Installation: Open your command line (Terminal on macOS/Linux, Command Prompt or PowerShell on Windows) and type:

```bash    
    python3 --version
```

You should see a version number (e.g., Python 3.9.7).

- Install if Needed: If Python isn't found, download it from python.org/downloads/. On Windows, make sure to check "Add Python to PATH" during installation.
   

## Step 2: Install Required Libraries from the Command Line

Our script uses two external libraries: requests (for web requests) and BeautifulSoup4 (for HTML parsing).

    Open your command line.
    Create a virtual environment.

    ```bash
    python3 -m venv path/to/venv
    ```

    activate environment (on mac)
    
    ```bash
    source bin/activate
    ```

    Install libraries

    ```Bash
    pip3 install requests beautifulsoup4
    ```

    You'll see messages confirming the successful installation of these packages.

## Step 3: Run the Python Script

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
