#!/usr/bin/env python
# encoding: utf-8
"""
dbpedia.py: Manages simulation of changes at DBpedia via dbpedia-live 

Created by Peter Kalchgruber on 2012-07-16.
"""

import re
import os
import random
import pprint
import logging
import time
import gzip
import StringIO
import urllib
import datetime
import rdflib
from rdflib.compare import to_isomorphic, graph_diff

from apscheduler.scheduler import Scheduler
from change import ChangeEvent
from resource import Resource

class DBpedia():
    """Returns all missed changelog files"""
    RESOURCE_PATH = "/resources"
    STATIC_FILE_PATH = os.path.join(os.path.dirname(__file__), "static")
    DBDBPEDIAPEDIA_LIVE_UPDATE_URL = "http://live.dbpedia.org/liveupdates/"
    DBPEDIALIVE_URL = "http://live.dbpedia.org/resource/"
    DBPEDIAURL = "http://dbpedia.org/resource/"
    
    @staticmethod  
    def get_all(changeset):
        """get all changesets from given changeset until latest changeset"""
        cslatest=self.get_latest_changeset()
        csets=[]
        while True:
            cs=changeset.next()
            if (cs!=cslatest):
                csets.append(cs)
            else:
                break
        return csets
 
    @staticmethod  
    def download_changeset(changeset):
        """unzip changeset and compare with actual live resource"""
        print "*** Download Changeset %s " % changeset
        try:
            addedgraph=DBpedia.download_graph(changeset.addedurl)
            deletedgraph=DBpedia.download_graph(changeset.deletedurl)
            return addedgraph, deletedgraph
        except IOError as e:
            print ("Failed to load changeset at %s, HTTP return code: %s" % (changeset,url.getcode()))
            return False
    
    @staticmethod
    def download_graph(url):
        """download graph at given url"""
        graph = rdflib.Graph()
        url = urllib.urlopen(url)
        url_f = StringIO.StringIO(url.read())
        zipped_file = gzip.GzipFile(fileobj=url_f)
        graph.parse(zipped_file, format="nt")
        return graph


    @staticmethod  
    def checkforupdates(changeset):
        """Proof if new changelog file is available"""
        latest_cs=self.get_latest_changeset()
        print "*** Last online changeset: %s \n*** Last local changeset:  %s" % (latest_cs, changeset)
        if(latest_cs==changeset):
            print "*** Latest Changeset given"
            return False
        print "*** New Changeset available"
        return True
        
    @staticmethod  
    def liveize(url):
        """adds live to dbpedia url"""
        return url.replace(DBpedia.DBPEDIAURL,DBpedia.DBPEDIALIVE_URL)  
      
    @staticmethod        
    def check_graph(graph,type):
        """check if update or create by comparision with live graph"""
        result=graph.query("""SELECT DISTINCT ?subject WHERE {?subject ?b ?c}""")
        """for every subject of changeset graph try to find other triples in DBpedia live to differ between add/update/delete"""
        for subject in result:
            resource=subject[0]
            if(resource.find(DBpedia.DBPEDIAURL)==0): #apply only for resources on server with DBPEDIA URL
                live_resource=DBpedia.liveize(resource) #online version of dbpedia live have different URIs as changeset URIs
                onl_graph=rdflib.Graph()
                try:
                    onl_graph.parse(live_resource)
                    print live_resource
                    onl_iso = to_isomorphic(onl_graph)
                    loc_iso = to_isomorphic(graph)
                    in_both, in_onl, in_loc = graph_diff(onl_iso,loc_iso)
                    event_type="notupdated"
                    event=None
                    print type
                    for res_of_diff, b, c in in_onl:
                        #print "a: %s subject: %s" % (a,DBpedia.liveize(changed_resource))
                        # if live graph has more triples about resource it should be an update
                        if(str(live_resource)==str(res_of_diff)): 
                            event_type="update"
                            break;
                    if(event_type=="notupdated" and type=="added"):
                        event = ChangeEvent("CREATE", str(live_resource))
                    elif(event_type=="notupdated" and type=="deleted"):
                        event = ChangeEvent("DELETE", str(live_resource))
                    else:        
                        event = ChangeEvent("UPDATE", str(live_resource))
                    print event
                except Exception as e:
                    print "Error parsing %s" % live_resource
                #self.notify_observers(event)
    
    @staticmethod    
    def get_latest_changeset():
        """Returns latest changeset file"""
        url="http://live.dbpedia.org/liveupdates/lastPublishedFile.txt"
        urlhandler = urllib.urlopen(url)
        csmark=urlhandler.read()
        time=datetime.datetime.strptime(csmark[:13],"%Y-%m-%d-%H")
        c=Changeset(None,time,(int(csmark[14:])-1))
        return c



