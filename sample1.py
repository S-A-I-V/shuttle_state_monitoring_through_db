import logging
import asyncio
import pymysql
from typing import List, Dict, Tuple
import ping3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

shuttle_states: Dict[str, Tuple[bool, int]] = {}
offline_servers: Dict[str, bool] = {}

# Database connection parameters
db_config = {
    'host': '192.168.27.185',
    'user': 'saideep',
    'password': 'Lenskart@123#',
    'database': 'shuttle_state',
    'port': 3306
}

def execute_query(query, params=None):
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
    except pymysql.MySQLError as e:
        logging.error(f"Error executing query: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def read_shuttles_from_file(file_path: str) -> List[Tuple[str, str]]:
    shuttles = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        name = parts[0].strip()
                        ip_address = parts[1].strip()
                        shuttles.append((name, ip_address))
                        shuttle_states[ip_address] = (None, 0)  # Initialize state as None and failed count as 0
                        offline_servers[ip_address] = False  # Initialize offline status
                    else:
                        logging.warning(f"Ignoring line in file '{file_path}' with unexpected format: {line.strip()}")
    except FileNotFoundError:
        logging.error(f"File '{file_path}' not found.")
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {str(e)}")
    return shuttles

async def ping_ip(ip_address: str) -> bool:
    try:
        failed_pings = 0
        for _ in range(4):
            response = ping3.ping(ip_address, timeout=0.1)
            logging.info(f"Pinging IP: {ip_address} with response: {response}")
            if response is None:
                failed_pings += 1
        return failed_pings < 4
    except Exception as e:
        logging.error(f"Error pinging {ip_address}: {str(e)}")
        return False

async def monitor_shuttles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shuttles = read_shuttles_from_file('temp_shuttles.txt')
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Monitoring started.")

    while True:
        for name, ip in shuttles:
            current_state = await ping_ip(ip)
            prev_state, fail_count = shuttle_states[ip]

            if current_state:
                if not prev_state:  # Transition from offline to online
                    shuttle_states[ip] = (True, 0)  # Reset fail count if online
                    offline_servers[ip] = False  # Mark server as back online
                    message = f"Shuttle ({ip}) is back online."
                    logging.info(message)
                    await context.bot.send_message(chat_id=chat_id, text=message)
                    # Update the shuttle_status table
                    query = """UPDATE shuttle_status 
                               SET shuttle_state = 'up', state_timestamp = NOW() 
                               WHERE shuttle_ip = %s"""
                    execute_query(query, (ip,))
            else:
                if prev_state:  # Transition from online to offline
                    shuttle_states[ip] = (False, 4)  # Lock in fail count at 4 to signify offline
                    offline_servers[ip] = True  # Mark server as offline
                    message = f"Shuttle ({ip}) is offline."
                    logging.info(message)
                    await context.bot.send_message(chat_id=chat_id, text=message)
                    # Update the shuttle_status table
                    query = """UPDATE shuttle_status 
                               SET shuttle_state = 'down', state_timestamp = NOW() 
                               WHERE shuttle_ip = %s"""
                    execute_query(query, (ip,))

        await asyncio.sleep(30)  # Update state every 30 seconds

if __name__ == '__main__':
    application = ApplicationBuilder().token('5611651914:AAHjWlUqXDBJmQph0nw4fFrktUGsvtPg-uQ').build()
    monitor_handler = CommandHandler('monitor', monitor_shuttles)
    application.add_handler(monitor_handler)
    application.run_polling()
