
import telebot
import os
import subprocess
import logging
from flask import Flask, render_template
import threading
import time

# --- CONFIGURATION ---
BOT_TOKEN = "8345947714:AAENEX0AOb0_fOD9kd3GJjpDSECNytmVe8c"  # Replace with your bot's token
ADMIN_USER_ID = 2052400282  # Replace with your Telegram user ID (admin)
UPLOAD_FOLDER = "uploaded_files"
LOG_FILE = "bot_logs.txt"
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000  # Choose a suitable port

# --- SETUP ---
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- LOGGING ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- TELEBOT ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- FLASK ---
app = Flask(__name__)

# --- GLOBALS ---
running_processes = {} # Store running processes with their IDs

# --- HELPER FUNCTIONS ---

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

def run_command(command, timeout=60):  # Added timeout
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        running_processes[process.pid] = process
        stdout, stderr = process.communicate(timeout=timeout) # Added timeout
        del running_processes[process.pid]
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        process.kill()
        return 1, "", "Timeout expired after 60 seconds."
    except Exception as e:
        return 1, "", str(e)

def list_files():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    return files

def get_file_path(filename):
    return os.path.join(UPLOAD_FOLDER, filename)

# --- TELEBOT HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        bot.reply_to(message, "👋 Welcome, Admin! You have control. Use /help for commands.")
    else:
        bot.reply_to(message, "🚫 Unauthorized access.")

@bot.message_handler(commands=['help'])
def help_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    help_text = """
    🤖 Bot Commands:
    /start - Start the bot
    /help - Show this help message
    /upload - Upload a Python file (attach file to message)
    /listfiles - List uploaded files
    /run <filename> - Run a Python file
    /install <package> - Install a Python package using pip
    /logs - Get the bot's log file
    /stop <process_id> - Stop a running process
    /status - Check if the bot is running (via web)
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['listfiles'])
def list_files_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    files = list_files()
    if files:
        file_list = "\n".join(files)
        bot.reply_to(message, f"📁 Uploaded files:\n{file_list}")
    else:
        bot.reply_to(message, "📂 No files uploaded yet.")

@bot.message_handler(commands=['run'])
def run_file_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    try:
        filename = message.text.split(" ", 1)[1].strip()
        file_path = get_file_path(filename)

        if not os.path.exists(file_path):
            bot.reply_to(message, f"❌ File '{filename}' not found.")
            return

        # Run the file
        command = f"python3 {file_path}"
        bot.reply_to(message, f"🚀 Running '{filename}'...")
        returncode, stdout, stderr = run_command(command)

        if returncode == 0:
            bot.reply_to(message, f"✅ '{filename}' executed successfully.\n\nOutput:\n{stdout}")
            logging.info(f"File '{filename}' ran successfully. Output: {stdout}")
        else:
            error_message = f"❌ '{filename}' failed with error:\n{stderr}"
            bot.reply_to(message, error_message)
            bot.send_message(ADMIN_USER_ID, f"🚨 Error running '{filename}':\n{stderr}")  # Notify admin
            logging.error(f"File '{filename}' failed. Error: {stderr}")

    except IndexError:
        bot.reply_to(message, "⚠️ Please specify a filename to run. Example: /run my_script.py")
    except Exception as e:
        bot.reply_to(message, f"❌ An unexpected error occurred: {e}")
        logging.exception("Error running file.")

@bot.message_handler(commands=['stop'])
def stop_process_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    try:
        process_id = int(message.text.split(" ", 1)[1].strip())
        if process_id in running_processes:
            process = running_processes[process_id]
            process.terminate()  # Or process.kill()
            del running_processes[process_id]
            bot.reply_to(message, f"🛑 Process {process_id} stopped.")
        else:
            bot.reply_to(message, f"❌ Process {process_id} not found.")

    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Please specify a process ID to stop. Example: /stop 1234")
    except Exception as e:
        bot.reply_to(message, f"❌ An unexpected error occurred: {e}")
        logging.exception("Error stopping process.")

@bot.message_handler(commands=['install'])
def install_package_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    try:
        package_name = message.text.split(" ", 1)[1].strip()
        bot.reply_to(message, f"⏳ Installing '{package_name}'...")

        command = f"pip install {package_name} -U" #added -U to avoid dependency problems
        returncode, stdout, stderr = run_command(command)

        if returncode == 0:
            bot.reply_to(message, f"✅ '{package_name}' installed successfully.\n\nOutput:\n{stdout}")
            logging.info(f"Package '{package_name}' installed successfully. Output: {stdout}")
        else:
            error_message = f"❌ Failed to install '{package_name}':\n{stderr}"
            bot.reply_to(message, error_message)
            bot.send_message(ADMIN_USER_ID, f"🚨 Error installing '{package_name}':\n{stderr}") #Notify Admin
            logging.error(f"Failed to install '{package_name}'. Error: {stderr}")

    except IndexError:
        bot.reply_to(message, "⚠️ Please specify a package to install. Example: /install requests")
    except Exception as e:
        bot.reply_to(message, f"❌ An unexpected error occurred: {e}")
        logging.exception("Error installing package.")


@bot.message_handler(commands=['logs'])
def get_logs_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    try:
        with open(LOG_FILE, "r") as f:
            logs = f.read()
        bot.send_document(message.chat.id, open(LOG_FILE, 'rb'), caption="📜 Bot Logs")  # Send as document
    except FileNotFoundError:
        bot.reply_to(message, "⚠️ Log file not found.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting logs: {e}")
        logging.exception("Error getting logs.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = message.document.file_name

        if not filename.endswith(".py"):
            bot.reply_to(message, "⚠️ Only Python files (.py) are allowed.")
            return

        file_path = get_file_path(filename)

        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f"✅ File '{filename}' saved successfully.")
        logging.info(f"File '{filename}' uploaded.")

    except Exception as e:
        bot.reply_to(message, f"❌ Error saving file: {e}")
        logging.exception("Error saving file.")


# --- FLASK ROUTES ---

@app.route("/")
def index():
    return render_template('index.html', bot_status="✅ Bot is Running Live")  # Use Jinja template

@app.route("/status")
def status():
    return "Bot is Running Live ✅"

@bot.message_handler(commands=['status'])
def status_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Unauthorized access.")
        return
    bot.reply_to(message, "Bot status can be viewed at the web interface.")

# --- POLLING and WEB SERVER ---
def start_flask():
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False) # Disable reloader for threading

def start_polling():
    bot.infinity_polling()

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True  # Daemonize thread so it exits when the main thread exits
    flask_thread.start()

    # Start Telegram bot polling in the main thread
    start_polling()
