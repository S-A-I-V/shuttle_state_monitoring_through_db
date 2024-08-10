import pymysql

# Function to connect to MySQL and create the database and table
def setup_database():
    connection = pymysql.connect(
        host='192.168.27.185',  # Replace with your MySQL server IP
        user='saideep',  # Replace with your MySQL username
        password='Lenskart@123#',  # Replace with your MySQL password
        port=3306  # Default MySQL port
    )

    try:
        with connection.cursor() as cursor:
            # Create database if it does not exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS shuttle_state")
            
            # Switch to the new database
            cursor.execute("USE shuttle_state")
            
            # Create table if it does not exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    ip VARCHAR(15) NOT NULL,
                    state ENUM('up', 'down') NOT NULL,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
        connection.commit()
    finally:
        connection.close()

# Execute the function to set up the database and table
setup_database()
