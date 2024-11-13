import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
import re
from dotenv import load_dotenv
from konlpy.tag import Okt

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

# HTML 태그 및 특수문자 제거
def clean_text(text):
    """
    텍스트에서 HTML 태그와 특수문자를 제거합니다.
    """
    if text is None:
        return ""
    # HTML 태그 제거
    text = BeautifulSoup(text, 'html.parser').get_text()
    # 특수 문자 제거
    return re.sub(r'[^a-zA-Z0-9가-힣\s]', '', text).strip()

# 네이버 뉴스 API 호출
def get_naver_news(query, start=1, display=10, sort='sim'):
    """
    네이버 뉴스 API를 호출하여 검색 결과를 반환합니다.
    """
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)
    return response.json()

# 기사 본문 크롤링
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

        # 본문 추출
        content_div = soup.find('div', {'id': 'dic_area'})
        content = content_div.get_text(separator=" ").strip() if content_div else "No Content Found"

        return {
            'title': clean_text(title),
            'content': clean_text(content)
        }
    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return None

# 키워드 기반 뉴스 크롤링
def collect_relevant_news():
    """
    주어진 키워드로 네이버 뉴스 검색 및 본문 크롤링.
    """
    articles = []
    for keyword in stock_prediction_keywords_kr:
        print(f"Processing keyword: {keyword}")
        news_result = get_naver_news(keyword, start=1, display=10, sort='sim')
        for item in news_result.get('items', []):
            link = item['link']
            article_data = get_article_content(link)
            if article_data and article_data['content'] != "No Content Found":
                articles.append({
                    'keyword': keyword,
                    'title': article_data['title'],
                    'content': article_data['content']
                })

    # 중복 제거 및 저장
    unique_articles = {article['title']: article for article in articles}.values()
    with open('filtered_news.json', 'w', encoding='utf-8') as f:
        json.dump(list(unique_articles), f, ensure_ascii=False, indent=4)

    print(f"Collected {len(unique_articles)} unique articles.")

# 실행
collect_relevant_news()
