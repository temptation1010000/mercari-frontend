import os
import re
import time
import json
import sqlite3
import logging
import asyncio
import requests
import threading
import traceback
import random
import smtplib
import string
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import jwt

# 设置日志
LOG_FILE = "mercari_monitor.log"

# 移除生产环境检查，直接设置日志配置
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mercari_monitor.log"),
        logging.StreamHandler()  # 恢复控制台输出
    ]
)
logger = logging.getLogger(__name__)

# 配置信息
DB_NAME = "mercari_monitor.db"
CHECK_INTERVAL = 0
# 添加JWT密钥
SECRET_KEY = os.environ.get("SECRET_KEY", "mercari_monitor_secret_key")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.101 Mobile/15E148 Safari/604.1",
]

# 邮件配置
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 587
EMAIL_USER = '2094025775@qq.com'
EMAIL_PASS = 'plhrkwmekwbcbegc'

class DBHelper:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_NAME)
    
    @staticmethod
    def execute_query(query, params=(), fetch_one=False, commit=False):
        conn = DBHelper.get_connection()
        c = conn.cursor()
        try:
            c.execute(query, params)
            
            if commit:
                conn.commit()
                return True
            
            if fetch_one:
                return c.fetchone()
            return c.fetchall()
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def execute_many(query, params_list, commit=True):
        conn = DBHelper.get_connection()
        c = conn.cursor()
        try:
            c.executemany(query, params_list)
            if commit:
                conn.commit()
            return True
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
        finally:
            conn.close()

def create_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id TEXT PRIMARY KEY, 
                  user_id TEXT,
                  name TEXT, 
                  price TEXT,
                  image_url TEXT,
                  product_url TEXT,
                  stock_status TEXT,
                  last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  keywords TEXT,
                  email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scrape_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  scrape_time REAL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

