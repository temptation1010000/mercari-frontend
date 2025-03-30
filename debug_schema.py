import sqlite3
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = "mercari_monitor.db"

def fix_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 备份当前数据
        logger.info("备份products表数据...")
        c.execute("CREATE TABLE products_backup AS SELECT * FROM products")
        
        # 删除旧表
        logger.info("删除旧的products表...")
        c.execute("DROP TABLE products")
        
        # 使用新结构创建表
        logger.info("用新结构创建products表...")
        c.execute('''CREATE TABLE products (
            id TEXT,
            user_id TEXT,
            name TEXT,
            price TEXT,
            image_url TEXT,
            product_url TEXT,
            stock_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, user_id)
        )''')
        
        # 恢复数据
        logger.info("从备份恢复数据...")
        c.execute('''INSERT INTO products 
                    (id, user_id, name, price, image_url, product_url, stock_status)
                    SELECT id, user_id, name, price, image_url, product_url, stock_status
                    FROM products_backup''')
        
        # 统一notified_products表中user_id的类型
        logger.info("修改notified_products表中user_id为TEXT类型...")
        c.execute("CREATE TABLE notified_temp AS SELECT id, user_id as user_id_old, notified_at FROM notified_products")
        c.execute("DROP TABLE notified_products")
        c.execute('''CREATE TABLE notified_products (
            id TEXT,
            user_id TEXT,
            notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, user_id)
        )''')
        c.execute("INSERT INTO notified_products SELECT id, CAST(user_id_old AS TEXT), notified_at FROM notified_temp")
        c.execute("DROP TABLE notified_temp")
        
        conn.commit()
        logger.info("数据库修复完成！")
    except Exception as e:
        conn.rollback()
        logger.error(f"修复过程中出错: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()