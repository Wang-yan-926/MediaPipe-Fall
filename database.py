# database.py
import pymysql

def init_database():
    """自动初始化 MySQL 数据库与基础表结构"""
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='231006410',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS fall_detector_db DEFAULT CHARACTER SET utf8mb4;")
        cursor.close()
        conn.close()

        db = pymysql.connect(
            host='localhost',
            user='root',
            password='231006410',
            database='fall_detector_db',
            charset='utf8mb4'
        )
        cursor = db.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alarm_time VARCHAR(50),
            video_filename VARCHAR(255),
            status VARCHAR(50)
        );
        """)

        cursor.execute("SELECT COUNT(*) FROM users WHERE username='root';")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('root', '231006410', 'admin');")
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('family', '123456', 'family');")
            db.commit()

        cursor.close()
        db.close()
        print("✅ MySQL 数据库连接及初始化成功！")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False