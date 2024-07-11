import feedparser
from bs4 import BeautifulSoup
import urllib
from dateparser import parse as parse_date
import requests
from newspaper import Article
from google.cloud import storage
import os
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
GOOGLE_CLOUD_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_BUCKET_NAME = os.getenv('GOOGLE_CLOUD_BUCKET_NAME')

# Initialize Google Cloud Storage client
storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT_ID)
bucket = storage_client.bucket(GOOGLE_CLOUD_BUCKET_NAME)

class GoogleNews:
    def __init__(self, lang='en', country='US'):
        self.lang = lang.lower()
        self.country = country.upper()
        self.BASE_URL = 'https://news.google.com/rss'

    def __top_news_parser(self, text):
        """Return subarticles from the main and topic feeds"""
        try:
            bs4_html = BeautifulSoup(text, "html.parser")
            # find all li tags
            lis = bs4_html.find_all('li')
            sub_articles = []
            for li in lis:
                try:
                    sub_articles.append({"url": li.a['href'],
                                         "title": li.a.text,
                                         "publisher": li.font.text})
                except:
                    pass
            return sub_articles
        except:
            return text

    def __ceid(self):
        """Compile correct country-lang parameters for Google News RSS URL"""
        return '?ceid={}:{}&hl={}&gl={}'.format(self.country, self.lang, self.lang, self.country)

    def __add_sub_articles(self, entries):
        for i, val in enumerate(entries):
            if 'summary' in entries[i].keys():
                entries[i]['sub_articles'] = self.__top_news_parser(entries[i]['summary'])
            else:
                entries[i]['sub_articles'] = None
        return entries

    def __scaping_bee_request(self, api_key, url):
        response = requests.get(
            url="https://app.scrapingbee.com/api/v1/",
            params={
                "api_key": api_key,
                "url": url,
                "render_js": "false"
            }
        )
        if response.status_code == 200:
            return response
        if response.status_code != 200:
            raise Exception("ScrapingBee status_code: " + str(response.status_code) + " " + response.text)

    def __parse_feed(self, feed_url, proxies=None, scraping_bee=None):
        if scraping_bee and proxies:
            raise Exception("Pick either ScrapingBee or proxies. Not both!")

        if proxies:
            r = requests.get(feed_url, proxies=proxies)
        else:
            r = requests.get(feed_url, verify=False)

        if scraping_bee:
            r = self.__scaping_bee_request(url=feed_url, api_key=scraping_bee)
        else:
            r = requests.get(feed_url, verify=False)

        if 'https://news.google.com/rss/unsupported' in r.url:
            raise Exception('This feed is not available')

        d = feedparser.parse(r.text)

        if not scraping_bee and not proxies and len(d['entries']) == 0:
            d = feedparser.parse(feed_url)

        return dict((k, d[k]) for k in ('feed', 'entries'))

    def __search_helper(self, query):
        return urllib.parse.quote_plus(query)

    def __from_to_helper(self, validate=None):
        try:
            validate = parse_date(validate).strftime('%Y-%m-%d')
            return str(validate)
        except:
            raise Exception('Could not parse your date')

    def top_news(self, proxies=None, scraping_bee=None):
        """Return a list of all articles from the main page of Google News
        given a country and a language"""
        d = self.__parse_feed(self.BASE_URL + self.__ceid(), proxies=proxies, scraping_bee=scraping_bee)
        d['entries'] = self.__add_sub_articles(d['entries'])
        return d

    def topic_headlines(self, topic: str, proxies=None, scraping_bee=None):
        """Return a list of all articles from the topic page of Google News
        given a country and a language"""
        if topic.upper() in ['WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SCIENCE', 'SPORTS', 'HEALTH']:
            d = self.__parse_feed(self.BASE_URL + '/headlines/section/topic/{}'.format(topic.upper()) + self.__ceid(), proxies=proxies, scraping_bee=scraping_bee)
        else:
            d = self.__parse_feed(self.BASE_URL + '/topics/{}'.format(topic) + self.__ceid(), proxies=proxies, scraping_bee=scraping_bee)

        d['entries'] = self.__add_sub_articles(d['entries'])
        if len(d['entries']) > 0:
            return d
        else:
            raise Exception('unsupported topic')

    def geo_headlines(self, geo: str, proxies=None, scraping_bee=None):
        """Return a list of all articles about a specific geolocation
        given a country and a language"""
        d = self.__parse_feed(self.BASE_URL + '/headlines/section/geo/{}'.format(geo) + self.__ceid(), proxies=proxies, scraping_bee=scraping_bee)

        d['entries'] = self.__add_sub_articles(d['entries'])
        return d

    def search(self, query: str, helper=True, when=None, from_=None, to_=None, proxies=None, scraping_bee=None):
        """
        Return a list of all articles given a full-text search parameter,
        a country and a language

        :param bool helper: When True helps with URL quoting
        :param str when: Sets a time range for the artiles that can be found
        """

        if when:
            query += ' when:' + when

        if from_ and not when:
            from_ = self.__from_to_helper(validate=from_)
            query += ' after:' + from_

        if to_ and not when:
            to_ = self.__from_to_helper(validate=to_)
            query += ' before:' + to_

        if helper == True:
            query = self.__search_helper(query)

        search_ceid = self.__ceid()
        search_ceid = search_ceid.replace('?', '&')

        d = self.__parse_feed(self.BASE_URL + '/search?q={}'.format(query) + search_ceid, proxies=proxies, scraping_bee=scraping_bee)

        d['entries'] = self.__add_sub_articles(d['entries'])
        return d

def get_article_content(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.text

def create_and_upload_json_file(article_data, bucket_name):
    file_name = f"{uuid.uuid4()}.json"  # Generate a UUID for the filename
    json_data = json.dumps(article_data, indent=4)
    
    with open(file_name, 'w') as json_file:
        json_file.write(json_data)

    upload_to_gcs(bucket_name, file_name, f"{file_name}")
    os.remove(file_name)  # Clean up the local file after upload

def create_and_store_json_file(article_data, folder_path):
    # Ensure the folder exists, create if it doesn't
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    file_name = f"{uuid.uuid4()}.json"  # Generate a UUID for the filename
    json_data = json.dumps(article_data, indent=4)
    
    full_file_path = os.path.join(folder_path, file_name)
    
    with open(full_file_path, 'w') as json_file:
        json_file.write(json_data)
    
    return full_file_path   

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

# Initialize GoogleNews
gn = GoogleNews()

# Search for a specific topic
search = gn.search('UEFA Euro 2024')

# Get the news items
news_items = search['entries']

# Loop through the news items and create/upload individual JSON files
for item in news_items:
    article_content = ""
    try:
        article_content = get_article_content(item['link'])
    except Exception as e:
        print(f"Failed to get content for {item['link']}: {e}")
        continue

    article_data = {
        'id': item.get('id', str(uuid.uuid4())),  # Use UUID if no ID is present
        'title': item['title'],
        'link': item['link'],
        'published': item['published'],
        'summary': item['summary'],
        'content': article_content
    }

    #create_and_upload_json_file(article_data, GOOGLE_CLOUD_BUCKET_NAME)
    create_and_store_json_file(article_data,'output')