import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
import re
from dotenv import load_dotenv
import urllib3
from konlpy.tag import Okt

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 파일 로드
load_dotenv()

# 네이버 API 키 가져오기
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 주식 관련 키워드 리스트
stock_prediction_keywords_kr = [
    "주식", "증권", "투자", "경제", "주가",
    "금융", "시장", "코스피", "코스닥", "배당",
    "인플레이션", "금리", "성장", "채권", "분석",
    "상장", "매도", "매수", "공매도", "IPO", "유동성",
    "ETF", "기업", "실적", "재무", "수익률", "차트",
    "포트폴리오", "리스크", "리밸런싱", "배당금"
]

# 텍스트 정제 함수
def clean_text(text):
    if text is None:
        return ""
    clean = BeautifulSoup(text, "html.parser").get_text()
    clean = re.sub(r'[■▲▶●]', '', clean)
    clean = re.sub(r'[\n\r\t]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'[^\w\s]', '', clean)
    return clean

# 네이버 뉴스 API 호출 함수
def get_naver_news(query, start=1, display=10, sort='sim'):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)
    return response.json()

# 기사 본문 크롤링 함수
# 기사 본문 크롤링 함수
def get_article_content(url):
    """
    기사 URL에서 제목과 본문을 크롤링합니다.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')

        # 제목 추출
        title_tag = soup.select_one('div#ct > div.media_end_head.go_trans > div.media_end_head_title > h2')
        title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

        # 본문 추출 (여러 태그 시도)
        content_div = soup.find('div', {'id': 'dic_area'})  # 기본 본문 태그
        if not content_div:  # 다른 구조의 본문 처리
            content_div = soup.find('div', {'id': 'articleBodyContents'})  # 예비 태그

        content = content_div.get_text(separator=" ").strip() if content_div else "No Content Found"

        return {
            'title': clean_text(title),
            'content': clean_text(content)
        }
    except Exception as e:
        # 실패한 URL 로그 기록
        with open('failed_urls.log', 'a', encoding='utf-8') as log_file:
            log_file.write(f"Failed to crawl: {url}\nError: {e}\n")
        print(f"Error crawling {url}: {e}")
        return None

# 뉴스 데이터 수집 및 저장 함수
def collect_relevant_stock_news_kr():
    json_file = 'again.json'  # JSON 파일 이름
    articles = set()  # 중복 확인을 위한 링크 저장

    # JSON 파일 초기화
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            articles.update([article['link'] for article in existing_data])
    else:
        existing_data = []

    for keyword in stock_prediction_keywords_kr:
        print(f"Processing keyword: {keyword}")
        news_result = get_naver_news(keyword, start=1, display=10, sort='sim')
        
        if not news_result.get('items'):
            print(f"No articles found for keyword: {keyword}")
            continue

        for item in news_result.get('items', []):
            link = item['link']
            if link in articles:
                print(f"Skipping duplicate article: {link}")
                continue

            article_data = get_article_content(link)
            if not article_data or article_data['content'] == "No Content Found":
                print(f"Failed to crawl content for link: {link}")
                continue

            new_article = {
                'keyword': keyword,
                'title': article_data['title'],
                'content': article_data['content'],
                'link': link,
                'description': clean_text(item['description']),
                'pub_date': item['pubDate']
            }

            # 실시간으로 파일 업데이트
            existing_data.append(new_article)
            articles.add(link)  # 중복 확인을 위해 링크 저장
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

            print(f"Saved article: {new_article['title']}")

# 실행
collect_relevant_stock_news_kr()
