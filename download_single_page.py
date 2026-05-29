import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import re
import sys

def extract_info_from_link(link_text, href, year=None, month=None):
    text = link_text + " " + href
    
    lang_match = re.search(r'([Cc]\+\+|[Cc]pp|[Pp]ython)', text)
    
    level_patterns = [
        r'(\d+)级',
        r'一级|二级|三级|四级|五级|六级',
        r'level.?(\d+)',
        r'Level.?(\d+)',
        r'(\d+) level',
        r'(\d+)[-_]?level',
        r'L(\d+)',
        r'等级(\d+)',
        r'grade.?(\d+)',
        r'Grade.?(\d+)'
    ]
    
    level = "未知"
    for pattern in level_patterns:
        level_match = re.search(pattern, text)
        if level_match:
            if level_match.lastindex and level_match.group(1):
                level = level_match.group(1)
            else:
                level_map = {'一级': '1', '二级': '2', '三级': '3', '四级': '4', '五级': '5', '六级': '6'}
                level = level_map.get(level_match.group(0), "未知")
            break
    
    if not lang_match:
        return None
    
    language = "C++" if '++' in lang_match.group(1) or 'cpp' in lang_match.group(1).lower() else "Python"
    
    level_map = {'1': '一级', '2': '二级', '3': '三级', '4': '四级', '5': '五级', '6': '六级', '7': '七级', '8': '八级', '未知': '未知级别'}
    level_name = level_map.get(level, f"{level}级")
    
    final_year = year
    final_month = month
    
    if not (final_year and final_month):
        date_match = re.search(r'(\d{4})[-年](\d{1,2})', text)
        if date_match:
            final_year = date_match.group(1)
            final_month = date_match.group(2).zfill(2)
    
    if not (final_year and final_month):
        final_year = '2023'
        final_month = '06'
    
    filename = f"{language}-{level}级-{final_year}{final_month}"
    
    return {
        'filename': filename,
        'language': language,
        'level': level_name
    }

def download_file(url, save_dir, info=None):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or '.pdf'
        
        if info:
            filename = f"{info['filename']}{ext}"
            target_dir = os.path.join(save_dir, info['level'], info['language'])
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
        else:
            filename = os.path.basename(urllib.parse.urlparse(url).path) or f"download{ext}"
            filepath = os.path.join(save_dir, filename)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > 1024:
                print(f"⏭️ 跳过（已存在）: {filepath}")
                return True, False
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r下载中: {filename} {progress:.1f}%", end='')
        
        print(f"\n✅ 已下载: {filepath} ({format_size(total_size)})")
        return True, True
    except Exception as e:
        print(f"\n❌ 下载失败: {url} - {str(e)}")
        return False, False

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def extract_date_from_url(url, page_title=""):
    """从URL和页面标题中提取年份和月份"""
    text = url + " " + page_title
    
    date_patterns = [
        r'(\d{4})[-年](\d{1,2})月',
        r'(\d{4})[-年](\d{1,2})',
        r'/(\d{4})(\d{2})\d*\.html',
        r'(\d{4})[-_](\d{2})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1), match.group(2).zfill(2)
    
    return None, None

def crawl_single_page(url):
    """爬取单个详情页面"""
    links = []
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_title = soup.title.string if soup.title else ""
        
        year, month = extract_date_from_url(url, page_title)
        
        file_extensions = ('.pdf', '.zip', '.rar', '.doc', '.docx')
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            link_text = link.get_text(strip=True) if link else ""
            
            if any(href.lower().endswith(ext) for ext in file_extensions):
                if not href.startswith('http'):
                    href = urllib.parse.urljoin(url, href)
                
                full_text = link_text + " " + href
                if 'C++' in full_text or 'cpp' in full_text.lower() or 'Python' in full_text or 'python' in full_text.lower():
                    links.append((href, link_text, year, month))
    
    except Exception as e:
        print(f"❌ 访问页面失败: {url} - {str(e)}")
    
    return links

def main():
    default_urls = ["https://gesp.ccf.org.cn/101/1010/10092.html"]
    
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        urls = default_urls
    
    save_dir = "gesp_downloads"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"🔄 开始爬取 {len(urls)} 个页面...")
    
    downloaded_count = 0
    skipped_count = 0
    
    for url in urls:
        print(f"\n📄 处理页面: {url}")
        links = crawl_single_page(url)
        
        if not links:
            print("  ❌ 未找到可下载的文件")
            continue
        
        for href, link_text, year, month in links:
            info = extract_info_from_link(link_text, href, year, month)
            if info:
                success, is_new = download_file(href, save_dir, info)
                if success:
                    downloaded_count += 1
                    if not is_new:
                        skipped_count += 1
    
    print(f"\n🎉 下载完成！成功下载 {downloaded_count} 个文件（{skipped_count} 个已存在跳过）")

if __name__ == "__main__":
    main()