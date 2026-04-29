import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

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
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", 
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

# We found that it is more efficient and effective to call is_valid before adding the links to the list. So, therefore, links only contains is_valid() links.
def scraper(url, resp):
    return extract_next_links(url, resp)
    

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
    text = soup.get_text().split()
    words = [word.lower() for word in text if word.isalpha() and word.lower() not in stop_words]

    # If the page has less than 300 words, we consider it not useful for our purposes and skip it to save resources.
    if len(words) < 300:
        print(f"Not enough words for {url}")
        return list()
    
    # Find links in the page and convert them to absolute URLs. We will use these links to crawl the next pages.
    valid_links = []

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
        absolute_url = urljoin(url, href)
        
        if is_valid(absolute_url):
            next_defragmeneted_url = urlparse(absolute_url)._replace(fragment='').geturl()
            valid_links.append(next_defragmeneted_url)
        
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return valid_links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
            

        #Check if the url is in the list of valid domains
        valid_domains = [".ics.uci.edu", ".cs.uci.edu", ".informatics.uci.edu", ".stat.uci.edu"]
        valid = False
            
        for domain in valid_domains:
            #First condition checks for subdomains, second condition checks for the domain itself
            if parsed.netloc.endswith(domain) or parsed.netloc == domain[1:]:
                valid = True
                break

        if not valid:
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
  


#Report
def generate_report():
    top_50_words = dict(sorted(word_frequencies.items(), key=lambda item: item[1], reverse=True)[:50])
    sorted_subdomains = dict(sorted(subdomain_list.items(), key=lambda item: item[0].lower()))
    
    report_text = f"There are {len(unique_pages)} unique pages\n"
    report_text += f"Longest page: {longest_page}\n\n"
    report_text += "Top 50 words:\n" + str(top_50_words) + "\n\n"
    report_text += "Subdomains:\n" + str(sorted_subdomains) + "\n"
    
    print(report_text)
    
    try:
        with open("crawler_stats.txt", "w", encoding="utf-8") as file:
            file.write(report_text)
        print("Stats successfully exported to crawler_stats.txt")
    except Exception as e:
        print(f"Could not write to file: {e}")

#Notes:
# Filter out calendar/date stuff (Done)
# Add check for to much content (does not download files that are too large) (Done)
# Error checking to ensure web crawler does not crash (Done)
# Add multi threading (Done)
# Add statistics to output such as text file (Done)
# Copy detection (check just the text with beautiful soup) 
# Specific error detection (for is valid to tell us what went wrong) 
# Refactor code functions to be simpler