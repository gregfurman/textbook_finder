import requests
import asyncio
import aiohttp
import time
import re
import difflib

from urllib.parse import urlencode, urlunparse,urlparse,parse_qs
from urllib.request import urlopen,Request
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from itertools import chain, dropwhile
from collections import Counter

class Trie(object):
    def __init__(self):
        self.child = {}
        self._pattern = re.compile('[\W_]+')

    def insert(self,title,index):
        node = self.child
        for term in title.split(" "):
            term = self._pattern.sub('', term)
            if term not in node:
                node[term] = {"id" : index}
            node = node[term]
        node['#'] = '#'


    def ratio(self,title_prefix):
        node = self.child
        for depth,term in enumerate(title_prefix.split(" ")):
            term = self._pattern.sub('', term)
            if term not in node:
                return depth/len(title_prefix),node.get("id",None)
            node = node[term]

            if '#' in node:
                return 1,node["id"]

        return 1,node["id"]

    def startsWith(self,title_prefix):
        node = self.child
        for term in title_prefix.split(" "):
            term = self._pattern.sub('', term)
            if term not in node:
                return False
            node = node[term]
        return True

    def search(self, title):
        node = self.child
        for term in title.split(" "):
            term = self._pattern.sub('', term)
            if term not in node:
                return False
            node = node[term]
        return '#' in node

class Scraper(object):

    # import Trie

    def __init__(self,language,pages):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0", 
        "Accept-Encoding":"gzip, deflate", 
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language" : "en-US,en;q=0.5",
        "Content-Type": "application/json"}

        self.language = language
        self.pages = pages
        self.titles = []
        self.trie = Trie()
        

    def main(self):
        self.get_amazon_data(self.pages,language=self.language)

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.scrape_urls())
        
        t0 = time.perf_counter()

        c=self.count_instances(response)
        t1 = time.perf_counter()
        print("TIME PASSED: ",(t1-t0))
        return c + Counter()

    def count_instances(self,scraped_headings):
        scraped_headings = filter(lambda x: len(x) > 1,scraped_headings)
        counter = Counter()

        for scraped_heading in chain.from_iterable(scraped_headings):
            # print(scraped_heading)
            ratio,index = self.trie.ratio(scraped_heading)
            if ratio > 0.8:
                counter.update({self.titles[index] : 1}) #print(scraped_heading,"|",)
            # if (heading_match:=difflib.get_close_matches(scraped_heading,self.titles,n=1,cutoff=0.9)):
                # self.titles[heading_match[0]] +=1
            else:
                continue
        return counter

    async def scrape_urls(self):        
        tasks = []
        urls = set()
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for url in self.get_search_data(pages=self.pages,query=f"best {self.language} textbooks"):
                if url not in urls and (res:=self.fetch(session,url)):
                    tasks.append(res)
                urls.add(url)

            scraped_headings = await asyncio.gather(*tasks)

        return scraped_headings


    async def fetch(self,session,url):

        try:
            async with session.get(url) as response:
                text = await response.text(encoding="utf-8")
                headers = await self.search_page(text)
                return headers
        except Exception as e:
            print(e,url)
            return []


    async def search_page(self,text):
        soup = BeautifulSoup(text,'html.parser')
        headings = soup.find_all(["h1", "h2", "h3"])
        res = set()

        if headings:
            for ele in headings:
                cleaned_ele_text = ele.text.strip().lower()
                if bool(cleaned_ele_text) and cleaned_ele_text != (len(cleaned_ele_text) * cleaned_ele_text[0]):
                    if (match := re.match(r"^(?:#?(?:[a-z]|\d+)(?:\)|\.))?(.*)$",cleaned_ele_text)):
                        res.add(match.group(1).strip())
                    else:
                        res.add(cleaned_ele_text)

        return list(res)

    
    def get_search_data(self,pages=5,query="best python textbooks"):
        next_page = "/search?"+ urlencode({"q":query})
        base_url = "https://www.google.com"

        for _ in range(pages):
            
            req = requests.get( base_url + next_page ,headers=self.headers)

            soup = BeautifulSoup(req.text,'html.parser')
            results = soup.select("a > h3")

            for elem in results:

                if 'pdf' not in elem.parent.attrs["href"].split('.')[-1]:
                    yield elem.parent.attrs["href"]

                if (next_button := soup.find('a',attrs={'id':'pnnext'})):
                    next_page = next_button["href"]
                else:
                    print("Could not find 'Next' button.")


    def get_amazon_data(self,pages=1,language="python"):

        next_page = f"s?k={language.lower().strip()}&rh=n%3A3839&ref=nb_sb_noss"#"https://www.amazon.com/Programming-Computers-Internet-Books/b?ie=UTF8&node=3839"
        base_url = "https://www.amazon.com/"

        for page in range(pages+1):
            req = requests.get( base_url + next_page ,headers=self.headers)
            content = req.text
            soup = BeautifulSoup(content,features="html.parser")
            
            for result in soup.find_all('a',attrs={'class':'a-link-normal a-text-normal'}):#('div',attrs={'class':'a-section a-spacing-none a-spacing-top-small'}):
                # if (title_html := result.find('a',attrs={'class':'a-link-normal a-text-normal'}))
                # if (title_html:=result.find('span',attrs={'class':'a-size-base-plus a-color-base a-text-normal'})): #and (authors_html:=result.find('div',attrs={'class':'a-row a-size-base a-color-secondary'})):
                # title = result.getText().lower().strip()
                # self.titles[title] = 0
                self.trie.insert(result.getText().lower().strip(),len(self.titles))
                self.titles.append(result.getText().lower().strip())

                # authors = authors_html.getText() 
                # print(title,authors.replace("\n"," "))
            if (soup_find :=soup.find('li',attrs={'class':'a-last'})) != None:
                next_page = soup_find.find('a')['href']
            else:
                print("Error in finding Amazon details.")
                break

        # print(self.titles)




s = Scraper("python",10)
# t0 = time.time()



# t1 = time.time()

# print("TIME PASSED: ",t1-t0)


for key,count in s.main().most_common():
    print(f"{key}: {count}")

