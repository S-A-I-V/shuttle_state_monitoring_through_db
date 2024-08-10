import logging
import asyncio
import pymysql
from typing import List, Dict, Tuple
import ping3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from datetime import datetime, timedelta

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

shuttle_states: Dict[str, Tuple[bool, int, datetime]] = {}
offline_servers: Dict[str, bool] = {}

# MySQL connection configuration
db_config = {
    'host': '192.168.27.185',
    'user': 'saideep',
    'password': 'Lenskart@123#',
    'database': 'shuttle_state',
    'port': 3306
}

def log_to_database(name: str, ip: str, state: str, start_time: datetime, end_time: datetime = None, duration: timedelta = None):
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        if state == 'up':
            sql = "INSERT INTO server_logs (name, ip, state, start_time) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, ip, state, start_time))
        else:
            duration = end_time - start_time
            sql = "INSERT INTO server_logs (name, ip, state, start_time, end_time, duration) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (name, ip, state, start_time, end_time, duration))
        
        connection.commit()
    except pymysql.MySQLError as e:
        logging.error(f"Error logging to database: {e}")
    finally:
        connection.close()

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
                        shuttle_states[ip_address] = (None, 0, None)  # Initialize state as None, failed count as 0, and start time as None
                        offline_servers[ip_address] = False  # Initialize offline status
                    else:
                        logging.warning(f"Ignoring line in file '{file_path}' with unexpected format: {line.strip()}")
    except FileNotFoundError:
        logging.error(f"File '{file_path}' not found.")
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {str(e)}")
    return shuttles

async def monitor_shuttles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shuttles = read_shuttles_from_file('temp_shuttles.txt')
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Monitoring started.")

    while True:
        for name, ip in shuttles:
            current_state = await ping_ip(ip)
            prev_state, fail_count, start_time = shuttle_states[ip]

            if current_state:
                if prev_state is False:
                    end_time = datetime.now()
                    log_to_database(name, ip, 'down', start_time, end_time)
                    message = f"Shuttle ({ip}) is back online."
                    logging.info(message)
                    await context.bot.send_message(chat_id=chat_id, text=message)
                shuttle_states[ip] = (True, 0, datetime.now())
                if offline_servers[ip]:
                    offline_servers[ip] = False  # Mark server as back online
            else:
                if fail_count < 3:
                    shuttle_states[ip] = (False, fail_count + 1, start_time)
                else:
                    shuttle_states[ip] = (False, 4, start_time)
                    if not offline_servers[ip]:
                        start_time = datetime.now() if start_time is None else start_time
                        log_to_database(name, ip, 'down', start_time)
                        message = f"Shuttle ({ip}) is offline."
                        logging.info(message)
                        await context.bot.send_message(chat_id=chat_id, text=message)
                        offline_servers[ip] = True

        await asyncio.sleep(30)  # Update state every 30 seconds

if __name__ == '__main__':
    application = ApplicationBuilder().token('5611651914:AAHjWlUqXDBJmQph0nw4fFrktUGsvtPg-uQ').build()
    monitor_handler = CommandHandler('monitor', monitor_shuttles)
    application.add_handler(monitor_handler)
    application.run_polling()