async def get_page_content(url):
    """获取页面内容的异步函数，增强反爬虫绕过能力"""
    try:
        logger.info(f"正在获取页面: {url}")
        async with async_playwright() as p:
            # 使用无头浏览器模式
            browser = await p.chromium.launch(
                headless=True,  # 改回无头模式以在服务器环境中运行
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',  # 禁用自动化控制特征
                    '--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"'
                ]
            )
            
            # 创建更真实的浏览器环境
            context = await browser.new_context(
                locale="ja-JP",  # 使用日语区域
                timezone_id="Asia/Tokyo",  # 设置东京时区
                viewport={'width': 1280, 'height': 800},
                bypass_csp=True
            )
            
            # 增强的反检测脚本
            await context.add_init_script("""
                // 覆盖webdriver属性
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                
                // 添加伪造的插件
                Object.defineProperty(navigator, 'plugins', { 
                    get: () => [1, 2, 3, 4, 5].map(() => ({
                        name: 'Plugin',
                        description: 'Description',
                        filename: 'plugin.dll'
                    }))
                });
                
                // 设置语言为日语
                Object.defineProperty(navigator, 'languages', { 
                    get: () => ['ja-JP', 'ja', 'en-US', 'en'] 
                });
                
                // 添加伪造的指纹信息
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            page = await context.new_page()
            
            # 添加随机鼠标移动模拟真实用户
            await page.evaluate("""
                function simulateHumanMovement() {
                    const events = ['mousemove', 'scroll'];
                    const event = events[Math.floor(Math.random() * events.length)];
                    
                    if (event === 'mousemove') {
                        const x = Math.floor(Math.random() * window.innerWidth);
                        const y = Math.floor(Math.random() * window.innerHeight);
                        const event = new MouseEvent('mousemove', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y
                        });
                        document.dispatchEvent(event);
                    } else if (event === 'scroll') {
                        window.scrollBy(0, (Math.random() - 0.5) * 100);
                    }
                }
                
                setInterval(simulateHumanMovement, 500);
            """)
            
            # 使用更可靠的页面加载策略
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            logger.info("等待页面完全加载...")
            await page.wait_for_timeout(5000)  # 等待5秒确保JS加载完成
            
            # 执行滚动操作来触发懒加载内容
            await page.evaluate("""
                // 慢慢滚动以触发懒加载
                function smoothScroll() {
                    const height = document.body.scrollHeight;
                    const steps = 10;
                    for(let i = 0; i < steps; i++) {
                        setTimeout(() => {
                            window.scrollTo(0, (height/steps) * i);
                        }, i * 300);
                    }
                    setTimeout(() => window.scrollTo(0, 0), steps * 300);
                }
                smoothScroll();
            """)
            
            # 再等待加载完成
            logger.info("等待商品元素加载...")
            try:
                await page.wait_for_selector('[data-testid="item-cell"]', timeout=20000)
                logger.info("商品元素已成功加载")
                # 找到元素后立即获取
                html_content = await page.evaluate("() => document.documentElement.outerHTML")
                logger.info(f"成功获取商品页面，长度: {len(html_content)}")
            except Exception as wait_error:
                logger.warning(f"等待商品元素超时: {str(wait_error)}")
                # 超时后也获取内容（用于调试）
                html_content = await page.evaluate("() => document.documentElement.outerHTML")
                logger.info(f"获取页面成功，但无商品元素，长度: {len(html_content)}")
            
            # 保存截图和HTML
            await page.screenshot(path="mercari_screenshot.png", full_page=True)
            with open("mercari_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
                
            with open("mercari_full_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            
            await browser.close()
            return html_content
            
    except Exception as e:
        logger.error(f"获取页面错误: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def parse_products(html):
    """解析HTML内容提取商品信息，极简版本"""
    if not html:
        logger.error("HTML内容为空，无法解析")
        return []
        
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    
    # 使用最明确的选择器查找商品项
    items = soup.select('[data-testid="item-cell"]')
    
    if not items:
        logger.error("无法找到商品项，保存HTML以供调试")
        # 始终保存调试HTML
        with open("mercari_full_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        return []
    
    logger.info(f"找到 {len(items)} 个商品项")
    
    # 遍历每个找到的商品项
    for idx, item in enumerate(items):
        try:
            # 1. 提取商品ID - 只从merItemThumbnail的id属性获取
            thumbnail = item.select_one('.merItemThumbnail')
            if not thumbnail or not thumbnail.has_attr('id'):
                logger.warning(f"商品 #{idx} 没有有效ID，跳过")
                continue
            
            product_id = thumbnail.get('id')
            
            # 2. 提取商品链接 - 只从a标签href获取
            link_elem = item.select_one('a[href*="/item/"]')
            product_url = None
            if link_elem and link_elem.has_attr('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    product_url = f"https://jp.mercari.com{href}"
                else:
                    product_url = href
            else:
                product_url = f"https://jp.mercari.com/item/{product_id}"
            
            # 3. 提取商品名称 - 只从role="img"元素的aria-label获取
            name = None
            main_container = item.select_one('[role="img"][aria-label]')
            if main_container:
                aria_label = main_container.get('aria-label', '')
                if 'の画像' in aria_label:
                    name = aria_label.split('の画像')[0]
            
            # 如果没有名称，使用ID作为名称
            if not name or len(name) <= 2:
                name = f"商品 (ID: {product_id})"
            
            # 4. 提取价格 - 只从新的价格结构提取
            price = None
            currency_elem = item.select_one('.currency__6b270ca7')
            number_elem = item.select_one('.number__6b270ca7')
            if currency_elem and number_elem:
                price = f"{currency_elem.text}{number_elem.text}"
            else:
                price = "価格未知"
            
            # 5. 提取图片 - 只从img src属性提取
            image_url = None
            img = item.select_one('img[src]')
            if img:
                image_url = img.get('src')
            else:
                image_url = "https://static.mercdn.net/images/mercari_profile.png"
            
            # 创建商品对象并添加到列表
            product = {
                'id': product_id,
                'name': name,
                'price': price,
                'image_url': image_url,
                'product_url': product_url,
                'stock_status': 'on_sale'
            }
            
            logger.info(f"解析到商品: {name[:30]}{'...' if len(name) > 30 else ''} ({price})")
            products.append(product)
            
        except Exception as e:
            logger.error(f"解析商品 #{idx} 时出错: {str(e)}")
            traceback.print_exc()
            continue
    
    # 统计和记录
    logger.info(f"总共解析到 {len(products)} 个有效商品")
    if not products:
        logger.error("未解析到任何商品，检查解析函数")
    
    return products

def update_database(products, user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.isolation_level = None  # 启用自动提交
    c = conn.cursor()
    c.execute("BEGIN TRANSACTION")  # 开始事务
    
    try:
        new_products = []
        for p in products:
            # 检查是否存在
            c.execute("SELECT id FROM products WHERE id=? AND user_id=?", (p['id'], user_id))
            if not c.fetchone():
                new_products.append(p)
                c.execute('''INSERT OR REPLACE INTO products 
                    (id, user_id, name, price, image_url, product_url, stock_status)
                    VALUES (?,?,?,?,?,?,?)''',
                    (p['id'], user_id, p['name'], p['price'], p['image_url'], 
                     p['product_url'], p['stock_status']))
            else:
                # 更新现有记录
                c.execute('''UPDATE products SET name=?, price=?, image_url=?, product_url=?, stock_status=?
                    WHERE id=? AND user_id=?''',
                    (p['name'], p['price'], p['image_url'], p['product_url'], p['stock_status'], p['id'], user_id))
        
        c.execute("COMMIT")  # 提交事务
    except Exception as e:
        c.execute("ROLLBACK")  # 发生错误时回滚
        logger.error(f"更新数据库时出错: {str(e)}")
    finally:
        conn.close()
        
    return new_products

def send_email(new_products, email):
    if not new_products:
        return
    
    # 添加邮件开头提示
    msg_content = """
    <h2>新商品通知</h2>
    <p style="color:#666; font-size:12px;">注意：如果图片无法显示，请在邮件客户端中选择"显示图片"或"总是显示来自此发件人的图片"</p>
    """
    
    for p in new_products:
        # 确保图片URL是完整的
        image_url = p['image_url']
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
            image_url = f"https:{image_url}" if image_url.startswith('//') else f"https://jp.mercari.com{image_url}"
        
        # 使用更可靠的布局和样式
        msg_content += f"""
        <div style="margin-bottom:20px; padding:10px; border:1px solid #eee; border-radius:5px;">
            <h3 style="margin-top:0; color:#333;">{p['name']}</h3>
            <p>价格: <strong style="color:#e53935;">{p['price']}</strong><br>
            状态: <span style="color:#4caf50;">{p['stock_status']}</span></p>
            <p><a href="{p['product_url']}" style="background:#4caf50; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;">查看商品</a></p>
            <div>
                <img src="{image_url}" alt="{p['name']}" style="max-width:200px; border:1px solid #ddd; display:block;" />
                <p style="font-size:10px; color:#999;">如果图片未显示，请<a href="{image_url}" target="_blank">点击这里</a>直接查看</p>
            </div>
        </div>
        """
    
    # 添加底部说明
    msg_content += """
    <hr>
    <p style="color:#666; font-size:11px;">
        此邮件由Mercari监控系统自动发送。图片来源于Mercari网站，版权归原所有者所有。
    </p>
    """
    
    # 构建多部分邮件以支持更复杂的HTML内容
    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(f'Mercari新商品通知 ({len(new_products)}件)', 'utf-8')
    msg['From'] = EMAIL_USER
    msg['To'] = email
    
    # 添加纯文本版本作为备用
    text_content = f"发现{len(new_products)}件新商品。请使用支持HTML的邮件客户端查看完整内容。"
    msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
    
    # 添加HTML版本
    msg.attach(MIMEText(msg_content, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [email], msg.as_string())
        server.quit()
        logger.info(f"成功发送新品通知邮件到: {email}")
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")

def encode_keyword_to_base64(keyword):
    encoded_bytes = base64.b64encode(keyword.encode('utf-8'))
    encoded_str = encoded_bytes.decode('utf-8').rstrip('=')
    return encoded_str

# 定义Mercari搜索的基础URL前缀
BASE_URL_PREFIX = "https://jp.mercari.com/search?search_condition_id=1cx0xHGsd"

async def run_monitor(user_id):
    """异步监控任务主函数"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT keywords, email FROM users WHERE id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result is not None:
        keywords, email = result
        
        if not keywords:
            logger.warning(f"用户 ID {user_id} 的关键词为空")
            return
            
        logger.info(f"开始监控用户 ID {user_id}，关键词: {keywords}")
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 修复URL生成逻辑
            encoded_keyword = encode_keyword_to_base64(keywords)
            target_url = f"{BASE_URL_PREFIX}{encoded_keyword}"
            
            logger.info(f"请求URL: {target_url}")
            html = await get_page_content(target_url)
            
            if html:
                logger.debug(f"成功获取HTML内容，长度: {len(html)}")
                
                # 解析商品
                products = parse_products(html)
                
                if products:
                    logger.info(f"解析到 {len(products)} 个有效商品")
                    
                    # 只显示第一个产品的简要信息
                    first_product = products[0]
                    logger.info(f"商品示例: {first_product['name'][:30]}{'...' if len(first_product['name']) > 30 else ''} ({first_product['price']})")
                    
                    # 更新数据库并获取新商品
                    new_products = update_database(products, user_id)
                    
                    if new_products:
                        logger.info(f"发现 {len(new_products)} 个新商品，准备发送邮件")
                        send_email(new_products, email)
                        
                        # 更新新商品数量
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("UPDATE monitor_status SET new_products=? WHERE user_id=?", 
                               (len(new_products), user_id))
                        conn.commit()
                        conn.close()
                else:
                    logger.warning("未解析到任何商品，检查解析函数")
            else:
                logger.error("获取页面内容失败，检查网络连接或Playwright配置")
            
            # 计算并记录抓取时间
            end_time = time.time()
            scrape_time = end_time - start_time
            logger.info(f"抓取完成，耗时: {scrape_time:.2f}秒")
            
            # 记录到数据库
            DBHelper.execute_query(
                "INSERT INTO scrape_logs (user_id, scrape_time) VALUES (?, ?)",
                (user_id, scrape_time),
                commit=True
            )
        
        except Exception as e:
            logger.error(f"监控过程中出现错误: {str(e)}")
            logger.error(traceback.format_exc())

