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

# 주식 예측 관련 확장된 기본 한국어 키워드 리스트
stock_prediction_keywords_kr = [
    "주식", "증권", "투자", "경제", "주가", 
    "금융", "시장", "코스피", "코스닥", "배당", 
    "인플레이션", "금리", "성장", "채권", "분석", 
    "상장", "매도", "매수", "공매도", "IPO", "유동성", 
    "ETF", "기업", "실적", "재무", "수익률", "차트", 
    "포트폴리오", "리스크", "리밸런싱", "배당금"
]

# Okt 형태소 분석기 인스턴스 생성
okt = Okt()

# 불필요한 패턴 및 텍스트를 제거하는 전처리 함수
def clean_article_content(article_content):
    # 불필요한 문구 패턴 정의
    unwanted_phrases = [
        "KBS 언론사 구독 해지되었습니다", "무단 전재 및 재배포 금지", "기자의 다른 기사 보기",
        "Copyright", "모바일에서 보기", "관련 기사", "기사 공유", "기자", "입력"
    ]
    
    # 이메일 패턴 제거
    article_content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', article_content)
    
    # 전화번호 패턴 제거 (예: 010-1234-5678)
    article_content = re.sub(r'\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b', '', article_content)
    
    # 불필요한 문구 삭제
    for phrase in unwanted_phrases:
        article_content = article_content.replace(phrase, "")
    
    # 여러 줄로 나누어진 패턴 제거
    article_content = re.sub(r'\n+', ' ', article_content)
    
    return article_content.strip()

# 네이버 뉴스 API 호출 함수 (관련도 높은 순으로 정렬)
def get_naver_news(query, start=1, display=10, sort='sim'):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)
    return response.json()

# 기사 본문 크롤링 함수
def get_article_content(url):
    retry_count = 3  # 최대 3번 재시도
    for _ in range(retry_count):
        try:
            response = requests.get(url, timeout=10, verify=False)  # SSL 검증 건너뛰기
            response.encoding = 'utf-8'  # 인코딩을 UTF-8로 명시적으로 설정
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            article_content = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # 불필요한 문구, 이메일, 전화번호 등 제거
            return clean_article_content(article_content)
        except requests.exceptions.RequestException as e:
            print(f"Error crawling {url}: {e}")
        except Exception as e:
            print(f"Unexpected error while crawling {url}: {e}")
    return None

# 주식 관련 키워드 필터링 함수
def filter_stock_related_keywords(nouns):
    return [noun for noun in nouns if noun in stock_prediction_keywords_kr]

# 새로운 키워드 추출 및 주식 관련으로 확장하는 함수
def expand_stock_keywords(article_content):
    nouns = okt.nouns(article_content)  # 명사 추출
    unique_keywords = list(set(nouns))  # 중복 제거 후 리스트로 반환
    stock_related_keywords = filter_stock_related_keywords(unique_keywords)  # 주식 관련 키워드만 필터링
    
    return stock_related_keywords

# 키워드 확장 및 뉴스 수집 실행 (최대 1000개의 기사만 수집)
def collect_relevant_stock_news_kr():
    articles = set()  # 중복 URL 저장 방지
    total_articles_limit = 1000  # 최대 1000개의 기사만 수집
    collected_articles_count = 0  # 현재 수집된 기사 수
    
    # 실시간으로 업데이트하는 JSON 파일
    if not os.path.exists('news2.json'):
        with open('news2.json', 'w', encoding='utf-8') as f:
            json.dump([], f)  # 초기 빈 리스트로 파일 생성

    while collected_articles_count < total_articles_limit:
        for keyword in stock_prediction_keywords_kr:
            if collected_articles_count >= total_articles_limit:
                break  # 1000개 초과시 수집 중단
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

                        # 기사 본문에서 주식 관련 키워드 확장 및 새로운 키워드 추출
                        expanded_keywords = expand_stock_keywords(article_content)
                        
                        # 기사 데이터 저장
                        article_data = {
                            'title': title,
                            'link': link,
                            'description': description,
                            'content': article_content,
                            'pub_date': pub_date,
                            'stock_keywords': expanded_keywords  # 주식 관련 확장 키워드 저장
                        }

                        # 기존 데이터 불러오기
                        with open('news2.json', 'r+', encoding='utf-8') as f:
                            data = json.load(f)
                            data.append(article_data)
                            f.seek(0)
                            json.dump(data, f, ensure_ascii=False, indent=4)

                        collected_articles_count += 1  # 수집된 기사 수 증가

                        if collected_articles_count >= total_articles_limit:
                            break  # 1000개를 초과하면 종료
                
                start += 100  # 다음 페이지로 넘어감

    print(f"{collected_articles_count} relevant articles collected.")

# 뉴스 수집 실행
collect_relevant_stock_news_kr()
