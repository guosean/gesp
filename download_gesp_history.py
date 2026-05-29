import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import re

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
        final_year = '2024'
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

def crawl_detail_page(url, year, month):
    links = []
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
        print(f"❌ 访问详情页失败: {url} - {str(e)}")
    
    return links

def crawl_index_page(base_url, max_pages=10):
    all_links = []
    seen_links = set()
    
    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            url = base_url
        else:
            url = base_url.replace('.html', f'_{page_num}.html')
        
        print(f"🔄 正在爬取页面 {page_num}: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 404:
                print("📭 页面不存在，停止爬取")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            article_links = soup.find_all('a', href=True)
            
            page_links = []
            for link in article_links:
                href = link['href']
                link_text = link.get_text(strip=True) if link else ""
                
                if href.startswith('/101/1010/') and href.endswith('.html'):
                    full_url = urllib.parse.urljoin(base_url, href)
                    if '真题' in link_text or '试题' in link_text or '考试' in link_text:
                        date_match = re.search(r'(\d{4})[-年](\d{1,2})月', link_text)
                        year = date_match.group(1) if date_match else "未知"
                        month = date_match.group(2).zfill(2) if date_match else "01"
                        page_links.append((full_url, link_text, year, month))
            
            for href, link_text, year, month in page_links:
                if href not in seen_links:
                    seen_links.add(href)
                    print(f"🔍 进入详情页: {link_text}")
                    detail_links = crawl_detail_page(href, year, month)
                    all_links.extend(detail_links)
            
            print(f"✅ 从页面 {page_num} 找到 {len(page_links)} 个详情页链接")
        
        except Exception as e:
            print(f"❌ 访问页面失败: {url} - {str(e)}")
            break
    
    return all_links

def main():
    base_url = "https://gesp.ccf.org.cn/101/1010/index.html"
    save_dir = "gesp_downloads"
    
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"🔄 开始爬取索引页面: {base_url}")
    
    all_links = crawl_index_page(base_url)
    
    if not all_links:
        print("❌ 未找到任何可下载的文件")
        return
    
    print(f"\n📊 共找到 {len(all_links)} 个符合条件的文件")
    
    print(f"\n📂 开始下载到目录: {save_dir}")
    downloaded_count = 0
    skipped_count = 0
    
    for href, link_text, year, month in all_links:
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