# 添加一个同步包装函数，供非异步环境调用
def run_monitor_sync(user_id):
    """同步版本的run_monitor函数，供非异步环境调用"""
    asyncio.run(run_monitor(user_id))

# 添加这个新函数 - 定期执行监控任务
def run_monitor_periodic(user_id):
    """定期执行监控任务"""
    try:
        while True:
            # 检查是否应该继续运行
            status = DBHelper.execute_query(
                "SELECT is_running FROM monitor_status WHERE user_id=?", 
                (user_id,), 
                fetch_one=True
            )
            
            if not status or not status[0]:
                break
                
            # 执行一次监控
            run_monitor_sync(user_id)
            
            # 更新最后检查时间
            current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            DBHelper.execute_query(
                "UPDATE monitor_status SET last_check=? WHERE user_id=?", 
                (current_time, user_id),
                commit=True
            )
            
            # 等待间隔时间再次执行
            time.sleep(CHECK_INTERVAL * 60)
    except Exception as e: 
        # 发生错误时更新状态为停止
        logger.error(f"监控线程异常: {str(e)}")
        DBHelper.execute_query(
            "UPDATE monitor_status SET is_running=? WHERE user_id=?", 
            (False, user_id),
            commit=True
        )

# 全局存储所有监控线程
monitor_threads = {}

