import os
import re
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus

# --- Configuration from Environment Variables ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", 0)) # Your Telegram User ID
SUPPORT_LINK = os.environ.get("SUPPORT_LINK", "https://t.me/YourSupportGroup") # Support Group Link

# --- Initialize Bot ---
app = Client(
    "mention_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins") # Optional: if you want to use plugins folder
)

# --- Helper Functions ---
async def is_admin(bot, chat_id, user_id):
    """Check if a user is an admin or owner of the group."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

# --- Message Handlers ---

# 1. Handler for /start command in private chat
@app.on_message(filters.private & filters.command("start"))
async def start_command(bot, message):
    user = message.from_user.first_name
    buttons = [
        [InlineKeyboardButton("👑 Owner", url=f"tg://user?id={OWNER_ID}")],
        [InlineKeyboardButton("🆘 Support", url=SUPPORT_LINK)],
        [InlineKeyboardButton("➕ Add me to your Group", url=f"https://t.me/{bot.me.username}?startgroup=true")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        f"Hello {user}! 👋\n\nI am a group management bot. I can mention all members in a group.\n\nUse /all or @all in a group to mention everyone!",
        reply_markup=reply_markup
    )

# 2. Handler when bot is added to a new group
@app.on_message(filters.new_chat_members & filters.group)
async def welcome_new_group(bot, message):
    # Check if the bot itself is the new member
    if message.new_chat_members[0].id == bot.me.id:
        buttons = [
            [InlineKeyboardButton("👑 Owner", url=f"tg://user?id={OWNER_ID}")],
            [InlineKeyboardButton("🆘 Support", url=SUPPORT_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            f"Thanks for adding me to **{message.chat.title}**! 🎉\n\nUse /all or @all to mention all members.\nI am here to help!",
            reply_markup=reply_markup
        )

# 3. Handler for /all and @all commands (only in groups)
@app.on_message(filters.group & (filters.command("all") | filters.regex(r"@all")))
async def mention_all(bot, message):
    # Check if the command is a reply to a message
    replied_msg = message.reply_to_message
    if not replied_msg:
        await message.reply_text("ℹ️ Please reply to a message with /all or @all to mention everyone.")
        return

    # Check if the user is an admin (or owner)
    user_id = message.from_user.id
    if not await is_admin(bot, message.chat.id, user_id):
        await message.reply_text("⚠️ Only admins can use this command.")
        return

    # Notify that the process is starting
    status_msg = await message.reply_text("🔄 Fetching members and mentioning them...")

    try:
        members = []
        async for member in bot.get_chat_members(message.chat.id):
            # Exclude the bot itself and potentially excluded users (you can add logic here)
            if member.user.id != bot.me.id:
                members.append(member.user.mention())

        if not members:
            await status_msg.edit_text("❌ No members found to mention.")
            return

        # Split the mentions into chunks to avoid Telegram's message length limit
        chunk_size = 50 # Send 50 mentions per message
        for i in range(0, len(members), chunk_size):
            chunk = members[i:i+chunk_size]
            text_to_send = " ".join(chunk) # Combine mentions with spaces

            # Delete the command message and reply with mentions
            await message.delete()
            await message.reply_text(text_to_send, disable_web_page_preview=True)

        await status_msg.delete() # Delete the status message after completion

    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred: {e}")

# 4. Admin command for the bot to leave a group
@app.on_message(filters.command("leave") & filters.user(OWNER_ID))
async def leave_chat_command(bot, message):
    if len(message.command) == 1:
        await message.reply_text("ℹ️ Please provide a chat id: `/leave -100123456789`")
        return

    chat_id = message.command[1]
    try:
        chat_id = int(chat_id)
    except ValueError:
        await message.reply_text("❌ Invalid chat ID format.")
        return

    try:
        await bot.send_message(chat_id, "👋 My admin asked me to leave this group. Goodbye!")
        await bot.leave_chat(chat_id)
        await message.reply_text(f"✅ Left chat: `{chat_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Failed to leave chat: {e}")

# --- Run the Bot ---
print("Bot is starting...")
app.run()
