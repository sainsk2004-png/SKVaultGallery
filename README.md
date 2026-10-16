# SKVaultGallery

A local web-based media gallery for browsing, searching, previewing, and downloading files indexed from a Telegram channel.

## Features

- Browse indexed files in a web gallery
- Search filenames and captions
- Filter files by category
- Preview images
- Play supported videos in the browser
- Download selected files
- Cache media previews locally
- Store file metadata in SQLite

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Telethon
- SQLite
- HTML, CSS, and JavaScript

## Requirements

- Python 3.10 or newer
- Telegram API credentials
- Access to the Telegram channel being indexed

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/sainsk2004-png/SKVaultGallery.git
   cd SKVaultGallery
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file using `.env.example` and enter your own Telegram API credentials.

5. Run the indexing script when you are ready to index the configured channel:

   ```powershell
   python build_index.py
   ```

6. Start the web application:

   ```powershell
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```

7. Open http://127.0.0.1:8000 in your browser.

## Configuration

Configure your Telegram API ID and API hash in `.env`. Never commit real credentials or Telegram session files.

The application uses a local SQLite database and a preview cache. These files should be kept private and excluded from version control.

## Security Notes

- Do not publish `.env`.
- Do not publish Telegram session files.
- Do not commit your local database or cached media.
- Only access and download content you are authorized to use.

## Project Status

Core gallery functionality has been tested locally, including file search, image previews, video playback, and downloads.

## License

Choose a license before distributing this project. Until then, no reuse permissions are explicitly granted.