def start_monitoring(user_id):
    """启动用户的监控任务"""
    # 检查该用户是否已有监控线程
    if user_id in monitor_threads and monitor_threads[user_id].is_alive():
        # 更新状态为运行中
        update_monitor_status(user_id, True)
        return True
        
    # 获取用户配置
    config = get_user_config(user_id)
    if not config or not config[0]:
        return False
    
    # 更新监控状态
    update_monitor_status(user_id, True)
    
    # 创建并启动监控线程
    monitor_thread = threading.Thread(target=run_monitor_periodic, args=(user_id,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 存储线程引用
    monitor_threads[user_id] = monitor_thread
    return True

def stop_monitoring(user_id):
    """停止用户的监控任务"""
    # 只需更新状态为停止
    # 线程会自行检查状态并终止
    update_monitor_status(user_id, False)
    return True

def update_monitor_status(user_id, is_running):
    """更新监控状态"""
    current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    # 确保表存在
    DBHelper.execute_query(
        '''CREATE TABLE IF NOT EXISTS monitor_status 
        (user_id INTEGER PRIMARY KEY, is_running BOOLEAN, 
        last_check TEXT, new_products INTEGER)''',
        commit=True
    )
    
    # 更新状态
    DBHelper.execute_query(
        '''INSERT OR REPLACE INTO monitor_status 
        (user_id, is_running, last_check, new_products) 
        VALUES (?, ?, ?, ?)''',
        (user_id, is_running, current_time, 0),
        commit=True
    )

# 生成随机验证码
def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# 发送验证码的API
def send_verification_code(email):
    code = generate_verification_code()
    save_verification_code(email, code)
    
    msg_content = f"您的验证码是：{code}"
    msg = MIMEText(msg_content, 'plain', 'utf-8')
    msg['Subject'] = Header('注册验证码', 'utf-8')
    msg['From'] = EMAIL_USER
    msg['To'] = email
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [email], msg.as_string())
        server.quit()
    except Exception as e:
        pass

def save_verification_code(email, code):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO verification_codes (email, code, timestamp)
                 VALUES (?, ?, CURRENT_TIMESTAMP)''', (email, code))
    conn.commit()
    conn.close()

def check_verification_code(email, code):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT code FROM verification_codes WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == code:
        return True
    return False

# 假设有一个Flask API来处理请求
app = Flask(__name__)
CORS(app)  # 启用CORS

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]
        
        if not token:
            return jsonify({'error': '未提供授权令牌'}), 401
            
        try:
            # 使用SECRET_KEY解码JWT令牌
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            # 将用户信息添加到请求上下文中
            request.user = payload
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的令牌'}), 401
        
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]
            
        if not token:
            return jsonify({'error': '未提供授权令牌'}), 401
            
        try:
            # 使用SECRET_KEY解码JWT令牌
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            # 检查是否为管理员
            if not payload.get('isAdmin', False):
                return jsonify({'error': '需要管理员权限'}), 403
                
            # 将用户信息添加到请求上下文中
            request.user = payload
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的令牌'}), 401
    return decorated

@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    data = request.json
    email = data.get('email')
    if email:
        send_verification_code(email)
        return jsonify({'message': '验证码已发送'}), 200
    return jsonify({'error': '邮箱不能为空'}), 400

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    if check_verification_code(email, code):
        return jsonify({'message': '验证码正确'}), 200
    return jsonify({'error': '验证码错误'}), 400

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    # 检查用户是否已存在
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 先检查用户名是否已存在
        c.execute("SELECT username FROM users_auth WHERE username=?", (username,))
        if c.fetchone():
            return jsonify({'error': '用户名已被注册'}), 400
            
        # 再检查邮箱是否已存在
        c.execute("SELECT email FROM users_auth WHERE email=?", (email,))
        if c.fetchone():
            return jsonify({'error': '邮箱已被注册'}), 400
        
        # 创建表（如果不存在）
        c.execute('''CREATE TABLE IF NOT EXISTS users_auth
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE,
                      password TEXT,
                      email TEXT UNIQUE)''')
        
        # 插入新用户
        c.execute("INSERT INTO users_auth (username, password, email) VALUES (?, ?, ?)",
                  (username, password, email))
        
        # 同时在users表中添加用户信息(用于监控设置)
        c.execute("INSERT INTO users (keywords, email) VALUES (?, ?)",
                  ('', email))  # 初始关键词为空
        
        conn.commit()
        return jsonify({'message': '注册成功'}), 200
    except sqlite3.IntegrityError:
        # 数据库完整性错误（这个分支可能永远不会走到，因为我们前面已经检查了唯一性）
        return jsonify({'error': '用户名或邮箱已被注册'}), 400
    except Exception as e:
        return jsonify({'error': '注册失败'}), 500
    finally:
        conn.close()

@app.route('/api/user/update', methods=['POST'])
@auth_required
def api_user_update():
    # 从认证令牌中获取用户信息
    username = request.user.get('username')
    
    data = request.json
    keywords = data.get('keywords', '')
    email = data.get('email', '')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 通过用户名查询用户ID
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        if user_result:
            user_id = user_result[0]
        else:
            return jsonify({'error': '用户不存在'}), 404
        
        # 更新用户信息
        c.execute("UPDATE users SET keywords=?, email=? WHERE id=?", 
                  (keywords, email, user_id))
        
        # 同时更新users_auth表中的email
        c.execute("UPDATE users_auth SET email=? WHERE username=?", 
                  (email, username))
            
        conn.commit()
        return jsonify({'message': '设置已更新'}), 200
    except Exception as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/monitor/start', methods=['POST'])
@auth_required
def api_start_monitor():
    # 从JWT令牌中获取用户名
    username = request.user.get('username')
    
    # 从请求中获取可选的参数
    keywords = request.args.get('keywords', '')
    
    # 通过用户名获取用户ID
    user_id = get_user_id_from_username(username)
    
    if not user_id:
        return jsonify({'error': '用户不存在'}), 404
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 检查用户配置
        config = get_user_config(user_id)
        if not config or not config[0]:  # 用户没有设置关键词
            # 如果请求中提供了关键词，则使用请求中的关键词
            if keywords:
                # 更新用户关键词
                c.execute("UPDATE users SET keywords=? WHERE id=?", 
                          (keywords, user_id))
                conn.commit()
            else:
                return jsonify({'error': '请先设置关键词或在请求中提供关键词'}), 400
        
        # 开始监控
        start_monitoring(user_id)
        
        return jsonify({'message': '监控已启动'}), 200
    except Exception as e:
        return jsonify({'error': f'启动监控失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/monitor/stop', methods=['POST'])
@auth_required
def api_stop_monitor():
    # 从JWT令牌中获取用户名
    username = request.user.get('username')
    
    # 通过用户名获取用户ID
    user_id = get_user_id_from_username(username)
    
    if not user_id:
        return jsonify({'error': '用户不存在'}), 404
    
    try:
        success = stop_monitoring(user_id)
        
        if success:
            return jsonify({'message': '监控已停止'}), 200
        else:
            return jsonify({'error': '无法停止监控，可能监控任务尚未启动'}), 400
    except Exception as e:
        return jsonify({'error': f'停止监控失败: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 验证用户凭据
        c.execute("SELECT id, password FROM users_auth WHERE username=?", (username,))
        user = c.fetchone()
        
        if user and user[1] == password:
            # 检查是否为管理员
            c.execute("SELECT * FROM admins WHERE username=?", (username,))
            is_admin = c.fetchone() is not None
            
            # 生成JWT令牌
            payload = {
                'username': username,
                'userId': user[0],
                'isAdmin': is_admin,
                'exp': datetime.utcnow() + timedelta(days=30)
            }
            
            # 使用SECRET_KEY签名JWT令牌
            token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'token': token,
                'isAdmin': is_admin
            }), 200
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return jsonify({'error': '登录失败，请重试'}), 500
    finally:
        conn.close()

@app.route('/api/monitor/status', methods=['GET'])
@auth_required
def api_monitor_status():
    # 从JWT令牌中获取用户名
    username = request.user.get('username')
    
    # 通过用户名获取用户ID
    user_id = get_user_id_from_username(username)
    
    if not user_id:
        return jsonify({'error': '用户不存在'}), 404
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("SELECT is_running, last_check, new_products FROM monitor_status WHERE user_id=?", (user_id,))
        status_result = c.fetchone()
        
        if not status_result:
            # 用户还没有监控记录，创建一个初始记录
            c.execute("INSERT INTO monitor_status (user_id, is_running, last_check, new_products) VALUES (?, 0, NULL, 0)", 
                    (user_id,))
            conn.commit()
            
            return jsonify({
                'is_running': False,
                'last_check': '暂无',
                'new_products': 0
            }), 200
        else:
            return jsonify({
                'is_running': bool(status_result[0]),
                'last_check': status_result[1] if status_result[1] else '暂无',
                'new_products': status_result[2] or 0
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'获取监控状态失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/user/info', methods=['GET'])
@auth_required
def api_user_info():
    # 从认证令牌中获取用户信息
    username = request.user.get('username')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 通过用户名查询用户ID
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        if user_result:
            user_id = user_result[0]
        else:
            return jsonify({'error': '用户不存在'}), 404
            
        # 查询用户信息
        c.execute("SELECT keywords, email FROM users WHERE id=?", (user_id,))
        result = c.fetchone()
        
        if result:
            keywords, email = result
            return jsonify({
                'keywords': keywords,
                'email': email
            }), 200
        else:
            return jsonify({'error': '用户信息不存在'}), 404
    except Exception as e:
        return jsonify({'error': '获取用户信息失败'}), 500
    finally:
        conn.close()

def create_verification_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS verification_codes
                 (email TEXT PRIMARY KEY, 
                  code TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def insert_test_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 插入测试用户数据
    c.execute("INSERT INTO users (keywords, email) VALUES (?, ?)", ("魔トカゲ", "test@example.com"))
    conn.commit()
    conn.close()

# 添加一个函数来设置管理员账号
def set_admin_account():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 检查管理员账号是否已存在
        c.execute("SELECT * FROM admins WHERE username=?", ("momo9144",))
        admin = c.fetchone()
        
        if not admin:
            # 先确保这个用户存在于users_auth表中
            c.execute("SELECT id FROM users_auth WHERE username=?", ("momo9144",))
            user = c.fetchone()
            
            if user:
                # 将该用户添加为管理员
                c.execute("INSERT INTO admins (username) VALUES (?)", ("momo9144",))
                conn.commit()
            else:
                # 如果用户不存在，先创建用户再设为管理员
                c.execute("INSERT INTO users_auth (username, password, email) VALUES (?, ?, ?)",
                          ("momo9144", "admin123", "admin@example.com"))
                c.execute("INSERT INTO users (keywords, email) VALUES (?, ?)",
                          ('', "admin@example.com"))
                c.execute("INSERT INTO admins (username) VALUES (?)", ("momo9144",))
                conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()

# 添加管理员API端点，用于查看所有用户信息
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_get_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        username = request.args.get('username', '')
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 构建查询 - 使用正确的表结构
        query = """
            SELECT ua.username, ua.email, u.keywords 
            FROM users_auth ua 
            LEFT JOIN users u ON ua.id = u.id 
            WHERE ua.username != ?
        """
        params = [username]
        
        # 获取总记录数
        count_query = """
            SELECT COUNT(*) 
            FROM users_auth ua 
            WHERE ua.username != ?
        """
        total = DBHelper.execute_query(count_query, params, fetch_one=True)[0]
        
        # 获取分页数据
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        users = DBHelper.execute_query(query, params)
        
        return jsonify({
            'users': [{
                'username': user[0],
                'email': user[1],
                'keywords': user[2] if user[2] else ''
            } for user in users],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logging.error(f"获取用户列表失败: {str(e)}")
        return jsonify({'error': '获取用户列表失败'}), 500

@app.route('/api/check-username', methods=['POST'])
def api_check_username():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({'available': False, 'message': '用户名不能为空'}), 400
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT username FROM users_auth WHERE username=?", (username,))
        user = c.fetchone()
        if user:
            return jsonify({'available': False, 'message': '用户名已被注册'}), 200
        else:
            return jsonify({'available': True, 'message': '用户名可用'}), 200
    except Exception as e:
        return jsonify({'available': False, 'message': '检查失败'}), 500
    finally:
        conn.close()

def get_user_id_from_username(username):
    """通过用户名获取用户ID"""
    result = DBHelper.execute_query(
        "SELECT id FROM users_auth WHERE username=?", 
        (username,), 
        fetch_one=True
    )
    return result[0] if result else None

def get_user_config(user_id):
    """获取用户配置信息"""
    return DBHelper.execute_query(
        "SELECT keywords, email FROM users WHERE id=?", 
        (user_id,), 
        fetch_one=True
    )

@app.route('/api/user/delete', methods=['POST'])
@auth_required
def api_delete_account():
    # 从JWT令牌中获取用户名
    username = request.user.get('username')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 验证用户是否存在
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        
        if not user_result:
            return jsonify({'error': '用户不存在'}), 404
            
        user_id = user_result[0]
        
        # 检查是否为管理员账户（可选：阻止删除管理员账户）
        c.execute("SELECT * FROM admins WHERE username=?", (username,))
        is_admin = c.fetchone()
        if is_admin:
            return jsonify({'error': '管理员账户不能被注销'}), 403
        
        # 停止该用户的监控任务（如果有）
        c.execute("SELECT is_running FROM monitor_status WHERE user_id=?", (user_id,))
        monitor_status = c.fetchone()
        if monitor_status and monitor_status[0]:
            stop_monitoring(user_id)
            
        # 删除用户的监控状态
        c.execute("DELETE FROM monitor_status WHERE user_id=?", (user_id,))
        
        # 删除用户的监控记录
        c.execute("DELETE FROM products WHERE user_id=?", (user_id,))
        
        # 删除users表中的记录
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        
        # 删除users_auth表中的记录
        c.execute("DELETE FROM users_auth WHERE id=?", (user_id,))
        
        conn.commit()
        return jsonify({'message': '账户已删除'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'删除账户失败: {str(e)}'}), 500
    finally:
        conn.close()
            
@app.route('/api/admin/stop-all-monitors', methods=['POST'])
@admin_required
def api_stop_all_monitors():
    try:
        # 获取所有用户的ID
        query = """
            SELECT ua.id 
            FROM users_auth ua 
            WHERE ua.username != ?
        """
        username = request.args.get('username', '')
        users = DBHelper.execute_query(query, [username])
        
        # 更新所有用户的监控状态为停止
        for user in users:
            user_id = user[0]
            DBHelper.execute_query(
                "UPDATE monitor_status SET is_running=? WHERE user_id=?", 
                (False, user_id),
                commit=True
            )
        
        return jsonify({'message': '已停止所有用户的监控'}), 200
    except Exception as e:
        logging.error(f"停止所有监控失败: {str(e)}")
        return jsonify({'error': '停止所有监控失败'}), 500

@app.route('/api/admin/send-notification', methods=['POST'])
@admin_required
def api_send_notification():
    try:
        data = request.json
        subject = data.get('subject', '系统通知')
        content = data.get('content', '')
        
        if not content:
            return jsonify({'error': '邮件内容不能为空'}), 400
            
        # 获取所有用户的邮箱
        query = """
            SELECT ua.email 
            FROM users_auth ua 
            WHERE ua.username != ?
        """
        username = request.args.get('username', '')
        users = DBHelper.execute_query(query, [username])
        
        # 发送邮件给所有用户
        success_count = 0
        fail_count = 0
        
        for user in users:
            email = user[0]
            try:
                # 构建邮件内容
                msg_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">{subject}</h2>
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        {content}
                    </div>
                    <p style="color: #666; font-size: 12px;">
                        此邮件由Mercari监控系统自动发送。
                    </p>
                </div>
                """
                
                msg = MIMEMultipart('alternative')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = EMAIL_USER
                msg['To'] = email
                
                # 添加纯文本版本
                text_content = content
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
                
                # 添加HTML版本
                msg.attach(MIMEText(msg_content, 'html', 'utf-8'))
                
                # 发送邮件
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, [email], msg.as_string())
                server.quit()
                
                success_count += 1
            except Exception as e:
                logging.error(f"发送邮件到 {email} 失败: {str(e)}")
                fail_count += 1
        
        return jsonify({
            'message': f'邮件发送完成，成功：{success_count}，失败：{fail_count}'
        }), 200
    except Exception as e:
        logging.error(f"发送通知邮件失败: {str(e)}")
        return jsonify({'error': '发送通知邮件失败'}), 500
            
@app.route('/api/monitor/avg_time', methods=['GET'])
@auth_required
def get_average_scrape_time():
    # 从JWT令牌中获取用户名
    username = request.user.get('username')
    
    # 根据用户名获取用户ID
    user_id = get_user_id_from_username(username)
    
    if not user_id:
        return jsonify({'error': '用户不存在'}), 404
    
    try:
        # 获取最近10次抓取的平均时间
        avg_time = DBHelper.execute_query(
            """
            SELECT AVG(scrape_time) FROM 
            (SELECT scrape_time FROM scrape_logs 
             WHERE user_id = ? 
             ORDER BY timestamp DESC LIMIT 10)
            """,
            (user_id,),
            fetch_one=True
        )
        
        # 获取最近10次的时间列表，用于详细显示
        recent_times = DBHelper.execute_query(
            """
            SELECT scrape_time, timestamp FROM scrape_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 10
            """,
            (user_id,)
        )
        
        # 格式化结果
        recent_data = []
        for time_value, timestamp in recent_times:
            recent_data.append({
                "time": round(time_value, 2),
                "timestamp": timestamp
            })
        
        return jsonify({
            "average_time": round(avg_time[0] if avg_time[0] else 0, 2),
            "recent_data": recent_data,
            "count": len(recent_data)
        })
    except Exception as e:
        logger.error(f"获取平均抓取时间失败: {str(e)}")
        return jsonify({'error': f'获取平均抓取时间失败: {str(e)}'}), 500

if __name__ == "__main__":
    create_database()
    create_verification_table()
    set_admin_account()  # 设置管理员账号
    
    # 始终使用调试模式
    app.run(debug=True, host='0.0.0.0')