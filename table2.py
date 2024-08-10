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

db_config = {
    'host': '192.168.27.185',
    'user': 'saideep',
    'password': 'Lenskart@123#',
    'database': 'shuttle_state',
    'port': 3306
}

def create_shuttle_status_table():
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS shuttle_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            shuttle_name VARCHAR(255) NOT NULL,
            shuttle_ip VARCHAR(255) NOT NULL,
            shuttle_state VARCHAR(10) NOT NULL,
            state_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
        cursor.execute(create_table_query)
        connection.commit()
    except pymysql.MySQLError as e:
        logging.error(f"Error creating table: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def populate_initial_data(file_path):
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
    except FileNotFoundError:
        logging.error(f"File '{file_path}' not found.")
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {str(e)}")
    return shuttles

def insert_initial_shuttles(shuttles):
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        for name, ip in shuttles:
            query = """INSERT INTO shuttle_status 
                       (shuttle_name, shuttle_ip, shuttle_state, state_timestamp) 
                       VALUES (%s, %s, 'YTC', NOW())"""
            cursor.execute(query, (name, ip))
        connection.commit()
    except pymysql.MySQLError as e:
        logging.error(f"Error executing query: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    create_shuttle_status_table()  # Create the table if it doesn't exist
    shuttles = populate_initial_data('temp_shuttles.txt')
    insert_initial_shuttles(shuttles)