class Changeset():
    
    DBPEDIALIVE_UPDATE_URL = "http://live.dbpedia.org/liveupdates/"
    ADDED_EXTENSION = ".added.nt.gz"
    DELETED_EXTENSION = ".removed.nt.gz"
    
    def __init__(self,url=None, date=None, number=None):
        if(url):
            self.set_by_url(url)
        elif(date and number):
            self.set_by_date(date, number)
        else:
            raise Exception("not possible to build changeset without any information")
    
    def __eq__(self,other):
        return self.url==other.url

    def set_by_url(self, url):
        self.update_url(url)
        self.check()

    def set_by_date(self,date,number):
        self.date=date
        self.number=number
        self.update_date(date)
        self.check()
               
    def update_url(self,url):
        """update url of changeset"""
        self.baseurl=url[:url.find(Changeset.ADDED_EXTENSION) + url.find(Changeset.DELETED_EXTENSION) + 1]
        x=url.split("/")
        y=len(x)-5
        self.year=int(x[y])
        self.month=int(x[y+1])
        self.day=int(x[y+2])
        self.hour=int(x[y+3])
        self.number=int(x[y+4].split(".")[0])
        self.createurls()
    
    def update_date(self,date):
        """update date of changeset"""
        self.year=int(date.strftime("%Y"))
        self.month=int(date.strftime("%m"))
        self.day=int(date.strftime("%d"))
        self.hour=int(date.strftime("%H"))
        self.createurls()
    
    def increase_hour(self):
        """increase hour of changeset to be able to continue with next hour folder"""
        print "%s %s %s %s %s" % (self.year, self.month, self.day, self.hour, self.number)
        date=datetime.datetime(self.year,self.month,self.day,self.hour)
        date=date+datetime.timedelta(hours=1)
        self.number=0
        self.update_date(date)
        
    def createurls(self):
        """Create URL of changelog file"""
        self.baseurl="%s%s/%s/%s/%s/%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.year, str(self.month).zfill(2), str(self.day).zfill(2), str(self.hour).zfill(2), str(self.number).zfill(6))
        self.addedurl="%s%s/%s/%s/%s/%s%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.year, str(self.month).zfill(2), str(self.day).zfill(2), str(self.hour).zfill(2), str(self.number).zfill(6), Changeset.ADDED_EXTENSION)
        self.deletedurl="%s%s/%s/%s/%s/%s%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.year, str(self.month).zfill(2), str(self.day).zfill(2), str(self.hour).zfill(2), str(self.number).zfill(6), Changeset.DELETED_EXTENSION)
        
    def increase_number(self):
        """increase number to possible next changset"""
        self.number+=1
        self.createurls()
          
    def next(self):
        """return next changeset"""
        failcounter=0
        while True:
            """increase and try to catch next changesets"""
            time.sleep(1)
            if(failcounter>1):
                failcounter=0
                self.increase_hour()
            else:
                self.increase_number()
                failcounter+=1
            self.status=self.check()
            if (self.status==200):
                print "*** Changeset %s successfully loaded" % self.baseurl
                return True
    
    def check(self):
        """check response status of changeset """
        num_of_tries=3
        for i in range(1,num_of_tries):
            print "*** %i try to check status of %s" % (i,self.addedurl)
            try:
                urlh=urllib.urlopen(self.addedurl)
                print urlh.getcode()
                return urlh.getcode()
            except IOError as e:
                print ("### Failed to load changeset at %s -  %s" % (self.addedurl, e))
                return False
            time.sleep(1)

    def get_changeset(self):
        """return http-code"""
       
    
    def __str__(self):
        return self.baseurl
  
    
def main():
#    x=Changeset("http://live.dbpedia.org/liveupdates/2012/07/20/23/000060.added.nt.gz")    

    print DBpedia.get_latest_changeset()
    x=Changeset("http://live.dbpedia.org/liveupdates/2012/07/20/23/000062.added.nt.gz")
    print x
    while x.next():
        graph=DBpedia.download_changeset(x)
        print DBpedia.check_graph(graph[0],"added")
        print DBpedia.check_graph(graph[1],"deleted")
    
    
if __name__ == '__main__':
    main()    