import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv
import re
import urllib3
from gensim.models import Word2Vec
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 파일 로드
load_dotenv()

# 네이버 API 키 가져오기
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 주식 예측 관련 기본 한국어 키워드 리스트
stock_prediction_keywords_kr = [
    "주식", "증권", "투자", "경제", "주가", 
    "금융", "시장", "코스피", "코스닥", "배당", 
    "인플레이션", "금리", "성장", "채권", "분석", 
    "상장", "매도", "매수", "공매도", "IPO", "유동성", 
    "ETF", "기업", "실적", "재무", "수익률", "차트", 
    "포트폴리오", "리스크", "리밸런싱", "배당금"
]

# 불필요한 텍스트를 제거하는 전처리 함수
def clean_article_content(article_content):
    unwanted_phrases = [
        "KBS 언론사 구독 해지되었습니다", "무단 전재 및 재배포 금지", "기자의 다른 기사 보기",
        "Copyright", "모바일에서 보기", "관련 기사", "기사 공유", "기자", "입력"
    ]
    
    article_content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', article_content)
    article_content = re.sub(r'\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b', '', article_content)
    
    for phrase in unwanted_phrases:
        article_content = article_content.replace(phrase, "")
    
    article_content = re.sub(r'\n+', ' ', article_content)
    return article_content.strip()

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
def get_article_content(url):
    retry_count = 3
    for _ in range(retry_count):
        try:
            response = requests.get(url, timeout=10, verify=False)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            article_content = ' '.join([p.get_text().strip() for p in paragraphs])
            return clean_article_content(article_content)
        except requests.exceptions.RequestException as e:
            print(f"Error crawling {url}: {e}")
        except Exception as e:
            print(f"Unexpected error while crawling {url}: {e}")
    return None

# 코사인 유사도를 사용하여 주식 관련성을 판단하는 함수
def filter_by_cosine_similarity(article_content, stock_keywords):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([article_content, ' '.join(stock_keywords)])
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return similarity >= 0.2  # 기준 유사도 값 설정

# Word2Vec 모델을 이용한 주식 관련 키워드 확장
def expand_stock_keywords_with_word2vec(article_content, model):
    words = article_content.split()
    expanded_keywords = []
    
    for word in words:
        if word in model.wv:
            similar_words = [sim_word for sim_word, _ in model.wv.most_similar(word, topn=3)]
            expanded_keywords.extend(similar_words)
    
    stock_related_keywords = filter_stock_related_keywords(expanded_keywords)
    return stock_related_keywords

# 주식 관련 키워드 필터링 함수
def filter_stock_related_keywords(nouns):
    return [noun for noun in nouns if noun in stock_prediction_keywords_kr]

# Word2Vec 모델 초기화
def initialize_word2vec():
    # 임시 학습 데이터로 모델을 초기화 (사용자의 데이터로 학습 필요)
    sentences = [["주식", "투자", "금융", "시장", "성장"],
                 ["경제", "증권", "분석", "금리", "채권"]]
    model = Word2Vec(sentences, vector_size=100, window=5, min_count=1, workers=4)
    return model

# Word2Vec 모델 초기화
word2vec_model = initialize_word2vec()

# 키워드 확장 및 뉴스 수집 실행 (최대 1000개의 기사만 수집)
def collect_relevant_stock_news_kr():
    articles = set()
    total_articles_limit = 1000
    collected_articles_count = 0

    if not os.path.exists('news_copy.json'):
        with open('news_copy.json', 'w', encoding='utf-8') as f:
            json.dump([], f)

    while collected_articles_count < total_articles_limit:
        for keyword in stock_prediction_keywords_kr:
            if collected_articles_count >= total_articles_limit:
                break
            start = 1

            while collected_articles_count < total_articles_limit:
                news_result = get_naver_news(keyword, start=start, display=100, sort='sim')
                if not news_result.get('items'):
                    break

                for item in news_result.get('items', []):
                    link = item['link']
                    title = item['title']
                    description = item['description']
                    pub_date = item['pubDate']

                    if not hashlib.md5(link.encode()).hexdigest() in articles:
                        articles.add(hashlib.md5(link.encode()).hexdigest())

                        article_content = get_article_content(link)
                        if not article_content or len(article_content) < 300:
                            continue

                        expanded_keywords = expand_stock_keywords_with_word2vec(article_content, word2vec_model)
                        
                        article_data = {
                            'title': title,
                            'link': link,
                            'description': description,
                            'content': article_content,
                            'pub_date': pub_date,
                            'stock_keywords': expanded_keywords
                        }

                        with open('news_copy.json', 'r+', encoding='utf-8') as f:
                            data = json.load(f)
                            data.append(article_data)
                            f.seek(0)
                            json.dump(data, f, ensure_ascii=False, indent=4)

                        collected_articles_count += 1

                        if collected_articles_count >= total_articles_limit:
                            break
                
                start += 100

    print(f"{collected_articles_count} relevant articles collected.")

# 뉴스 수집 실행
collect_relevant_stock_news_kr()
