from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
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
                'active_users': 0  # Track number of active users
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


VM_CONFIG = {
    "project_id": "proven-answer-446208-h6",
    "zone": "asia-south1-c",
    "instance_name": "ubuntu-vm",
    "machine_type": "e2-standard-8",
    "image_family": "ubuntu-2004-lts",
    "image_project": "ubuntu-os-cloud",
    "disk_size_gb": 30,
    "disk_type": "pd-ssd",
    "tags": ["proxy-server"],
    "startup_script_path": "startup-script.sh"
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
    """Get existing proxy IP or create new VM if needed"""
    existing_ip = proxy_state.get_proxy_ip()
    if existing_ip:
        proxy_state.add_user()
        return existing_ip

    # Create new VM if none exists
    external_ip = create_instance_with_public_ip(**VM_CONFIG)
    proxy_state.update_proxy(external_ip)
    time.sleep(20)  # Wait for VM to be fully ready
    return external_ip


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to Tender Bot! 🤖\nI will make reports of which works are available based on the client's name from https://tender.nprocure.com."
    )
    await asyncio.sleep(2)
    keyboard = [
        [InlineKeyboardButton(client, callback_data=client)] for client in clients
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a client to proceed:",
        reply_markup=reply_markup
    )


async def finish_task(context: ContextTypes.DEFAULT_TYPE):
    """Mark task as complete by removing user"""
    proxy_state.remove_user()
    # Attempt cleanup if no active users and time elapsed
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


async def client_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    selected_client = query.data

    await query.edit_message_text(f"You selected: {selected_client}\nChecking proxy server status...")

    try:
        proxy_ip = await get_or_create_proxy()
        await query.edit_message_text(
            f"You selected: {selected_client}\n"
            f"Using proxy server (IP: {proxy_ip})\n"
            "Fetching tenders..."
        )

        # Assuming perform_tender_search returns a file path
        file_path = await perform_tender_search(selected_client, proxy_ip)

        # Send file to user
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(file_path, 'rb'),
            caption="Here is the tender report you requested."
        )

        await query.edit_message_text(f"Tender report for {selected_client} sent successfully.")

        # Schedule task completion after 30 minutes
        context.job_queue.run_once(
            finish_task,
            when=timedelta(minutes=30)
        )

    except Exception as e:
        await query.edit_message_text(
            f"Error with proxy server: {str(e)}\n"
            "Please try again later."
        )
        proxy_state.remove_user()


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

if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(client_selection))

    # Periodic cleanup check every 5 minutes
    app.job_queue.run_repeating(
        cleanup_check,
        interval=300,  # 5 minutes
        first=300
    )

    print("Bot is running...")
    app.run_polling()
