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

Step 2: Install Required Libraries

Our script uses two external libraries: requests (for web requests) and BeautifulSoup4 (for HTML parsing).

    Open your command line.
    Run the following command to install them:
    Bash

    pip install requests beautifulsoup4
    # If 'pip' fails, try 'pip3':
    # pip3 install requests beautifulsoup4

    You'll see messages confirming the successful installation of these packages.

Step 3: Save the Python Code

    Copy the entire Python script provided in our previous conversation.
    Paste it into a plain text editor (like Notepad, VS Code, Sublime Text, etc.).
    Save the file as popup_chinese_crawler.py.
        Choose a location you can easily navigate to, like a new folder on your Desktop (e.g., C:\Users\YourName\Desktop\PopupCrawler on Windows, or /Users/YourName/Desktop/PopupCrawler on macOS/Linux).

Step 4: Open Your Command Line / Terminal

    Windows: Search for "cmd" or "PowerShell" in the Start Menu and open it.
    macOS: Go to Applications > Utilities > Terminal.
    Linux: Open your preferred terminal emulator.

Step 5: Navigate to the Script's Directory

You need to tell your command line where the popup_chinese_crawler.py file is located. Use the cd (change directory) command.

    Example (Windows): If your file is in C:\Users\YourName\Desktop\PopupCrawler, type:
    Bash

cd C:\Users\YourName\Desktop\PopupCrawler

Example (macOS/Linux): If your file is in /Users/YourName/Desktop/PopupCrawler, type:
Bash

    cd /Users/YourName/Desktop/PopupCrawler

    Pro Tip: After typing cd (note the space!), you can often drag and drop the folder containing your script directly into the terminal window, and it will automatically paste the correct path.

Step 6: Run the Python Script

Once you're in the correct directory, execute the script:
Bash

python popup_chinese_crawler.py
# If 'python' doesn't work, try 'python3':
# python3 popup_chinese_crawler.py

What to Expect When Running:

    Console Output: The script will print messages to your terminal, showing its progress: which lesson listing pages it's visiting, which individual lessons it's found, and the status of audio downloads (downloading or skipping if already exists).
    New Folder: A new folder named popup_chinese_audio will be created in the same directory as your script.
    Downloaded Files: Inside popup_chinese_audio, you'll find the MP3 audio files, named clearly based on the lesson titles.
    Summary File: A popup_chinese_audio_summary.json file will also be saved in the popup_chinese_audio folder. This file contains a JSON summary of all the lessons the script processed, including their original URL, audio URL, and final filename.
