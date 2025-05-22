import os
import random
import json
import datetime
import asyncio
import re
from pathlib import Path
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest

TOKEN = "7546360344:AAGgQHNmUuKY2K8LFKFhS-lHolyjbmM3d3c"
ADMIN_ID = 7882844007
KEY_PREFIX = "ZenGod-"

ACCESS_FILE = "access.json"
SEARCH_RESULTS_DIR = Path("/storage/emulated/0/Download/Logs/Search")
USER_DROPS_DIR = Path("/storage/emulated/0/Download/Logs/user")
LOGS_DIR = Path("/storage/emulated/0/Download/Logs/")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MAX_SEARCH_LINES = 100

def setup_directories():
    try:
        SEARCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)
        USER_DROPS_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)
        LOGS_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)
        DATABASE_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)
        print("Directories created with proper permissions")
    except Exception as e:
        print(f"Error creating directories: {e}")
        raise

SEARCH_CATEGORIES = {
    "ML": "mtacc.mobilelegends.com",
    "CODM": {
        "Gaslite": "garena.gaslite"
        },
    "Roblox": "roblox.com",
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "TikTok": "tiktok.com",
    "Youtube": "youtube.com",
    "Netflix": "netflix.com",
    "Spotify": "spotify.com",
    "Paypal": "paypal.com",
    "Discord": "discord.com",
    "Twitter": "twitter.com",
    "Microsoft": "microsoft.com",
    "Onlyfans": "onlyfans.com"
}

DATABASE_FILES = {
    "CODM": "Cod.txt",
    "ML": "Ml.txt",
    "Ml/User-pass": "Ml1.txt",
     "100082": "100082.txt",
}

DATABASE_DIR = Path("/storage/emulated/0/Download/database")
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

USER_ACCESS = {}
USER_STATS = {}  
ACCESS_KEYS = {}
USED_KEYS = set()

AWAITING_KEY_INPUT = set()
AWAITING_REVOKE_USER = set()
AWAITING_ANNOUNCEMENT = set()

def load_access():
    global USER_ACCESS, USER_STATS, ACCESS_KEYS, USED_KEYS
    if os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "r") as f:
            try:
                data = json.load(f)
                USER_ACCESS = {int(k): (v if v is None else float(v)) for k, v in data.get("user_access", {}).items()}
                USER_STATS = data.get("user_stats", {})
                USER_STATS = {int(k): v for k, v in USER_STATS.items()}
                ACCESS_KEYS = data.get("access_keys", {})
                USED_KEYS = set(data.get("used_keys", []))
            except json.JSONDecodeError:
                print(f"Error decoding {ACCESS_FILE}. Initializing with empty objects.")
                USER_ACCESS = {}
                USER_STATS = {}
                ACCESS_KEYS = {}
                USED_KEYS = set()
    else:
        USER_ACCESS = {}
        USER_STATS = {}
        ACCESS_KEYS = {}
        USED_KEYS = set()

def save_access():
    data = {
        "user_access": {str(k): v for k, v in USER_ACCESS.items()},
        "user_stats": {str(k): v for k, v in USER_STATS.items()},
        "access_keys": ACCESS_KEYS,
        "used_keys": list(USED_KEYS)
    }
    with open(ACCESS_FILE, "w") as f:
        json.dump(data, f)

