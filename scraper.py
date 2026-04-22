import re
from urllib.parse import urlparse

unique_pages = set() 
longest_page = {"url":"", "word_count":0} #url, length
word_frequencies = dict() #word: count
subdomain_frequencies = dict() #subdomain: count

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    print(f"Crawled: {url}")
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    if (resp.status != 200):
        return list()
    

    # resp.error: when status is not 200, you can check the error here, if needed.
    print(resp.error)
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    print(resp.raw_response.content)
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return list()

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
        print ("TypeError for ", parsed)
        raise
