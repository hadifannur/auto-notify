# Auto-Notify Usage Guide

## Overview
This project automates notifications for completed tasks in the POC Round by integrating with Feishu/Lark Sheets and Lark group chat.

## Prerequisites
- Python 3.7+
- Feishu/Lark developer account (for API credentials)
- Access to the target Lark group chat
- Git (optional, for version control)

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/hadifannur/auto-notify.git
   cd auto-notify
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   - Copy `.env.example` to `.env` (if provided) or create a `.env` file with the following keys:
     - `KL_TRACKER_SHEET` - Spreadsheet token
     - `SHEET_ID` - Sheet ID
     - `APP_ID` - Feishu/Lark app ID
     - `APP_SECRET` - Feishu/Lark app secret
     - `QA_CHAT_ID` - Lark group chat ID
     - `USER_ACCESS_TOKEN` - (optional, for user-level chat fetch)
     - `CHAT_ID` - (optional, for user-level chat fetch)

## How to Use
1. **Run the script:**
   ```sh
   python run.py
   ```
2. The script will:
   - Fetch tasks marked as 'POC Round' from the configured spreadsheet.
   - Search for these tasks in the specified Lark group chat.
   - Send a notification to the group chat listing completed tasks and prompting for review/update.

## Notes
- If your user access token expires, the script will prompt you to re-authenticate via OAuth.
- The `.env` file should be kept secret and is excluded from git by default.
- You can customize the notification message in `run.py` if needed.

## Troubleshooting
- Ensure all environment variables are set correctly in `.env`.
- Check your Feishu/Lark app permissions for Sheets and IM APIs.
- Review error messages in the terminal for API or authentication issues.

## License
MIT
