import requests  #use this to find current user agent
import json
import re   #allowed us to clean up some clutter
import pandas as pd
import time

from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser 
from urllib.parse import urljoin, urlparse  #parses URL and joins them
from collections import defaultdict #dict subclass that calls a factory function to supply missing values


#set debug to 1 to get some testline prints
Debug = 0

#change amount to crawl here
pagesToCrawl = 1000
    
def crawl(begin_URL, crawlMax):

    #Testline
    if Debug == 1: print(f"Currently Crawling: {begin_URL}")
    if Debug == 1: print(f"Current pages to crawl: {crawlMax}")

    urlsToCrawl = [begin_URL] #current list of pages to crawl
    urlsVisited = []  #index reference for matrix
    edges = [] #This will help us make our matrix
    siteData = {} #will hold extracted data from pages
    urlsNeededToIndex = {}  #lookup for indices


    #tempparseURL = urlparse(begin_URL).netloc  #lock it do the base


    rp = RobotFileParser() #initialize the robot file parse
    #will see if we have permits for the robots.txt

    tempparseURL = urlparse(begin_URL)  #.netloc  #lock it do the base
    #TODO this line fails and unsure why because it was working before.
    temprootURL = f"{tempparseURL.scheme}://{tempparseURL.netloc}"
    tempRobots = f"{temprootURL}/robots.txt"

    #Testline
    if Debug == 1: print(f"URL for robots text is : {tempRobots}")

    #set the robot file parser her with finished URL
    rp.set_url(tempRobots)
    userAgent = f"crawler/1.0 (contact: lyndragon@msn.com)"

    try:#try to read it. If readable then it exists
        ##rp.read()
        r = requests.get(tempRobots, headers={"User-Agent": userAgent}) #added this
        rp.parse(r.text.splitlines()) #added this
        if rp.can_fetch(userAgent, begin_URL):
            if Debug == 1:  
                print(f"We are allowed to crawl in : {begin_URL}")
        else:
            if Debug == 1: print(f"Must skip because we are not allowed : {begin_URL}")
            #must skip and not log
            return
    except Exception:
        #if no robots.txt then we can assume that it doesn't exist
        print(f"robots.txt doesn't exist {tempRobots}. Begin")
    
       
    num = 0 #used for and increase ticker to print so I can watch 

    #create a while loop to get through the appropriate num of websites
    while urlsToCrawl and len(urlsVisited) < crawlMax:

        if Debug == 1: print(f"We entered the while loop")

        currURL = urlsToCrawl.pop(0) #pop off the first element in list and assign

        #do a check to see if the currURL has been visited. If so hop
        if currURL in urlsNeededToIndex: continue
        
        #pop into and grab text from the curr URL
        try:
            if Debug == 1: print(f"We entered the try catch")
            #response = requests.get(currURL, timeout=10)
            response = requests.get(currURL, headers={"User-Agent": userAgent}, timeout=10)
            #print(f"{response}") #TESTLINE
            #print(f"{response.text}")#TESTLINE
            if "text/html" not in response.headers.get("Content-Type", ""):
                if Debug == 1: print(f"test/html not in the response.headers.get")
                continue
        except requests.RequestException:
            if Debug == 1: print(f"An exception was found in our try catch")
            continue

        if Debug == 1: print(f"We exited the try catch to get text")
        #if not visited plug it into the visited.
        
        currIndexOfVisitedURL = len(urlsVisited) #start will always be index 0 because array
        urlsVisited.append(currURL)
        urlsNeededToIndex[currURL] = currIndexOfVisitedURL

        #save the raw text. Not entire HTML but important bits according to assignment
        soup = BeautifulSoup(response.text, "html.parser")
        #remove the elements below
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.extract()
        #cleaning up viscera
        text = soup.get_text(separator = " ")
        text = re.sub(r"\s+", " ", text).strip()

        siteData[currIndexOfVisitedURL] = text

        num += 1 #personal up ticker
        print(f"{num}\n")

        if Debug == 1: print(f"NOW WE GET OUR LINKS")
        #need to get the links from our pageText
        #soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href = True):
            # if Debug == 1: print(link.get('href')) #TESTLINE
            moreCurrURL = urljoin(currURL, link["href"]).split("#")[0]
                #.split("#") breaks the sting into a list of two parts if # is seen in url
                #basically ensures we are not double dipping.

            if urlparse(moreCurrURL).netloc == tempparseURL.netloc: 
                if(moreCurrURL not in urlsNeededToIndex and moreCurrURL not in urlsToCrawl):
                    urlsToCrawl.append(moreCurrURL)

                edges.append((currURL, moreCurrURL))

        time.sleep(.75) #hopefully makes the program wait a second before jumping to next url
        #Need to makke sure does not reach 200 requests per second

    if Debug == 1: print(f"\n")
    if Debug == 1: print(f"{edges}\n\n")
    if Debug == 1: print(f"{urlsVisited}\n")

    numberOfNodes = len(urlsVisited)
    #creating a blank range at the amount needed for the nodes.
    adjacencyMatrix = [[0] * numberOfNodes for _ in range(numberOfNodes)]

    #new trick. Can make variables in for loop in python. NICE
    for originURL, childURL in edges:
        #need to make sure to only map the edges that were crawled
        if originURL in urlsNeededToIndex and childURL in urlsNeededToIndex:
            originIndex = urlsNeededToIndex[originURL]
            childIndex = urlsNeededToIndex[childURL]
            adjacencyMatrix[originIndex][childIndex] = 1   

    if Debug == 1: print(f"{adjacencyMatrix}\n")

    dataToJson = {
        "urlList": urlsVisited,
        "adjacencyMatrix": adjacencyMatrix,
        "collectedData": siteData,
    }

    """
    with open("SampleofData.json", "w", encoding = "utf-8") as f:  ##old code
        json.dump(dataToJson, f, indent = 4, ensure_ascii = False)

    """
 
    json_str = json.dumps(dataToJson, indent=4, ensure_ascii=False)

    def compact_matrix(match):
        block = match.group(0)
        return re.sub(r'\[\s*([0-9,\s]+)\s*\]', lambda m: '[' + ", ".join(re.findall(r'\d+', m.group(1))) + ']', block)

    json_str = re.sub(r'"adjacencyMatrix":\s*\[.*?\](?=\s*,\s*"|[\s\n]*})', compact_matrix, json_str, flags=re.DOTALL)

    with open("SampleofData.json", "w", encoding = "utf-8") as f:
        f.write(json_str)

    print(f"Dumped into Json\n")
    return


if __name__ == "__main__":
    #Test sites
    #URL_Start = "https://en.wikipedia.org/wiki/Cat" #testing site used
    #URL_Start = "https://www.robotstxt.org/"
    #URL_Start = "https://www.nationalgeographic.com/animals/mammals/facts/domestic-cat"
    #URL_Start = "https://www.loa.org/"S
    #URL_Start = "https://pokemon.fandom.com/wiki/Pok%C3%A9mon_Wiki"
    
    #this is our current seeded siteS
    URL_Start = "https://en.wikipedia.org/wiki/Lists_of_video_games"
    crawl(URL_Start, pagesToCrawl)