import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import socket
import ipaddress
import scraper

unique_pages = set() 
longest_page = {"url":"", "word_count":0} #url, length
word_frequencies = {} #word: count
subdomain_list = {} #subdomain: count

stop_words = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", 
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", 
    "being", "below", "between", "both", "but", "by", "can't", "cannot", 
    "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", 
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", 
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", 
    "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", 
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", 
    "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", 
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", 
    "on", "once", "only", "or", "other", "ought", "our", "oursourselves", 
    "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", 
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", 
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", 
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", 
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", 
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", 
    "what's", "when", "when's", "where", "where's", "which", "while", "who", 
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", 
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", 
    "yourselves"
}

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    print(f"Crawled: {url}")

    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    if (resp.status != 200):
        # resp.error: when status is not 200, you can check the error here, if needed.
        if(resp.error):
            print(f"Error crawling {url}: {resp.error}")
        return list()
    
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    # Check if the content is empty or too large to avoid wasting resources on processing it
    if len(resp.raw_response.content) == 0:
        print(f"Empty content for {url}")
        return list()

    # Use BeautifulSoup to extract the text from the page and split it into words. Then filter out non-alphabetic words and stop words, and convert the remaining words to lowercase.
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    text = soup.get_text().split()
    words = [word.lower() for word in text if word.isalpha() and word.lower() not in stop_words]

    # If the page has less than 100 words, we consider it not useful for our purposes and skip it to save resources.
    if len(words) < 100:
        print(f"Not enough words for {url}")
        return list()
    
    # Find links in the page and convert them to absolute URLs. We will use these links to crawl the next pages.
    extract_next_links = []

    defragmented_url = urlparse(url)._replace(fragment='').geturl()

    if defragmented_url not in unique_pages:
        unique_pages.add(defragmented_url)

        # Update longest page if necessary
        if len(words) > longest_page["word_count"]:
            longest_page["url"] = defragmented_url
            longest_page["word_count"] = len(words)

        # Update word frequencies
        for word in words:
            word_frequencies[word] = word_frequencies.get(word, 0) + 1

        if urlparse(defragmented_url).netloc.endswith("uci.edu"):
            count = subdomain_list.get(urlparse(defragmented_url).netloc, 0)
            subdomain_list[urlparse(defragmented_url).netloc] = count + 1 

    for link in soup.find_all('a', href=True):
        href = link['href']
        if scraper.is_valid(href):
            extract_next_links.append(urlparse(href)._replace(fragment='').geturl())
        
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return extract_next_links

html_doc = """<html><head><title>The Dormouse's story</title></head>
<body>
<p class="title"><b>The Dormouse's story</b></p>

<p class="story">Once upon a time there were three little sisters; and their names were
<a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
<a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
<a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
and they lived at the bottom of a well.</p>

<p class="story">...</p>
"""

class MockResp:
    def __init__(self, response):
        self.status = response.status_code
        self.raw_response = response
        
    

# Checks if the url is a valid IPv4 or IPv6 address
def checkIPAddress(address):
    try: 
        addr_info = socket.getaddrinfo(address, None, socket.AF_UNSPEC)
        for info in addr_info:
            ip_str = info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            print(ip_obj.version)     
            if ip_obj.version == 4:
                return True    
            elif ip_obj.version == 6:
                return True

        return False
    except:
        return False
    
if __name__ == "__main__":
    # soup = BeautifulSoup(html_doc, 'html.parser')
    # print(soup.prettify())
    response = requests.get("https://cnn.com")
    resp = MockResp(response)
    print(extract_next_links("https://cnn.com", resp))