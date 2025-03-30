import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import random
import time
import base64
import threading
import string
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import logging
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import traceback

# 检查是否为生产环境
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'

# 配置日志
log_level = logging.INFO if IS_PRODUCTION else logging.DEBUG
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mercari_monitor.log"),
        # 在生产环境不输出到控制台
        logging.StreamHandler() if not IS_PRODUCTION else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置信息
DB_NAME = "mercari_monitor.db"
CHECK_INTERVAL = 0.1  
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

def get_page_content_with_selenium(url):
    try:
        logger.info(f"使用Selenium开始获取页面: {url}")
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        
        # 添加更多浏览器特性模拟
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 在生产环境中禁止WebDriverManager的输出
        os.environ['WDM_LOG_LEVEL'] = '0' if IS_PRODUCTION else '20'
        logger.info("初始化Chrome WebDriver")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        
        # 修改webdriver属性，绕过检测
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info(f"开始访问URL: {url}")
        # 添加更多随机行为
        driver.get(url)
        
        # 模拟随机滚动
        for i in range(3):
            scroll_amount = random.randint(300, 700)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(1, 3))
        
        # 等待页面加载 - 增加更多的等待时间以确保骨架屏消失
        wait_time = random.uniform(8, 12)
        logger.info(f"等待页面加载完成: {wait_time:.2f}秒")
        time.sleep(wait_time)
        
        # 尝试等待骨架屏元素消失
        try:
            # 尝试等待直到没有骨架屏元素
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.CLASS_NAME, "merSkeleton"))
            )
            logger.info("骨架屏元素已消失，页面内容完全加载")
        except Exception as e:
            logger.warning(f"等待骨架屏消失失败，将继续处理: {str(e)}")
            # 额外等待几秒尝试确保内容加载
            time.sleep(5)
        
        # 尝试查找内容加载的指标
        try:
            loaded_items = driver.find_elements(By.CSS_SELECTOR, '[data-testid="item-cell"] [data-testid="thumbnail-item-name"]')
            if loaded_items:
                logger.info(f"已找到 {len(loaded_items)} 个带名称的商品项，页面可能已完全加载")
            else:
                logger.warning("未找到商品名称元素，页面可能未完全加载")
                # 再次随机滚动尝试触发懒加载
                for i in range(2):
                    scroll_amount = random.randint(300, 700)
                    driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
                    time.sleep(2)
        except Exception as e:
            logger.warning(f"检查商品名称元素时出错: {str(e)}")
        
        # 仅在非生产环境下保存调试信息
        if not IS_PRODUCTION:
            # 截取页面截图，用于调试
            screenshot_file = "mercari_screenshot.png"
            driver.save_screenshot(screenshot_file)
            logger.info(f"已保存页面截图到 {screenshot_file}")
        
        html_content = driver.page_source
        logger.info(f"成功获取页面源代码，长度: {len(html_content)}")

        # 仅在非生产环境下保存HTML
        if not IS_PRODUCTION:
            # 保存HTML用于分析
            with open("mercari_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
                logger.info("已保存HTML内容到mercari_debug.html文件")
            
        # 检查页面上是否包含商品元素
        item_cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="item-cell"]')
        if item_cells:
            logger.info(f"页面上找到 {len(item_cells)} 个商品元素")
            
            # 检查第一个商品的文本
            if len(item_cells) > 0:
                try:
                    first_item_text = item_cells[0].text
                    logger.debug(f"第一个商品元素文本: {first_item_text[:100]}...")
                except:
                    logger.warning("无法获取第一个商品元素文本")
                    
            # 检查是否还有骨架屏元素
            skeleton_elements = driver.find_elements(By.CLASS_NAME, "merSkeleton")
            if skeleton_elements:
                logger.warning(f"页面上仍有 {len(skeleton_elements)} 个骨架屏元素，内容可能未完全加载")

        # 关闭浏览器
        driver.quit()
        logger.debug("WebDriver已关闭")
        
        # 检查页面内容中是否包含关键标识
        if 'item-cell' in html_content:
            logger.info(f"Selenium成功获取页面内容，长度: {len(html_content)}")
            return html_content
        else:
            # 尝试其他关键标识
            alternative_identifiers = ['thumbnail-item-name', 'merItemThumbnail', 'href="/item/', 'data-location="search_result']
            for identifier in alternative_identifiers:
                if identifier in html_content:
                    logger.info(f"找到替代标识符 '{identifier}'，页面加载可能成功")
                    return html_content
                    
            logger.error("Selenium获取页面不完整，可能被反爬虫机制拦截")
            return None
    except Exception as e:
        logger.error(f"Selenium获取页面失败: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def parse_products(html):
    if not html:
        logger.error("HTML内容为空，无法解析")
        return []
        
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    
    # 尝试不同的选择器模式来定位商品项
    selectors = [
        # 新的Mercari选择器模式
        '[data-testid="item-cell"]',
        '[data-testid="search-items"] > div',
        '.merItemThumbnail',
        '.merListItem',
        '[role="listitem"]',
        '[data-location*="search_result"]',
        # 通用选择器尝试
        'a[href*="/item/"]'
    ]
    
    items = []
    for selector in selectors:
        items = soup.select(selector)
        if items:
            logger.info(f"成功使用选择器 '{selector}' 找到 {len(items)} 个商品项")
            break
    
    if not items:
        logger.error("无法找到商品项，网站结构可能已更改")
        # 保存HTML以便分析
        with open("mercari_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("已保存HTML到mercari_debug.html文件供分析")
        return []
    
    # 在非生产环境才保存调试文件
    if not IS_PRODUCTION:
        # 将整个HTML保存为本地文件，用于调试分析
        with open("mercari_full_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("已保存完整HTML到mercari_full_debug.html文件供分析")
            
        # 提取特定商品的示例HTML，用于学习结构
        if len(items) > 0:
            with open("mercari_item_example.html", "w", encoding="utf-8") as f:
                f.write(str(items[0]))
            logger.info("已保存第一个商品HTML示例到mercari_item_example.html")
    
    for item_index, item in enumerate(items):
        try:
            # 处理骨架屏加载的情况 - 检查是否为骨架屏元素
            skeleton_elem = item.select_one('.merSkeleton')
            if skeleton_elem:
                logger.info("检测到骨架屏元素，这是尚未加载完成的占位符")
                # 提取商品信息时使用默认值或从链接中提取的ID
                link_elem = item.select_one('a[href*="/item/"]')
                if link_elem and link_elem.has_attr('href'):
                    product_id = link_elem['href'].split('/')[-1] if '/' in link_elem['href'] else ''
                    price_elem = item.select_one('[class*="price"]')
                    price = price_elem.text.strip() if price_elem else "価格未知"
                    
                    # 构建基本产品信息
                    product = {
                        'id': product_id,
                        'name': f"商品加载中 (ID: {product_id})", # 更清晰的提示
                        'price': price,
                        'image_url': "https://static.mercdn.net/images/mercari_profile.png",
                        'product_url': link_elem['href'] if link_elem['href'].startswith('http') else f"https://jp.mercari.com{link_elem['href']}",
                        'stock_status': 'on_sale'
                    }
                    products.append(product)
                continue  # 跳过其余处理，继续下一个商品项
                
            # 检查文本是否是有效的商品名称的函数
            def is_valid_name(text):
                if not text:
                    return False
                
                # 排除明显是折扣标记的文本
                discount_patterns = [
                    r'\d+%\s*OFF', 
                    r'SALE', 
                    r'セール', 
                    r'割引',
                    r'^\d+%$', 
                    r'^OFF$',
                    r'^\d+%オフ$',
                    r'特価',
                    r'値下げ',
                    r'^送料無料$',
                    r'^即購入OK$',
                    r'^匿名配送$'
                ]
                
                for pattern in discount_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        logger.debug(f"跳过折扣标记: {text}")
                        return False
                
                # 排除纯价格格式
                price_patterns = [
                    r'^¥\s*[\d,]+$',  # 日元价格格式 (¥1,000)
                    r'^\$\s*[\d,\.]+$',  # 美元价格格式 ($10.99)
                    r'^EUR\s*[\d,\.]+$',  # 欧元价格格式 (EUR10.99)
                    r'^\d+円$',  # 日元（数字+円）(1000円)
                    r'^[\d,]+$',  # 纯数字 (1000)
                    r'^[\d,]+円$',  # 数字+円带千位分隔符 (1,000円)
                ]
                for pattern in price_patterns:
                    if re.search(pattern, text):
                        logger.debug(f"跳过价格标记: {text}")
                        return False
                
                # 排除过短的名称
                if len(text) < 3:
                    logger.debug(f"跳过过短名称: {text}")
                    return False
                
                # 排除纯由数字、特殊字符组成的文本
                if re.match(r'^[0-9¥$€£,.%\s]+$', text):
                    logger.debug(f"跳过纯数字或特殊字符名称: {text}")
                    return False
                
                return True
            
            # 按照优先级顺序定义名称选择器
            name_selectors = [
                '[data-testid="thumbnail-item-name"]',  # 高优先级选择器
                'span[data-testid="item-name"]',
                '[data-testid="name"]',
                '.merItemTitle h3',
                '.item-name',
                '.item-title',
                'h3',
                'figcaption',
                'p.primary__5616e150',
                # 更通用的选择器
                'figcaption span',
                '.merText:not([class*="price"])',
                'div > span:not([class*="price"])',
                'a[data-location*="search_result"] span:not([class*="price"])',
                'a[href*="/item/"] span:not([class*="price"])',
                # 极其通用的选择器（作为最后尝试）
                'p',
                'div'
            ]
            
            # 尝试找到有效商品名称
            name = None
            valid_name_found = False
            
            # 保存第一个找到的价格元素文本，用于后续分析
            first_price_elem = item.select_one('[class*="price"]')
            first_price_text = first_price_elem.text.strip() if first_price_elem else None
            
            for selector in name_selectors:
                name_elems = item.select(selector)
                for name_elem in name_elems:
                    if name_elem and name_elem.text.strip():
                        potential_name = name_elem.text.strip()
                        
                        # 跳过与价格完全匹配的文本
                        if first_price_text and first_price_text == potential_name:
                            logger.debug(f"跳过与价格相同的文本: {potential_name}")
                            continue
                            
                        # 检查是否是有效的商品名称
                        if is_valid_name(potential_name):
                            name = potential_name
                            logger.info(f"找到有效商品名称: {name}，使用选择器: {selector}")
                            valid_name_found = True
                            break
                        else:
                            logger.debug(f"忽略无效名称: {potential_name}，使用选择器: {selector}")
                    
                if valid_name_found:
                    break
            
            # 新增：尝试使用item元素的title属性
            if not valid_name_found:
                if item.has_attr('title') and is_valid_name(item['title']):
                    name = item['title']
                    valid_name_found = True
                    logger.info(f"从元素title属性找到有效名称: {name}")
                    
                # 尝试查找子元素的title属性
                else:
                    for elem in item.select('[title]'):
                        if elem.has_attr('title') and is_valid_name(elem['title']):
                            name = elem['title']
                            valid_name_found = True
                            logger.info(f"从子元素title属性找到有效名称: {name}")
                            break
                            
            # 新增：尝试使用alt属性中的描述文本
            if not valid_name_found:
                img_with_alt = item.select_one('img[alt]')
                if img_with_alt and img_with_alt.has_attr('alt') and is_valid_name(img_with_alt['alt']):
                    name = img_with_alt['alt']
                    valid_name_found = True
                    logger.info(f"从图片alt属性找到有效名称: {name}")
                    
            # 尝试提取商品描述信息
            if not valid_name_found:
                # 尝试找描述信息
                desc_selectors = [
                    '[data-testid="item-description"]',
                    '[data-testid="description"]',
                    '.item-description',
                    '.description',
                    'p.description'
                ]
                
                for selector in desc_selectors:
                    desc_elem = item.select_one(selector)
                    if desc_elem and desc_elem.text.strip() and is_valid_name(desc_elem.text.strip()):
                        name = desc_elem.text.strip()
                        valid_name_found = True
                        logger.info(f"从商品描述中找到名称: {name}")
                        break
                    
            if not valid_name_found:
                # 尝试使用元素文本或商品ID
                text_content = item.get_text(strip=True)
                
                # 移除任何明显的折扣信息和价格信息
                for pattern in [r'\d+%\s*OFF', r'SALE', r'セール', r'割引', r'¥\s*[\d,]+', r'\$\s*[\d,\.]+', r'送料無料', r'即購入OK', r'匿名配送']:
                    text_content = re.sub(pattern, '', text_content, flags=re.IGNORECASE).strip()
                
                if text_content and len(text_content) > 5:
                    # 尝试通过寻找价格模式来分割文本
                    price_match = re.search(r'(¥\s*[\d,]+|\$\s*[\d,\.]+|EUR\s*[\d,\.]+|\d+円|[\d,]+円)', text_content)
                    if price_match:
                        # 使用价格之前的文本作为名称
                        potential_name = text_content[:price_match.start()].strip()
                        if is_valid_name(potential_name):
                            name = potential_name[:100] if len(potential_name) > 100 else potential_name
                            logger.info(f"从文本中提取出名称: {name}")
                        else:
                            # 尝试在价格之后寻找名称
                            potential_name = text_content[price_match.end():].strip()
                            if is_valid_name(potential_name):
                                name = potential_name[:100] if len(potential_name) > 100 else potential_name
                                logger.info(f"从价格后文本中提取出名称: {name}")
                            else:
                                # 如果前后都不是有效名称，使用不包含折扣和价格的元素文本
                                cleaned_text = text_content
                                # 移除所有匹配价格模式的内容
                                price_patterns = [
                                    r'¥\s*[\d,]+',
                                    r'\$\s*[\d,\.]+',
                                    r'EUR\s*[\d,\.]+',
                                    r'\d+円',
                                    r'[\d,]+円'
                                ]
                                for pattern in price_patterns:
                                    cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE).strip()
                                
                                # 尝试分割成行，可能会有更好的结果
                                lines = cleaned_text.split('\n')
                                for line in lines:
                                    if line and len(line.strip()) > 5 and is_valid_name(line.strip()):
                                        name = line.strip()[:100]
                                        logger.info(f"从分行文本中提取名称: {name}")
                                        break
                                
                                if not name and len(cleaned_text) > 5:
                                    name = cleaned_text[:100].strip()
                                    logger.info(f"使用清理后的元素文本作为名称: {name}")
                    else:
                        # 如果没有找到价格，使用清理后的文本
                        if is_valid_name(text_content):
                            name = text_content[:100].strip()
                            logger.info(f"使用元素文本作为名称: {name}")
                        else:
                            # 尝试分割文本并找到有效部分
                            lines = text_content.split('\n')
                            for line in lines:
                                if line and len(line.strip()) > 5 and is_valid_name(line.strip()):
                                    name = line.strip()[:100]
                                    logger.info(f"从分行文本中提取名称: {name}")
                                    break
                
                # 尝试从URL提取信息作为名称
                if not name or len(name) < 5:
                    link_elem = item.select_one('a[href*="/item/"]')
                    if link_elem and link_elem.has_attr('href'):
                        item_id = link_elem['href'].split('/')[-1]
                        
                        # 尝试查看链接中是否包含其他信息
                        url_parts = link_elem['href'].split('/')
                        if len(url_parts) > 4:
                            url_name_part = url_parts[-2]
                            if url_name_part != 'item' and is_valid_name(url_name_part):
                                name = f"{url_name_part.replace('-', ' ').replace('_', ' ').title()} (ID: {item_id})"
                                logger.info(f"从URL中提取出名称: {name}")
                            else:
                                name = f"商品 (ID: {item_id})"
                                logger.info(f"使用商品ID作为名称: {name}")
                        else:
                            name = f"商品 (ID: {item_id})"
                            logger.info(f"使用商品ID作为名称: {name}")
                    else:
                        # 如果完全无法获取信息
                        name = f"未命名商品 #{item_index+1}"
                        logger.warning(f"无法找到商品名称，使用索引: {name}")
            
            # 尝试多种价格选择器
            price = None
            price_selectors = [
                '.merPrice', 
                '[data-testid="price"]', 
                'span[class*="price"]',
                '.item-price',
                '.sc-6031d55c-1',
                '.price'
            ]
            
            for selector in price_selectors:
                price_elem = item.select_one(selector)
                if price_elem and price_elem.text.strip():
                    price = price_elem.text.strip()
                    break
                    
            if not price:
                # 如果找不到价格，尝试从文本内容中提取
                price_match = re.search(r'(¥\s*[\d,]+|\$\s*[\d,\.]+|EUR\s*[\d,\.]+|\d+円|[\d,]+円)', item.get_text())
                if price_match:
                    price = price_match.group(0).strip()
                else:
                    # 使用默认值
                    price = "価格未知"
            
            # 尝试多种图片选择器
            image = None
            img_elem = item.select_one('img')
            if img_elem and img_elem.has_attr('src'):
                image = img_elem['src']
            else:
                # 尝试查找懒加载图片属性
                img_elem = item.select_one('img[data-src]')
                if img_elem and img_elem.has_attr('data-src'):
                    image = img_elem['data-src']
                else:
                    # 尝试其他可能的图片属性
                    for attr in ['data-thumbnail', 'data-original', 'data-lazy-src', 'data-bg', 'data-image']:
                        img_elem = item.select_one(f'img[{attr}]')
                        if img_elem and img_elem.has_attr(attr):
                            image = img_elem[attr]
                            break
                    
                    # 尝试查找背景图片
                    if not image:
                        for elem in item.select('[style*="background"]'):
                            style = elem.get('style', '')
                            bg_match = re.search(r'background(?:-image)?:\s*url\([\'"]?(.*?)[\'"]?\)', style)
                            if bg_match:
                                image = bg_match.group(1)
                                break
                    
            if not image:
                # 默认图片
                image = "https://static.mercdn.net/images/mercari_profile.png"
            
            # 获取链接
            link = None
            # 如果当前元素是链接
            if item.name == 'a' and item.has_attr('href'):
                link = item['href']
            else:
                # 尝试找子元素中的链接
                link_elem = item.select_one('a[href]')
                if link_elem and link_elem.has_attr('href'):
                    link = link_elem['href']
                    
            if not link:
                logger.warning("无法找到商品链接，跳过")
                continue
                
            # 确保完整URL
            if link.startswith('/'):
                link = f"https://jp.mercari.com{link}"
                
            # 提取商品ID
            product_id = link.split('/')[-1] if '/' in link else ''
            
            # 构建产品信息
            product = {
                'id': product_id,
                'name': name,
                'price': price,
                'image_url': image,
                'product_url': link,
                'stock_status': 'on_sale'
            }
            
            products.append(product)
            logger.info(f"成功解析商品: {name}, 价格: {price}")
            
        except Exception as e:
            logger.warning(f"解析单个商品时出错: {str(e)}")
            logger.warning(traceback.format_exc())
            continue
    
    logger.info(f"总共解析到 {len(products)} 个商品")
    
    # 新增：记录有多少商品使用了ID作为名称
    id_as_name_count = sum(1 for p in products if "ID:" in p['name'])
    if id_as_name_count > 0:
        logger.warning(f"{id_as_name_count}/{len(products)} 个商品使用ID作为名称")
    
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

# 恢复原始URL格式
BASE_URL = "https://jp.mercari.com/search?search_condition_id=1cx0xHGsd{encoded_keyword}"

def run_monitor(user_id):
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
            
            # 使用原来的URL生成方式
            encoded_keyword = encode_keyword_to_base64(keywords)
            target_url = BASE_URL.format(encoded_keyword=encoded_keyword)
            
            logger.info(f"请求URL: {target_url}")
            html = get_page_content_with_selenium(target_url)
            
            if html:
                # 移除过于详细的日志输出
                if not IS_PRODUCTION:
                    logger.debug(f"成功获取HTML内容，长度: {len(html)}")
                
                # 检查是否包含骨架屏元素
                if 'merSkeleton' in html:
                    logger.warning("HTML中检测到骨架屏元素，页面可能未完全加载，但仍将尝试解析")
                
                products = parse_products(html)
                
                if products:
                    logger.info(f"解析到 {len(products)} 个商品")
                    
                    # 检查是否所有商品名称都与价格相同（通常是骨架屏情况）
                    price_as_name_count = sum(1 for p in products if p['name'] == p['price'])
                    if price_as_name_count > 0:
                        logger.warning(f"检测到 {price_as_name_count}/{len(products)} 个商品使用价格作为名称，可能是骨架屏")
                        
                    # 至少有一个产品能够正确解析
                    if len(products) > price_as_name_count:
                        # 减少输出示例，使用简洁格式
                        logger.info(f"商品示例: {products[0]['name'][:30]}..., {products[0]['price']}")
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
                        logger.warning("所有商品都使用价格作为名称，页面可能未完全加载，跳过更新数据库")
                else:
                    logger.warning("未解析到任何商品，检查解析函数")
            else:
                logger.error("获取页面内容失败，检查网络连接或Selenium配置")
            
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
        
        if token != 'your_jwt_token_here':
            return jsonify({'error': '未授权访问'}), 401
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]
        
        username = request.args.get('username', '')
        if not username:
            return jsonify({'error': '未提供用户名'}), 400
            
        try:
            is_admin = DBHelper.execute_query(
                "SELECT * FROM admins WHERE username=?", 
                (username,), 
                fetch_one=True
            )
            
            if not is_admin:
                return jsonify({'error': '未授权的访问'}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'认证失败: {str(e)}'}), 500
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
def api_user_update():
    # 从认证令牌中获取用户ID
    token = request.headers.get('Authorization', '')
    if token.startswith('Bearer '):
        token = token[7:]  # 去掉'Bearer '前缀
    
    # 这里应该解析JWT token获取用户ID
    # 简化版：从token中提取用户名，然后查询用户ID
    if token == 'your_jwt_token_here':  # 测试用的token
        data = request.json
        keywords = data.get('keywords', '')
        email = data.get('email', '')
        
        # 获取请求中的用户名（应该从token中解析）
        username = request.args.get('username', '')
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # 先通过用户名查询用户ID
            if username:
                c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
                user_result = c.fetchone()
                if user_result:
                    user_id = user_result[0]
                else:
                    return jsonify({'error': '用户不存在'}), 404
            else:
                return jsonify({'error': '未提供用户名'}), 400
            
            # 更新用户信息
            c.execute("UPDATE users SET keywords=?, email=? WHERE id=?", 
                      (keywords, email, user_id))
            
            # 同时更新users_auth表中的email
            if username:
                c.execute("UPDATE users_auth SET email=? WHERE username=?", 
                          (email, username))
                
            conn.commit()
            return jsonify({'message': '设置已更新'}), 200
        except Exception as e:
            return jsonify({'error': '更新失败'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': '未授权'}), 401

@app.route('/api/monitor/start', methods=['POST'])
def api_monitor_start():
    username = request.args.get('username', '')
    
    if not username:
        return jsonify({'error': '未提供用户名'}), 400
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        
        if not user_result:
            return jsonify({'error': '用户不存在'}), 404
            
        user_id = user_result[0]
        success = start_monitoring(user_id)
        
        if success:
            return jsonify({'message': '监控已启动'}), 200
        else:
            return jsonify({'error': '无法启动监控，请确保已设置关键词'}), 400
    except Exception as e:
        return jsonify({'error': '启动监控失败'}), 500
    finally:
        conn.close()

@app.route('/api/monitor/stop', methods=['POST'])
def api_monitor_stop():
    username = request.args.get('username', '')
    
    if not username:
        return jsonify({'error': '未提供用户名'}), 400
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        
        if not user_result:
            return jsonify({'error': '用户不存在'}), 404
            
        user_id = user_result[0]
        success = stop_monitoring(user_id)
        
        if success:
            return jsonify({'message': '监控已停止'}), 200
        else:
            return jsonify({'error': '停止监控失败'}), 500
    except Exception as e:
        return jsonify({'error': '停止监控失败'}), 500
    finally:
        conn.close()

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
            
            return jsonify({
                'token': 'your_jwt_token_here',
                'isAdmin': is_admin
            }), 200
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    except Exception as e:
        return jsonify({'error': '登录失败'}), 500
    finally:
        conn.close()

@app.route('/api/monitor/status', methods=['GET'])
def api_monitor_status():
    username = request.args.get('username', '')
    
    if not username:
        return jsonify({'error': '未提供用户名'}), 400
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 根据用户名获取用户ID
        c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
        user_result = c.fetchone()
        
        if not user_result:
            return jsonify({'error': '用户不存在'}), 404
            
        user_id = user_result[0]
        
        # 创建监控状态表（如果不存在）
        c.execute('''CREATE TABLE IF NOT EXISTS monitor_status 
                 (user_id INTEGER PRIMARY KEY,
                  is_running BOOLEAN,
                  last_check TEXT,
                  new_products INTEGER)''')
        
        # 查询该用户的监控状态
        c.execute("SELECT is_running, last_check, new_products FROM monitor_status WHERE user_id=?", (user_id,))
        status_result = c.fetchone()
        
        if not status_result:
            # 如果没有记录，创建默认记录
            c.execute("INSERT INTO monitor_status (user_id, is_running, last_check, new_products) VALUES (?, ?, ?, ?)",
                     (user_id, False, None, 0))
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
def api_user_info():
    # 从认证令牌中获取用户ID
    token = request.headers.get('Authorization', '')
    if token.startswith('Bearer '):
        token = token[7:]  # 去掉'Bearer '前缀
    
    # 这里应该解析JWT token获取用户ID
    # 简化版：从token中提取用户名，然后查询用户ID
    if token == 'your_jwt_token_here':  # 测试用的token
        # 获取请求中的用户名（应该从token中解析）
        username = request.args.get('username', '')
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # 先通过用户名查询用户ID
            if username:
                c.execute("SELECT id FROM users_auth WHERE username=?", (username,))
                user_result = c.fetchone()
                if user_result:
                    user_id = user_result[0]
                else:
                    return jsonify({'error': '用户不存在'}), 404
            else:
                return jsonify({'error': '未提供用户名'}), 400
                
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
    else:
        return jsonify({'error': '未授权'}), 401

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
            run_monitor(user_id)
            
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
def api_delete_account():
    # 从认证令牌中获取用户ID
    token = request.headers.get('Authorization', '')
    if token.startswith('Bearer '):
        token = token[7:]  # 去掉'Bearer '前缀
    
    # 验证token (这里使用简化版验证)
    if token != 'your_jwt_token_here':  # 应改为实际的token验证
        return jsonify({'error': '未授权'}), 401
    
    username = request.args.get('username', '')
    
    if not username:
        return jsonify({'error': '未提供用户名'}), 400
        
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
            # 更新监控状态为停止
            c.execute("UPDATE monitor_status SET is_running=? WHERE user_id=?", 
                    (False, user_id))
        
        # 开始事务删除用户所有相关数据
        # 1. 删除监控状态
        c.execute("DELETE FROM monitor_status WHERE user_id=?", (user_id,))
        
        # 2. 删除用户配置
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        
        # 3. 删除用户产品数据
        c.execute("DELETE FROM products WHERE user_id=?", (user_id,))
        
        # 4. 最后删除用户账户
        c.execute("DELETE FROM users_auth WHERE id=?", (user_id,))
        
        # 提交事务
        conn.commit()
        
        logger.info(f"用户 {username} 已注销账户")
        return jsonify({'message': '账户已成功注销'}), 200
            
    except Exception as e:
        conn.rollback()
        logger.error(f"注销账户失败: {str(e)}")
        return jsonify({'error': f'注销账户失败: {str(e)}'}), 500
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
def get_average_scrape_time():
    username = request.args.get('username')
    
    if not username:
        return jsonify({'error': '未提供用户名'}), 400
    
    # 使用与其他API一致的身份验证方式
    token = request.headers.get('Authorization', '')
    if token.startswith('Bearer '):
        token = token[7:]  # 去掉'Bearer '前缀
    
    # 这里简化验证，实际应该检查token的有效性
    if token != 'your_jwt_token_here':  # 测试用的token
        return jsonify({'error': '未授权'}), 401
    
    try:
        # 根据用户名获取用户ID
        user_id = get_user_id_from_username(username)
        
        if not user_id:
            return jsonify({'error': '用户不存在'}), 404
        
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
    
    # 根据环境变量配置Flask运行模式
    debug_mode = not IS_PRODUCTION
    
    # 生产环境中关闭Flask内置的启动消息和其他日志输出
    if IS_PRODUCTION:
        import werkzeug
        # 修复werkzeug日志配置，避免NoneType错误
        try:
            if hasattr(werkzeug, '_internal') and hasattr(werkzeug._internal, '_logger'):
                werkzeug._internal._logger.setLevel(logging.ERROR)
        except:
            logger.warning("无法设置werkzeug内部日志级别")
        
        # 设置Flask应用相关日志级别
        app.logger.setLevel(logging.ERROR)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    # 启动应用服务器
    app.run(debug=debug_mode, host='0.0.0.0')