import git
import re
import requests
import os
import argparse
import xml.etree.ElementTree as ET  
import urllib.request

def find_modified_markdown_files(repo_path='.'):
    """在 Git 仓库中查找被修改过的 Markdown 文件。"""
    repo = git.Repo(repo_path)
    modified_files = []
    # repo.index.diff(None) 找出所有已修改但未暂存的文件
    for diff_item in repo.index.diff(None):
        if diff_item.a_path.endswith('.md'):
            path = os.path.join(repo_path,diff_item.a_path)
            modified_files.append(path)
    return modified_files

def download_papers_from_file(filepath):
    """从文件中提取 URL 并尝试下载 PDF。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    URL_REGEX = r'https?://[^\s()]+' 
    urls = re.findall(URL_REGEX, content)
    paper_urls = [url for url in urls if 'pdf' in url or 'arxiv' in url] 
    
    download_dir = os.path.join(os.path.dirname(filepath),'download')
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    for url in paper_urls:
        if 'arxiv.org/abs' in url:
            url = url.replace('/abs/', '/pdf/')
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status() 

            filename = os.path.join(download_dir, url.split('/')[-1])
            if not filename.endswith('.pdf'):
                 filename += '.pdf'
                 
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"成功下载: {url} -> {filename}")
            return os.path.join(download_dir,filename)
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 429:
             print(f"  -> API 请求过于频繁 (429)。脚本中的延迟可能需要增加。")
            else:
             print(f"  -> API 请求失败: {e}")
            return None

def get_paper_metadata(arxiv_id,pdf_path):
    """使用 Semantic Scholar Graph API 查询论文元数据。"""
    headers = {'User-Agent': 'MyNotesProcessor/1.0'}
    fields = 'title,authors,citationCount,url,publicationDate'
    api_url = f'https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields={fields}'

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        title = data.get('title', 'N/A')
        authors = ', '.join([author['name'] for author in data.get('authors', [])])
        citations = data.get('citationCount', 0)
        url = data.get('url', '')
        date = data.get('publicationDate', 'N/A')

        return {
            'title': title,
            'authors': authors,
            'citations': citations,
            'url': url,
            'date': date,
            'pdf_path': pdf_path
        }

    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")
        return get_metadata_from_arxiv_official(arxiv_id, pdf_path)

def get_metadata_from_arxiv_official(arxiv_id, pdf_path):
    """直接从 ArXiv 官方 API 获取元数据（支持最新论文），但没有引用数"""
    print(f" -> [备用] 正在尝试从 ArXiv 官方 API 获取: {arxiv_id}...")
    api_url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'
    
    try:
        with urllib.request.urlopen(api_url) as url:
            data = url.read()
        
        root = ET.fromstring(data)
        # ArXiv API 返回的是 Atom XML 格式
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', namespace)
        
        if entry is None:
            return None

        title = entry.find('atom:title', namespace).text.strip().replace('\n', ' ')
        published_raw = entry.find('atom:published', namespace).text
        published_date = published_raw[:10]
        authors_list = [author.find('atom:name', namespace).text for author in entry.findall('atom:author', namespace)]
        authors = ', '.join(authors_list)
        url = entry.find('atom:id', namespace).text
        
        return {
            'title': title,
            'authors': authors,
            'date': published_date,
            'citations': 'N/A',
            'url': url,
            'pdf_path': pdf_path
        }
    except Exception as e:
        print(f" -> 备用失败 ArXiv API 请求失败: {e}")
        return None
    
def format_and_process_links_in_file(filepath,download=False):
    """
    读取一个 Markdown 文件，查找 arXiv 链接，
    """
    print(f"--- 正在处理文件: {filepath} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        arxiv_abs_urls = re.findall(r'https?://arxiv\.org/abs/([a-z\-]+/\d{7}|\d+\.\d+)', content)

        if not arxiv_abs_urls:
            print("未找到新的 arXiv 链接，无需处理。")
            return
        
        if download:
            print("正在检查并下载 PDF...")
            pdf_path = download_papers_from_file(filepath)

        for arxiv_id in set(arxiv_abs_urls): 
            print(f"正在获取元数据: arXiv:{arxiv_id}")
            metadata = get_paper_metadata(arxiv_id,pdf_path)
            if metadata:
                original_url = f"https://arxiv.org/abs/{arxiv_id}"
                formatted_link = "[{title} - {authors}({date})]({url}) (Citations: {citations}) [PDF]({pdf_path})".format(
                    title=metadata['title'],
                    authors=metadata['authors'],
                    date=metadata.get('date', 'N/A'),
                    url=metadata['url'],
                    citations=metadata['citations'],
                    pdf_path =metadata['pdf_path']
                )
                print(f" -> 正在替换链接...")
                content = content.replace(original_url, formatted_link)

        if content != original_content:
            print(f"文件 {filepath} 已更新，正在写回...")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print("文件内容无变化。")
            
        print("--- 处理完成 ---")

    except Exception as e:
        print(f"处理文件 {filepath} 时发生错误: {e}")

##---执行---##
parser = argparse.ArgumentParser(description='Process modified markdown files.')
parser.add_argument('--repo', type=str, required=True, help='Path to Git repo (e.g., D:/poem/)')
args = parser.parse_args()

repo_path = args.repo
modified_files = find_modified_markdown_files(repo_path)

for file in modified_files:
    format_and_process_links_in_file(file, download=True)

#使用方法 python watch.py --repo D:/poem/