async def delete_generated_file(file_path):
    try:
        await asyncio.sleep(3)
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, 0o777)
            except:
                pass
            os.remove(file_path)
            print(f"File {file_path} deleted successfully.")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        keyboard = [
            ["📂 Generate Files", "🔍 Search"],
            ["🌟 Use Access Key"],
            ["🔑 Generate Key"],
            ["📊 Stats", "📣 Send Announcement", "🔴 Revoke Key"]
        ]
    else:
        keyboard = [
            ["📂 Generate Files", "🔍 Search"],
            ["🌟 Use Access Key"]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        f"👋 Welcome, {user.first_name}!\n\n"
        "🔒 Note: Only authorized users can use this bot.\n"
        "💬 Contact @ZenzOfficial to buy access."
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def generate_key(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ *Admin only!*", parse_mode="Markdown")
        return

    await update.message.reply_text("Send duration to generate the key", parse_mode="Markdown")
    context.user_data["awaiting_key_time"] = True

async def handle_key_time(update: Update, context: CallbackContext):
    if not context.user_data.get("awaiting_key_time"):
        return

    duration_text = update.message.text.strip().lower()
    if duration_text == "lifetime":
        expires_at = None
        expiry_text = "Lifetime"
    else:
        match = re.match(r"(\d+)([smhd])", duration_text)
        if not match:
            await update.message.reply_text("⚠️ *Invalid format! Use formats like `10s`, `5m`, `2h`, `1d`, or `lifetime`*", parse_mode="Markdown")
            context.user_data["awaiting_key_time"] = False
            return

        value, unit = int(match[1]), match[2]
        time_multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=value * time_multipliers[unit])).timestamp()
        expiry_text = f"{value}{unit}"

    key = f"{KEY_PREFIX}{random.randint(100000, 999999)}"

    context.user_data["awaiting_key_time"] = False

    key_generated_message = (
        f"🌟 Key Generated!\n"
        f"🔑 Key: `{key}`\n"
        f"⏳ Validity: {expiry_text}\n"
        f"📝 Note: One-Time Use Only!"
    )

    await update.message.reply_text(key_generated_message, parse_mode="Markdown")

    ACCESS_KEYS[key] = {"expires_at": expires_at}
    save_access()
    
