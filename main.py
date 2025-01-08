from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import asyncio
from datetime import datetime, timedelta
from create_vm import create_instance_with_public_ip
from delete_vm import delete_instance
import json
import os
from tender_search import perform_tender_search
import time
from dotenv import load_dotenv

load_dotenv()

# Define conversation states
WAITING_FOR_TOKEN, SELECTING_CLIENT = range(2)  # Added SELECTING_CLIENT state


class ProxyState:
    def __init__(self, state_file="proxy_state.json"):
        self.state_file = state_file
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'proxy_ip': None,
                'creation_time': None,
                'vm_running': False,
                'active_users': 0,
                'user_tokens': {}
            }

    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

    def update_proxy(self, ip):
        self.state['proxy_ip'] = ip
        self.state['creation_time'] = datetime.now().isoformat()
        self.state['vm_running'] = True
        self.state['active_users'] = 1
        self.save_state()

    def clear_proxy(self):
        self.state['proxy_ip'] = None
        self.state['creation_time'] = None
        self.state['vm_running'] = False
        self.state['active_users'] = 0
        self.save_state()

    def get_user_token(self, user_id):
        # Ensure the 'user_tokens' key exists
        if 'user_tokens' not in self.state:
            self.state['user_tokens'] = {}
            self.save_state()
        return self.state['user_tokens'].get(str(user_id))

    def set_user_token(self, user_id, token):
        # Ensure the 'user_tokens' key exists
        if 'user_tokens' not in self.state:
            self.state['user_tokens'] = {}
        self.state['user_tokens'][str(user_id)] = token
        self.save_state()

    def add_user(self):
        self.state['active_users'] += 1
        self.save_state()

    def remove_user(self):
        if self.state['active_users'] > 0:
            self.state['active_users'] -= 1
            self.save_state()

    def should_delete(self):
        if not self.state['creation_time'] or self.state['active_users'] > 0:
            return False
        creation_time = datetime.fromisoformat(self.state['creation_time'])
        return datetime.now() - creation_time > timedelta(minutes=30)

    def get_proxy_ip(self):
        return self.state['proxy_ip'] if self.state['vm_running'] else None


# Load configuration from environment variables
VM_CONFIG = {
    "project_id": os.getenv("PROJECT_ID"),
    "zone": os.getenv("ZONE"),
    "instance_name": os.getenv("INSTANCE_NAME"),
    "machine_type": os.getenv("MACHINE_TYPE"),
    "image_family": os.getenv("IMAGE_FAMILY"),
    "image_project": os.getenv("IMAGE_PROJECT"),
    "disk_size_gb": int(os.getenv("DISK_SIZE_GB")),
    "disk_type": os.getenv("DISK_TYPE"),
    "tags": os.getenv("TAGS").split(","),
    "startup_script_path": os.getenv("STARTUP_SCRIPT_PATH")
}

proxy_state = ProxyState()

clients = [
    "Jail Department - Gujarat State",
    "Jamnagar Area Development Authority",
    "Jamnagar Municipal Corporation",
    "Junagadh Municipal Corporation",
    "Labour and Employment Department",
    "Madhya Gujarat Vij Company Limited",
    "Nagarpalika (All Nagarpalika Gujarat)",
    "Narmada Water Resources",
    "National Forensic Sciences University",
    "National Institute of Design"
]


async def get_or_create_proxy():
    try:
        existing_ip = proxy_state.get_proxy_ip()
        if existing_ip:
            print("Using existing VM IP: ", existing_ip)
            proxy_state.add_user()
            return existing_ip

        print("Creating new VM instance...")
        external_ip = create_instance_with_public_ip(**VM_CONFIG)
        print("VM created with IP: ", external_ip)
        proxy_state.update_proxy(external_ip)
        await asyncio.sleep(20)  # Allow some time for VM to be fully operational
        return external_ip
    except Exception as e:
        print("Failed to initialize proxy server:", str(e))
        raise



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    token = proxy_state.get_user_token(user_id)

    if not token:
        await update.message.reply_text(
            "Welcome to Tender Bot! 🤖\n"
            "Before we begin, please provide your Scrapybara token."
        )
        return WAITING_FOR_TOKEN

    return await show_client_list(update, context)


async def token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    token = update.message.text.strip()
    user_id = update.effective_user.id

    proxy_state.set_user_token(user_id, token)

    try:
        await update.message.delete()
    except Exception:
        pass  # Ignore if message can't be deleted

    return await show_client_list(update, context)


# Changed return type to int
async def show_client_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton(client, callback_data=client)] for client in clients
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        "Please select a client to proceed:\n"
        "I will search for available works from https://tender.nprocure.com"
    )

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

    return SELECTING_CLIENT


async def finish_task(context: ContextTypes.DEFAULT_TYPE):
    """Mark task as complete by removing user"""
    proxy_state.remove_user()
    if proxy_state.should_delete():
        try:
            delete_instance(
                project_id=VM_CONFIG['project_id'],
                zone=VM_CONFIG['zone'],
                instance_name=VM_CONFIG['instance_name']
            )
            proxy_state.clear_proxy()
        except Exception as e:
            print(f"Error during VM cleanup: {e}")


async def cleanup_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic cleanup check"""
    if proxy_state.should_delete():
        try:
            delete_instance(
                project_id=VM_CONFIG['project_id'],
                zone=VM_CONFIG['zone'],
                instance_name=VM_CONFIG['instance_name']
            )
            proxy_state.clear_proxy()
        except Exception as e:
            print(f"Error during VM cleanup: {e}")


async def client_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_client = query.data
    user_id = update.effective_user.id
    token = proxy_state.get_user_token(user_id)

    if not token:
        await query.edit_message_text(
            "Token not found. Please start over with /start command."
        )
        return ConversationHandler.END

    try:
        status_message = await query.edit_message_text(
            f"Processing request for: {selected_client}\n"
            "⏳ Initializing..."
        )

        proxy_ip = await get_or_create_proxy()

        await status_message.edit_text(
            f"Processing request for: {selected_client}\n"
            "⏳ Fetching tenders..."
        )

        file_path = await perform_tender_search(selected_client, proxy_ip, token)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(file_path, 'rb'),
            caption=f"✅ Tender report for {selected_client}"
        )

        await status_message.edit_text(f"✅ Report generated successfully for {selected_client}")

        context.job_queue.run_once(
            finish_task,
            when=30  # Changed to seconds instead of timedelta
        )

    except Exception as e:
        error_message = "❌ An error occurred while processing your request. Please try again."
        if hasattr(e, 'args') and len(e.args) > 0:
            if 'proxy' in str(e.args[0]).lower():
                error_message = "❌ Connection issue detected. Please try again in a few minutes."
            elif 'token' in str(e.args[0]).lower():
                error_message = "❌ Invalid token. Please restart with /start and provide a valid token."

        await query.edit_message_text(error_message)
        proxy_state.remove_user()

    return ConversationHandler.END

if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_handler)],
            SELECTING_CLIENT: [CallbackQueryHandler(client_selection)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)

    # Periodic cleanup check every 5 minutes
    app.job_queue.run_repeating(
        cleanup_check,
        interval=300,
        first=300
    )

    print("Bot is running...")
    app.run_polling()
