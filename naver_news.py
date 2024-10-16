import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv
import re
import urllib3
from konlpy.tag import Okt  # KoNLPy의 형태소 분석기 사용

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

# Okt 형태소 분석기 인스턴스 생성
okt = Okt()

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

# 기사 본문에서 핵심 키워드를 추출하는 함수 (Okt 사용)
def extract_keywords(article_content):
    nouns = okt.nouns(article_content)  # 명사 추출
    return list(set(nouns))  # 중복 제거 후 리스트로 반환

# 키워드 확장 및 뉴스 수집 실행 (최대 1000개의 기사만 수집)
def collect_relevant_stock_news_kr():
    articles = set()  # 중복 URL 저장 방지
    news_data = []  # 수집된 뉴스 데이터를 저장할 리스트
    total_articles_limit = 1000  # 최대 1000개의 기사만 수집
    collected_articles_count = 0  # 현재 수집된 기사 수

    for keyword in stock_prediction_keywords_kr:
        if collected_articles_count >= total_articles_limit:
            break  # 1000개 초과시 수집 중단
        print(f"Collecting articles for keyword: '{keyword}'")
        start = 1

        while collected_articles_count < total_articles_limit:
            news_result = get_naver_news(keyword, start=start, display=100, sort='sim')
            if not news_result.get('items'):
                break  # 더 이상 기사가 없으면 종료

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

                    # 기사 본문에서 키워드 추출
                    extracted_keywords = extract_keywords(article_content)
                    
                    # 기사 데이터 저장
                    news_data.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'content': article_content,
                        'pub_date': pub_date,
                        'keywords': extracted_keywords  # 추출된 키워드 저장
                    })

                    collected_articles_count += 1  # 수집된 기사 수 증가

                    if collected_articles_count >= total_articles_limit:
                        break  # 1000개를 초과하면 종료
            
            start += 100  # 다음 페이지로 넘어감
    
    # 결과를 JSON 파일로 저장
    with open('collected_stock_news_kr_with_keywords.json', 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=4)

    print(f"{collected_articles_count} relevant articles collected.")

# 뉴스 수집 실행
collect_relevant_stock_news_kr()
