import csv
import sys
from bs4 import BeautifulSoup
import datetime
import time
import requests
import os
from subprocess import check_output

class Request(object):
    """docstring for Request"""
    def __init__(self, url):
        super(Request, self).__init__()
        self.url = url
        self.headers = {'Content-Type': 'application/json'}

    def make(self, query=None, resource=None):
        if query:
            params = {'qt': 'worldcat_org_all'}
            params['q'] = query
            url = self.url + '/search'
        elif resource:
            url = self.url + resource
            params = None
        r = requests.get(url, params=params, headers=self.headers)#Requests allows you to send organic, grass-fed HTTP/1.1 requests
        if r.status_code == requests.codes.ok: #a property called ok in the Response object that returns True if the status code is not a  4xx or a 5xx.
            return r.text
        else:
            try:#If we made a bad request (a 4XX client error or 5XX server error response), we can raise it
                r.raise_for_status()
            except Exception, e:
                if r.status_code == 403:
                    print ("\n\n===================   Execution stopped!   ===================")
                    sys.exit(e)
            return None

class ResponseManager(object):
    def __init__(self):
        super(ResponseManager, self).__init__()

    def get_resource(self, html_doc, text_to_find):
        """This obtains:
        1. view all editions
        2. next pages
        """
        soup = BeautifulSoup(html_doc, 'html.parser')
        links = soup.find_all('a')
        resource = None
        for link in links:
            if text_to_find in link.text.lower() and not resource:
                resource = link.get('href')
        return resource

    def get_resource_titles(self, html_doc):
        """
        This method returns all resources related to titles.
        """
        soup = BeautifulSoup(html_doc, 'html.parser')
        links = soup.find_all('a')
        resources = []
        for link in links:
            href = link.get('href')#get is a dictionary method returns a value for the given key
            if href and '/title' in href and not href in resources:
                resources.append(href)
        return resources

    def get_ISBN_code(self, html_doc):
        soup = BeautifulSoup(html_doc, 'html.parser')
        tr_element = soup.find(id="details-standardno")#standardno?
        if tr_element:
            return tr_element.td.string
        else:
            return None

def get_resource_titles_all_pages(html_doc, resources, r_manager):
    #the difference with the get_resource_titles function is that this function searches in all pages.
    resource = r_manager.get_resource(html_doc, 'next')
    if resource:#if the last one
        # os.system('cls' if os.name == 'nt' else 'clear')#Execute the command (a string) in a subshell
        # print ("getting...", resource)
        html_doc = request.make(resource=resource)
        resources_tmp = r_manager.get_resource_titles(html_doc)#returns all resources related to titles
        resources += resources_tmp
        return get_resource_titles_all_pages(html_doc, resources, r_manager)
        #the recursive function here call it self, why? 
        #it is finding the related books of the already found related books, until a related book in the chain has no related ones.
    else:
        return resources

wc = int(check_output(["wc", "-l", sys.argv[1]]).split()[0]) - 1 #total entries/books
inputFile = open(sys.argv[1], 'rb')
outputFile = open(sys.argv[2], 'wb')

inputFileReader = csv.reader(inputFile)
outputFileWriter = csv.writer(outputFile, quotechar='"', quoting=csv.QUOTE_ALL)

lineCounter = 0
request = Request('https://www.worldcat.org')
r_manager = ResponseManager() #just simplifies class name
codes_not_found = []
allstorage = set()
for row in inputFileReader:
    if(lineCounter == 0):
        print("%s Start Job !" % datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    else:
        ISBN_code_digit10 = row[0]
        ISBN_code_digit13 = row[1]

        if(ISBN_code_digit10 == 10):
            ISBN_code = ISBN_code_digit10
        else: 
            ISBN_code = ISBN_code_digit13
        if (ISBN_code not in allstorage):
            html_doc = request.make(query=ISBN_code)#search this ISBN
            resource = r_manager.get_resource(html_doc, 'view all editions')#within the available related books
            if(resource): 
                tempRowStorage = []
                tempRowStorage.append(row[0])#first two cells are the 10 and 13-ISBN inputs
                tempRowStorage.append(row[1])

                digits13Storage = set()#unordered collection with no duplicate elements.
                digits10Storage = set()

                html_doc = request.make(resource=resource)
                resources = r_manager.get_resource_titles(html_doc)#get all links
                resources = get_resource_titles_all_pages(html_doc, resources, r_manager)
                for resource in resources:
                    html_doc = request.make(resource=resource)#resource has changed from that of line 125
                    if html_doc:
                        ISBN_code_related = r_manager.get_ISBN_code(html_doc)#actually we are not getting ISBNs only, 
                        if ISBN_code_related:
                            resourceQueryResult = ISBN_code_related.split(" ") #breakdown a large string, by space
                            for isbn in resourceQueryResult:
                                if(len(isbn) == 13 and isbn != ISBN_code_digit13):
                                    digits13Storage.add(isbn) #collecting all related 13-ISBN
                                    allstorage.add(isbn)
                                elif(len(isbn) == 10 and isbn != ISBN_code_digit10):
                                    digits10Storage.add(isbn)
                                    allstorage.add(isbn)
                                else:
                                    if(isbn != ISBN_code_digit10 and isbn != ISBN_code_digit13):
                                        print "What kind of crap it is? %s" % isbn

                tempRowStorage.append(",".join(str(x) for x in digits13Storage))#writes the 3rd column
                tempRowStorage.append(",".join(str(x) for x in digits10Storage))#...     ...4th...
                outputFileWriter.writerow(tempRowStorage)
            else:
                codes_not_found.append(ISBN_code)
        else:
            pass

    lineCounter += 1
    print "Appropriate Progress: %s/%s" % (lineCounter, wc) 



inputFile.close()
outputFile.close()

print "%s Job Finished!" %  datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
