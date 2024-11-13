import os
import requests
from bs4 import BeautifulSoup
import json
import time
from dotenv import load_dotenv
import re

# .env 파일 로드
load_dotenv()

# 네이버 API 키
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 키워드 리스트
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
    text = re.sub(r'<.*?>', '', text)  # HTML 태그 제거
    text = re.sub(r'[^\w\s]', '', text)  # 특수문자 제거
    text = re.sub(r'\s+', ' ', text).strip()  # 여분의 공백 제거
    return text

# 네이버 뉴스 API 호출 함수
def get_naver_news(query, display=10, start=1, sort="sim"):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch news for {query}: {response.status_code}, {response.text}")
        return None

# 기사 본문 크롤링 함수
def get_article_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch article: {url}")
        return None
    
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    
    # 제목과 본문 추출
    try:
        title = soup.select_one('#title_area').get_text(strip=True)
    except:
        title = "No Title Found"
    
    try:
        content = soup.select_one('#dic_area').get_text(strip=True)
    except:
        content = "No Content Found"
    
    return {
        "title": clean_text(title),
        "content": clean_text(content)
    }

# JSON 저장 함수
def save_to_json_file(data, filename="yejin.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    # 데이터 추가
    existing_data.append(data)

    # 파일 저장
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)

# 뉴스 크롤링 및 저장
def crawl_and_save_news():
    for keyword in stock_prediction_keywords_kr:
        print(f"Processing keyword: {keyword}")
        news_data = get_naver_news(keyword)

        if not news_data or "items" not in news_data:
            print(f"No news found for keyword: {keyword}")
            continue

        for item in news_data["items"]:
            article_url = item["link"]
            article_data = get_article_content(article_url)

            if not article_data:
                continue
            
            # 저장할 데이터 구조
            news_item = {
                "keyword": keyword,
                "title": article_data["title"],
                "content": article_data["content"],
                "link": article_url,
                "pub_date": item.get("pubDate", "Unknown Date")
            }
            
            save_to_json_file(news_item)
            print(f"Saved article: {news_item['title']}")
            
            # 서버 부담 방지
            time.sleep(0.5)

# 실행
crawl_and_save_news()
