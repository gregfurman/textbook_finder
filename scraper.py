
from urllib.parse import urlencode, urlunparse,urlparse,parse_qs
from urllib.request import urlopen,Request
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import asyncio
import aiohttp
import time

from itertools import chain

from collections import Counter
import re

import difflib

class Scraper(object):



    def __init__(self,language,pages):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0", 
        "Accept-Encoding":"gzip, deflate", 
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language" : "en-US,en;q=0.5"}

        self.language = language
        self.pages = pages
        self.titles = Counter()
        asyncio.get_event_loop().run_until_complete(self.scrape_urls())

    async def scrape_urls(self):
        self.get_amazon_data(self.pages,language=self.language)
        url_list = self.get_search_data(pages=self.pages,query=f"best {self.language} textbooks")
        
        tasks = []
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for url in url_list:
                if (res:=self.fetch(session,url)):
                    tasks.append(res)



            scraped_headings = await asyncio.gather(*tasks)

            scraped_headings = filter(lambda x: len(x) > 2,scraped_headings)
            for scraped_heading in chain.from_iterable(scraped_headings):
                
                

                if (heading_match:=difflib.get_close_matches(scraped_heading,self.titles,n=3,cutoff=0.9)):
                    for h in heading_match:
                        self.titles[h] += 1
                else:
                    continue

        


    async def fetch(self,session,url):

        try:
            async with session.get(url) as response:
                text = await response.text(encoding="utf-8")
                headers = await self.search_page(text)
                return headers
        except Exception as e:
            print(e)
            return []

    async def search_page(self,text):
        soup = BeautifulSoup(text,'html.parser')
        headings = soup.find_all(["h1", "h2", "h3"])
        res = []

        if headings:
            for ele in headings:
                
                if (match := re.match(r"^(?:#?(?:[a-z]|\d+)(?:\)|\.))?(.*)$",ele.text.strip().lower())):
                    res.append(match.group(0))
                else:
                    res.append(ele.text.strip().lower())

        return res

        # except Exception as e:
        #     print(e)


    
    def get_search_data(self,pages=5,query="best python textbooks"):
        urls = set()
        # try:
        options = webdriver.chrome.options.Options()
        # options.add_argument("--headless")
        options.add_argument("--disable-extensions")
        options.add_argument("disable-gpu")
        options.add_argument('window-size=1920x1080')
        driver = webdriver.Chrome(executable_path="C:\\bin\chromedriver.exe",options=options)

        url = urlunparse(("https", "www.duckduckgo.com", "/html", "", urlencode({"q":query}) , ""),)
        # print(pages,query,url)

        driver.get(url)
        
        for _ in range(pages+1):
            
            for elem in driver.find_elements_by_xpath("//a[@class='result__a']"):
                if (href:=elem.get_attribute("href")):
                    urls.add(href)

            try:
                if (next_button:=WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,"//input[@class='btn btn--alt']")))):
                    next_button.click()

            except:
                return urls


        return urls


    def get_amazon_data(self,pages=1,language="python"):

        next_page = f"s?k={language.lower().strip()}&rh=n%3A3839&ref=nb_sb_noss"#"https://www.amazon.com/Programming-Computers-Internet-Books/b?ie=UTF8&node=3839"
        base_url = "https://www.amazon.com/"
        # url = urlunparse(("https", "www.duckduckgo.com", "/html", "", urlencode({"q":query}) , ""),)


        # next_page = "s?k=python&i=stripbooks&rh=n%3A8975347011&qid=1619101033&ref=sr_pg_1"
        for page in range(pages+1):
            req = requests.get( base_url + next_page ,headers=self.headers)
            content = req.text
            soup = BeautifulSoup(content,features="html.parser")
            # print(soup.find_all('div',attrs={'class':'a-section a-spacing-none a-spacing-top-small'}))

            for result in soup.find_all('div',attrs={'class':'a-section a-spacing-none a-spacing-top-small'}):
                # if (title_html := result.find('a',attrs={'class':'a-link-normal a-text-normal'}))
                if (title_html:=result.find('span',attrs={'class':'a-size-base-plus a-color-base a-text-normal'})): #and (authors_html:=result.find('div',attrs={'class':'a-row a-size-base a-color-secondary'})):
                    title = title_html.getText().lower().strip()
                    self.titles[title] = 0
                    # authors = authors_html.getText() 
                    # print(title,authors.replace("\n"," "))
            if (soup_find :=soup.find('li',attrs={'class':'a-last'})) != None:
                next_page = soup_find.find('a')['href']
            else:
                print("Error in finding Amazon details.")
                break

        # print(self.titles)


s = Scraper("java",10)

s.titles += Counter()
print("\n")
for i,v in s.titles.items():
    print(f"{i}: {v}")




    