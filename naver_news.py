import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv
import re
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 파일 로드
load_dotenv()

# 네이버 API 키 가져오기
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 주식 예측 관련 한국어 키워드 리스트
stock_prediction_keywords_kr = [
    "주식", "증권", "투자", "경제", "주가", 
    "금융" 
]

# 네이버 뉴스 API 호출 함수 (관련도 높은 순으로 정렬)
def get_naver_news(query, start=1, display=10, sort='sim'):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)
    return response.json()

# 기사 본문 크롤링 함수 (SSL 인증서 검증을 건너뜀 및 재시도 추가)
def get_article_content(url):
    retry_count = 3  # 최대 3번 재시도
    for _ in range(retry_count):
        try:
            response = requests.get(url, timeout=10, verify=False)  # SSL 검증 건너뛰기
            response.encoding = 'utf-8'  # 인코딩을 UTF-8로 명시적으로 설정
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            article_content = ' '.join([p.get_text().strip() for p in paragraphs])
            return article_content.strip()
        except requests.exceptions.RequestException as e:
            print(f"Error crawling {url}: {e}")
        except Exception as e:
            print(f"Unexpected error while crawling {url}: {e}")
    return None

# 키워드 확장 및 뉴스 수집 실행
def collect_relevant_stock_news_kr():
    articles = set()
    news_data = []

    for keyword in stock_prediction_keywords_kr:
        print(f"Collecting articles for keyword: '{keyword}'")
        news_result = get_naver_news(keyword, start=1, display=100, sort='sim')

        for item in news_result.get('items', []):
            link = item['link']
            title = item['title']
            description = item['description']
            pub_date = item['pubDate']

            if not hashlib.md5(link.encode()).hexdigest() in articles:
                articles.add(hashlib.md5(link.encode()).hexdigest())

                # 기사 본문 크롤링
                article_content = get_article_content(link)
                if not article_content or len(article_content) < 300:  # 본문이 너무 짧은 기사 제외
                    continue
                
                # 기사 데이터 저장
                news_data.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'content': article_content,
                    'pub_date': pub_date
                })
    
    # 결과를 JSON 파일로 저장
    with open('collected_stock_news_kr.json', 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=4)

    print(f"{len(news_data)} relevant articles collected.")

# 뉴스 수집 실행
collect_relevant_stock_news_kr()
