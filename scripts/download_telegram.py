import os
import sys
import asyncio
from telethon import TelegramClient, functions, types
from telethon.errors import UserAlreadyParticipantError

# Add parent path to allow importing from config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

API_ID = settings.TELEGRAM_API_ID
API_HASH = settings.TELEGRAM_API_HASH

if not API_ID or not API_HASH:
    print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH are not set in .env")
    print("Please get them from https://my.telegram.org and add them.")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("ERROR: TELEGRAM_API_ID must be a numeric string.")
    sys.exit(1)

INVITE_LINK = "https://t.me/+rylm_W3YQWs3Y2E0"
HASH = "rylm_W3YQWs3Y2E0"
OUTPUT_DIR = os.path.join("data", "raw", "Saudi_Telegram")

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    print("Initializing Telegram Client...")
    # This will ask for phone number, login code, and 2FA password (if enabled) in the terminal
    client = TelegramClient('food_safety_session', API_ID, API_HASH)
    await client.start()
    
    print("\nAuthenticated successfully.")
    
    # Try using the invite link to join
    try:
        updates = await client(functions.messages.ImportChatInviteRequest(hash=HASH))
        print("Successfully joined chat through invite link.")
    except UserAlreadyParticipantError:
        print("Already a participant of the chat.")
    except Exception as e:
        print(f"Notice on joining (you might already be in it?): {e}")
        
    chat = None
    try:
        chat = await client.get_entity(INVITE_LINK)
        print(f"Target chat found: {chat.title}")
    except Exception as e:
        print(f"Could not get chat entity for the invite link: {e}")
        
    if not chat:
        print("Failed to access the chat. Make sure the link is correct and your account is not banned from it.")
        return
        
    print(f"Scraping files from group: {chat.title}")
    # Iterate through messages
    count = 0
    async for message in client.iter_messages(chat):
        if message.document:
            filename = None
            for attr in message.document.attributes:
                if isinstance(attr, types.DocumentAttributeFilename):
                    filename = attr.file_name
                    break
            
            if filename:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.pdf', '.docx', '.pptx', '.doc']:
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    if not os.path.exists(filepath):
                        print(f"Downloading '{filename}' ...")
                        try:
                            await client.download_media(message, filepath)
                            count += 1
                        except Exception as e:
                            print(f"  -> Failed to download: {e}")
                    else:
                        print(f"Skipping '{filename}', already exists in output folder.")

    print(f"\n==============================================")
    print(f"Finished evaluating messages. Downloaded {count} new files.")
    print(f"Files are located at: {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