async def handle_enter_key(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in AWAITING_KEY_INPUT:
        return

    key = update.message.text.strip()
    
    if key in ACCESS_KEYS:
        key_data = ACCESS_KEYS[key]
        if key_data["expires_at"] and key_data["expires_at"] < datetime.datetime.now().timestamp():
            del ACCESS_KEYS[key]
            await update.message.reply_text("❌ *Key expired!*")
            return
        
        USER_ACCESS[user_id] = key_data["expires_at"]
        if user_id not in USER_STATS:
            USER_STATS[user_id] = {"generations": 0}
       
        del ACCESS_KEYS[key]
        USED_KEYS.add(key)
        save_access()

        if key_data["expires_at"] is None:
            duration = "Lifetime"
            expiration_time = "Lifetime"
        else:
            remaining_time = key_data["expires_at"] - datetime.datetime.now().timestamp()
            days = int(remaining_time // 86400)
            hours = int((remaining_time % 86400) // 3600)
            minutes = int((remaining_time % 3600) // 60)
            expiration_time = datetime.datetime.fromtimestamp(key_data["expires_at"]).strftime("%Y-%m-%d %H:%M:%S")
            duration = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        access_granted_message = (
            f"🌟 Access Granted!✅\n\n"
            f"🔐 Key Info: {duration}\n"
            f"⏳ Valid Until: {expiration_time}\n"
            f"🌟 Thank you"
        )

        await update.message.reply_text(access_granted_message, parse_mode="Markdown")
        AWAITING_KEY_INPUT.discard(user_id)
    elif key in USED_KEYS:
        await update.message.reply_text(
            "🌟 Oops!!!\n\n"
            "🌟 Used Key\n"
            "📢 Buy Access? Dm @ZenzOfficial"
        )
        AWAITING_KEY_INPUT.discard(user_id)
    else:
        await update.message.reply_text("❌ *Invalid key!*")
        AWAITING_KEY_INPUT.discard(user_id)

async def prompt_for_key(update: Update, context: CallbackContext):
    AWAITING_KEY_INPUT.add(update.message.from_user.id)
    await update.message.reply_text("🌟 Please Send Your Access Key.")

def has_access(user_id):
    if user_id not in USER_ACCESS:
        return False
    if USER_ACCESS[user_id] is None:
        return True
    return USER_ACCESS[user_id] > datetime.datetime.now().timestamp()

async def generate_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not has_access(user_id):
        await update.message.reply_text("🌟 You do not have Access")
        return

    keyboard = [[InlineKeyboardButton("🗄️ Database", callback_data="database_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗃️ *Choose an option:*", parse_mode="Markdown", reply_markup=reply_markup)

async def database_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎮 CODM", callback_data="generate:CODM"),
         InlineKeyboardButton("🎮 ML", callback_data="generate:ML")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📂 *Select a database:*", parse_mode="Markdown", reply_markup=reply_markup)

async def generate_file(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    try:
        await query.answer()  

        if not has_access(user_id):
            await query.message.edit_text("😞 You do not have access!")
            return

        _, game = query.data.split(":")
        file_name = DATABASE_DIR / DATABASE_FILES.get(game)

        if not file_name.exists():
            await query.message.edit_text(f"❌ Database file for {game} not found!")
            return

        if file_name.stat().st_size == 0:
            await query.message.edit_text(f"❌ Database for {game} is empty!")
            return

        message = await query.message.edit_text("⭐ Connecting to the Database")
        for i in range(1, 4):
            new_text = f"⭐ Connecting to the Database{'.' * i}"
            try:
                await message.edit_text(new_text)
            except BadRequest:
                pass  
            await asyncio.sleep(1)

        await message.edit_text("🌟 Initializing TxT")
        for i in range(1, 4):
            new_text = f"🌟 Initializing TxT{'.' * i}"
            try:
                await message.edit_text(new_text)
            except BadRequest:
                pass
            await asyncio.sleep(1)

        await message.edit_text("📂 File Ready!")
        await asyncio.sleep(1)

        with open(file_name, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        if not all_lines:
            await query.message.edit_text(f"❌ Database for {game} is empty!")
            return

        selected_lines = random.sample(all_lines, min(100, len(all_lines)))
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result_file = f"🌟ρяємιυм_{game}.txt"

        with open(result_file, "w", encoding="utf-8") as f:
            f.write(f"Generated Data\nDate & Time: {timestamp}\nGame: {game}\n\n")
            f.writelines(selected_lines)

        with open(result_file, "rb") as f:
            caption = (
                f"📂Premium File Generated!📂\n"
                f"💸Source: {game}\n"
                f"📄Lines: {len(selected_lines)}\n"
                f"🕓Date: {timestamp}\n"
                f"🫶Thank you for using our service!"
            )
            await query.message.reply_document(document=f, caption=caption, parse_mode="Markdown")

        USER_STATS.setdefault(user_id, {"generations": 0})
        USER_STATS[user_id]["generations"] += 1
        save_access()

        await message.delete()
        await delete_generated_file(result_file)

    except Exception as e:
        print(f"Error in generate_file: {str(e)}")
        await query.message.edit_text(f"❌ Failed to generate file: {str(e)}")

async def search_menu(update: Update, context: CallbackContext):
    if not has_access(update.message.from_user.id):
        await update.message.reply_text("🌟 You do not have Access")
        return

    keyboard = [
        [InlineKeyboardButton("🔎 Search Category", callback_data="search_category")],
        [InlineKeyboardButton("🔍 Keyword Search", callback_data="keyword_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔍 Choose search type:", reply_markup=reply_markup)

async def select_search_category(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    row = []
    
    for category, value in SEARCH_CATEGORIES.items():
        if isinstance(value, dict):  
            btn = InlineKeyboardButton(f"🎮 {category} ›", callback_data=f"cat_menu:{category}")
        else:
            btn = InlineKeyboardButton(category, callback_data=f"search_cat:{category}")
        
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row: 
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📂 Select a category to search:", reply_markup=reply_markup)

async def show_codm_subcategories(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    _, category = query.data.split(":")
    subcategories = SEARCH_CATEGORIES.get(category, {})
    
    keyboard = []
    row = []
    
    for sub_name, sub_value in subcategories.items():
        row.append(InlineKeyboardButton(sub_name, callback_data=f"search_cat:{category}:{sub_name}"))
        if len(row) == 1:  
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="search_category")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"🎮 {category} - Select subcategory:", reply_markup=reply_markup)

async def handle_search_request(update: Update, context: CallbackContext, search_type, query=None):
    """Handle search requests from both callback queries and text messages"""
    try:

        context.user_data["search_messages"] = []
        
        if update.callback_query:
            message = update.callback_query.message
        else:
            message = update.message
        
        context.user_data["search_messages"].append(message)
        
        prompt_msg = await message.reply_text(
            f"🔍 How many lines to retrieve? (Max {MAX_SEARCH_LINES})"
        )
        context.user_data["search_messages"].append(prompt_msg)
        
        context.user_data["search_type"] = search_type
        context.user_data["search_query"] = query
        context.user_data["awaiting_lines"] = True
        
    except Exception as e:
        print(f"Error in handle_search_request: {e}")
        error_msg = await update.effective_message.reply_text("❌ Failed to start search")
        await asyncio.sleep(3)
        try:
            await error_msg.delete()
        except:
            pass

async def handle_lines_input(update: Update, context: CallbackContext):
    if not context.user_data.get("awaiting_lines"):
        return
    
    try:
        lines = int(update.message.text)
        if lines < 1 or lines > MAX_SEARCH_LINES:
            raise ValueError
    except ValueError:
        msg = await update.message.reply_text(f"❌ Please enter a number between 1 and {MAX_SEARCH_LINES}")
        context.user_data["search_messages"].append(msg)
        return
    
    context.user_data["lines"] = lines
    context.user_data["awaiting_lines"] = False
    
    keyboard = [
        [InlineKeyboardButton("✅ Keep URLs", callback_data="urls:keep")],
        [InlineKeyboardButton("❌ Remove URLs", callback_data="urls:remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text("🖇️ Handle URLs in results:", reply_markup=reply_markup)
    context.user_data["search_messages"].append(msg)
    context.user_data["search_messages"].append(update.message) 

async def execute_search(update: Update, context: CallbackContext, keep_urls):
    query = update.callback_query
    await query.answer()
    
    try:
        if "search_messages" not in context.user_data:
            context.user_data["search_messages"] = []
        
        context.user_data["search_messages"].extend([
            query.message,  
            update.effective_message
        ])
        
        search_type = context.user_data["search_type"]
        search_query = context.user_data["search_query"]
        lines = context.user_data["lines"]
        
        searching_msg = await query.message.reply_text("🔍 Searching...")
        context.user_data["search_messages"].append(searching_msg)
        
        search_results = await perform_search(search_type, search_query, lines, keep_urls)
        
        if not search_results:
            await searching_msg.edit_text("❌ No results found")
            await asyncio.sleep(3)
            await delete_search_messages(context)
            return
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_query = re.sub(r'[^\w\-_. ]', '_', str(search_query or search_type))
        result_filename = f"{safe_query}.txt"
        result_file = SEARCH_RESULTS_DIR / result_filename
        
        with open(result_file, "w", encoding="utf-8") as f:
            f.writelines(search_results)
       
        with open(result_file, "rb") as f:
            await query.message.reply_document(
                document=f,
                caption=f"🔍 Found {len(search_results)} matching lines"
            )
        
        await delete_search_messages(context)
        
    except Exception as e:
        error_msg = await query.message.reply_text(f"❌ Search failed: {str(e)}")
        await asyncio.sleep(3)
        try:
            await error_msg.delete()
        except:
            pass

async def delete_search_messages(context: CallbackContext):
    """Delete only search process messages (not results)"""
    if "search_messages" not in context.user_data:
        return
    
    for msg in context.user_data["search_messages"]:
        try:
            if hasattr(msg, 'delete'):
                await msg.delete()
            elif hasattr(msg, 'message_id'):
                await context.bot.delete_message(
                    chat_id=msg.chat.id,
                    message_id=msg.message_id
                )
        except Exception as e:
            print(f"Couldn't delete message: {e}")
    
    context.user_data["search_messages"] = []
    
async def cleanup_old_files(context: CallbackContext):
    """Delete result files older than 24 hours"""
    cutoff = time.time() - 24*3600
    for file in SEARCH_RESULTS_DIR.glob("*.txt"):
        if os.path.getmtime(file) < cutoff:
            try:
                os.remove(file)
            except:
                pass
                
async def perform_search(search_type, query, max_lines, keep_urls):
    results = []
    
    def search_file(file_path):
        nonlocal results
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if len(results) >= max_lines:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    if query.lower() in line.lower():
                        if not keep_urls:
                            line = extract_credentials(line)
                            if ':' in line and '@' in line.split(':')[0]:
                                results.append(line + "\n")
                        else:
                            results.append(line + "\n")
        except Exception as e:
            print(f"Error searching {file_path}: {e}")
    
    files = list(LOGS_DIR.glob("*.txt"))
    
    with ThreadPoolExecutor(max_workers=500) as executor:
        executor.map(search_file, files)
    
    return results[:max_lines]

def extract_credentials(line):
    """Extracts credentials from various URL formats"""
    clean_line = re.sub(r'^(https?://|//)?([^/]+/)?', '', line)
    
    parts = re.split(r'[:/]', clean_line.strip())
    
    if len(parts) >= 2:
        credentials = [p for p in parts if p][-2:]
        if len(credentials) == 2:
            return f"{credentials[0]}:{credentials[1]}"
   
    return line.strip()

    return line
    
async def revoke_key(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ *Admin only!*", parse_mode="Markdown")
        return

    await update.message.reply_text("Send the user ID to revoke access:", parse_mode="Markdown")
    AWAITING_REVOKE_USER.add(update.message.from_user.id)

async def handle_revoke_user(update: Update, context: CallbackContext):
    if update.message.from_user.id not in AWAITING_REVOKE_USER:
        return

    user_id = update.message.text.strip()
    try:
        user_id = int(user_id)
        if user_id in USER_ACCESS:
            del USER_ACCESS[user_id]
            if user_id in USER_STATS:
                del USER_STATS[user_id]
            save_access()
            await update.message.reply_text(f"✅ Access revoked for user {user_id}")
        else:
            await update.message.reply_text("❌ User not found in database")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please send a numeric ID")
    
    AWAITING_REVOKE_USER.discard(update.message.from_user.id)

async def show_stats(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ *Admin only!*", parse_mode="Markdown")
        return

    if not USER_ACCESS:
        await update.message.reply_text("📊 No users in database")
        return

    stats_text = "📊 User Stats:\n\n"
    for user_id, expires_at in USER_ACCESS.items():
        generations = USER_STATS.get(user_id, {}).get("generations", 0)
        if expires_at is None:
            duration = "Lifetime"
        else:
            remaining = expires_at - datetime.datetime.now().timestamp()
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            minutes = int((remaining % 3600) // 60)
            duration = f"{days}d {hours}h {minutes}m"
        
        stats_text += f"👤 User ID: {user_id}\n"
        stats_text += f"📂 Files generated: {generations}\n"
        stats_text += f"⏳ Access duration: {duration}\n\n"

    await update.message.reply_text(stats_text)

async def send_announcement(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ *Admin only!*", parse_mode="Markdown")
        return

    await update.message.reply_text("📢 Send the announcement message:")
    AWAITING_ANNOUNCEMENT.add(update.message.from_user.id)

async def handle_announcement(update: Update, context: CallbackContext):
    if update.message.from_user.id not in AWAITING_ANNOUNCEMENT:
        return

    announcement = update.message.text
    users = list(USER_ACCESS.keys())
    
    await update.message.reply_text(f"📢 Sending announcement to {len(users)} users...")
    
    success = 0
    failed = 0
    
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=announcement)
            success += 1
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Announcement sent!\n"
        f"✔ Success: {success}\n"
        f"✖ Failed: {failed}"
    )
    
    AWAITING_ANNOUNCEMENT.discard(update.message.from_user.id)

async def callback_handler(update: Update, context: CallbackContext):
    """Handle all callback queries"""
    try:
        query = update.callback_query
        await query.answer()
        
        if "search_messages" not in context.user_data:
            context.user_data["search_messages"] = []
        context.user_data["search_messages"].append(query.message)
        
        if query.data == "database_menu":
            await database_menu(update, context)
        elif query.data.startswith("generate:"):
            await generate_file(update, context)
        elif query.data == "search_category":
            await select_search_category(update, context)
        elif query.data.startswith("cat_menu:"):
            await show_codm_subcategories(update, context)
        elif query.data.startswith("search_cat:"):
            parts = query.data.split(":")
            if len(parts) == 3:  
                category, sub_name = parts[1], parts[2]
                if isinstance(SEARCH_CATEGORIES[category], dict):
                    search_query = SEARCH_CATEGORIES[category][sub_name]
                    print(f"Searching for subcategory: {sub_name}, query: {search_query}")
                else:
                    search_query = SEARCH_CATEGORIES[category]
            else:
                category = parts[1]
                search_query = SEARCH_CATEGORIES[category]
                print(f"Searching for category: {category}, query: {search_query}")
            
            await handle_search_request(update, context, "category", search_query)
        elif query.data == "keyword_search":
            await query.message.edit_text("🔍 Enter keyword to search:")
            context.user_data["awaiting_keyword"] = True
        elif query.data.startswith("urls:"):
            keep_urls = query.data.split(":")[1] == "keep"
            await execute_search(update, context, keep_urls)
            
    except Exception as e:
        print(f"Error in callback_handler: {e}")
        error_msg = await update.effective_message.reply_text(f"❌ An error occurred: {str(e)}")
        await asyncio.sleep(3)
        try:
            await error_msg.delete()
        except:
            pass

async def handle_menu_selection(update: Update, context: CallbackContext):
    """Handle all menu selections and text inputs"""
    try:
        text = update.message.text
        user_id = update.message.from_user.id

        if context.user_data.get("awaiting_key_time"):
            await handle_key_time(update, context)
            return

        if user_id in AWAITING_KEY_INPUT:
            await handle_enter_key(update, context)
            return
            
        if user_id in AWAITING_REVOKE_USER:
            await handle_revoke_user(update, context)
            return
            
        if user_id in AWAITING_ANNOUNCEMENT:
            await handle_announcement(update, context)
            return

        if context.user_data.get("awaiting_keyword"):
            await handle_search_request(update, context, "keyword", update.message.text)
            context.user_data["awaiting_keyword"] = False
            return

        if context.user_data.get("awaiting_lines"):
            await handle_lines_input(update, context)
            return

        if text == "🔑 Generate Key":
            await generate_key(update, context)
        elif text == "🌟 Use Access Key":
            await prompt_for_key(update, context)
        elif text == "📂 Generate Files":
            await generate_menu(update, context)
        elif text == "🔍 Search":
            await search_menu(update, context)
        elif text == "🔴 Revoke Key" and user_id == ADMIN_ID:
            await revoke_key(update, context)
        elif text == "📊 Stats" and user_id == ADMIN_ID:
            await show_stats(update, context)
        elif text == "📣 Send Announcement" and user_id == ADMIN_ID:
            await send_announcement(update, context)
        else:
            msg = await update.message.reply_text("❓ Unknown option.")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except:
                pass

    except Exception as e:
        print(f"Error in handle_menu_selection: {e}")
        error_msg = await update.message.reply_text("❌ An error occurred")
        await asyncio.sleep(3)
        try:
            await error_msg.delete()
        except:
            pass
            
  
def main():
    """Main application setup"""
    load_access()
    app = Application.builder().token(TOKEN).build()
    async def error_handler(update: object, context: CallbackContext) -> None:
        print(f"Update {update} caused error {context.error}")
        if update and hasattr(update, 'effective_message'):
            msg = await update.effective_message.reply_text("⚠️ An error occurred")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except:
                pass
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_error_handler(error_handler)

    print("Bot is running")
    app.run_polling()

if __name__ == "__main__":
    main()