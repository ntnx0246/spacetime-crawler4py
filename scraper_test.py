import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests
import socket
import ipaddress
import scraper
from threading import Lock


unique_pages = set() 
longest_page = {"url":"", "word_count":0} #url, length
word_frequencies = {} #word: count
subdomain_list = {} #subdomain: count

report_lock = Lock()

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
        if(hasattr(resp, 'error') and resp.error):
            print(f"Error crawling {url}: {resp.error}")
        return list()
    
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    # Check if the resp.raw_response works and resp.response.content is not empty
    if not resp.raw_response or not resp.raw_response.content:
        print(f"Empty content for {url}")
        return list()
    
    #Check for too much content (skip it if larger than 5 MB)
    if len(resp.raw_response.content) > 5 * 1024 * 1024:
        print(f"Content too large for {url}")
        return list()
    # Use BeautifulSoup to extract the text from the page and split it into words. Then filter out non-alphabetic words and stop words, and convert the remaining words to lowercase.
    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    except Exception as e:
        print(f"Beautiful Soup crashed on {url}: {e}")
        return list()    
    text = soup.get_text()
    extracted_words = re.findall(r'[a-zA-Z]+', text)
    words = [word.lower() for word in extracted_words if word.lower() not in stop_words]
    
    # Find links in the page and convert them to absolute URLs. We will use these links to crawl the next pages.
    valid_links = []

    defragmented_url = urlparse(url)._replace(fragment='').geturl()

    with report_lock:
        if defragmented_url not in unique_pages:
            unique_pages.add(defragmented_url)

            #Skip over low text pages
            if len(words) >= 50:
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
        if not href or not isinstance(href, str):
            continue
        try:
            absolute_url = urljoin(url, str(href))
        except ValueError as e:
            print(f"Error joining URL {url} with href {href}: {e}")
            continue

        if is_valid(absolute_url):
            next_defragmeneted_url = urlparse(absolute_url)._replace(fragment='').geturl()
            valid_links.append(next_defragmeneted_url)
        
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return list(dict.fromkeys(valid_links))

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        hostname = (parsed.hostname or "").lower()
    
        if not hostname:
            return False

        #Check if the url is in the list of valid domains
        valid_domains = ("ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu")
        valid = False

        #Invalid domains
        invalid_domains = "doku.php"

        valid = any(hostname == domain or hostname.endswith(f".{domain}") for domain in valid_domains)
        if not valid:
            return False

        if invalid_domains in url:
            return False

        #Check if the path is too long to avoid infinite trap
        if len(parsed.path) > 400:
            return False
        
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()
        
        if any(x in path_lower or x in query_lower for x in ['calendar', 'event', 'ical', 'date=', 'day=', 'month=', 'year=']):
            return False
        if re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', path_lower) or re.search(r'/\d{4}/\d{2}/', path_lower):
            return False
        
        #Check for duplicate paths to avoid infinite trap
        path_segments = parsed.path.strip("/").split("/")

        #Detects whether a duplicate path exists
        if len(path_segments) != len(set(path_segments)):
            #Allow for certain duplicate paths that can happen because of chance in a valid url
            if len(path_segments) >= 5 and len(set(path_segments)) < len(path_segments) - 2:
                return False
            
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", url)
        raise
    except Exception as e:
        print(f"Something is very bad with URL validation! Error: {e}")
        return False 

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
    soup = BeautifulSoup(html_doc, 'html.parser')
    print(soup.prettify())
    response = requests.get("https://wiki.ics.uci.edu/doku.php/wiki:wiki?ns=pasted&tab_files=files&do=media")
    resp = MockResp(response)
    print(extract_next_links("https://wiki.ics.uci.edu/doku.php/wiki:wiki?ns=pasted&tab_files=files&do=media", resp))
    print(is_valid("https://wiki.ics.uci.edu/doku.php/wiki:wiki?ns=pasted&tab_files=files&do=media"))
    
    print(f'There are {len(unique_pages)} unique pages')
    print(longest_page)
    print(dict(sorted(word_frequencies.items(), key=lambda item: item[1])[:50]))
    print(dict(sorted(subdomain_list.items(), key=lambda item: item[0].lower())))
    print("wiki.ics.uci.edu/doku.php" in "https://wiki.ics.uci.edu/doku.php/wiki:wiki?ns=pasted&tab_files=files&do=media")