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
        addedgraph=DBpedia.download_graph(changeset.addedurl)
        deletedgraph=DBpedia.download_graph(changeset.deletedurl)
        print "*** Changesets downloaded: %s " % changeset
        return addedgraph, deletedgraph

    
    @staticmethod
    def download_graph(url):
        """download graph at given url"""
        try:
            graph = rdflib.Graph()
            url = urllib.urlopen(url)
            url_f = StringIO.StringIO(url.read())
            zipped_file = gzip.GzipFile(fileobj=url_f)
            graph.parse(zipped_file, format="nt")
            return graph
        except IOError as e:
            print ("Failed to download changeset at %s" % url.getcode())
            return False


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
        if not graph:
            return False
        result=graph.query("""SELECT DISTINCT ?subject WHERE {?subject ?b ?c}""")
        """for every subject of changeset graph try to find other triples in DBpedia live to differ between add/update/delete"""
        for subject in result:
            resource=subject[0]
            if(resource.find(DBpedia.DBPEDIAURL)==0): #apply only for resources on server with DBPEDIA URL
                live_resource=DBpedia.liveize(resource) #online version of dbpedia live have different URIs as changeset URIs
                onl_graph=rdflib.Graph()
                try:
                    onl_graph.parse(live_resource)
                    onl_iso = to_isomorphic(onl_graph)
                    loc_iso = to_isomorphic(graph)
                    in_both, in_onl, in_loc = graph_diff(onl_iso,loc_iso)
                    event_type="notupdated"
                    event=None
                    for res_of_diff, b, c in in_onl:
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
        cs=Changeset({'date' : time, 'number' : (int(csmark[14:])-1)}) # TODO: why not possible to download latest file (without -1)
        return cs
    
    @staticmethod
    def get_cs_by_url(url):
        return Changeset({'url' : url})
    
    @staticmethod
    def get_cs_by_date(date, number):
        return Changeset({  'date' : date,
                        'number' : number})

class Changeset():
    
    DBPEDIALIVE_UPDATE_URL = "http://live.dbpedia.org/liveupdates/"
    ADDED_EXTENSION = ".added.nt.gz"
    DELETED_EXTENSION = ".removed.nt.gz"
    
    def __init__(self,args):
        if('url' in args):
            self.get_by_url(args['url'])
        elif('date' in args and 'number' in args):
            self.get_by_date(args['date'], args['number'])
        else:
            raise Exception("not possible to build changeset without parameters")
    
    def __eq__(self,other):
        return self.baseurl==other.baseurl
        
    def __le__(self,other):
        if((self.date==other.date and self.number<=other.number) or self.date<other.date):
            return True
        return False
        
    def __lt__(self,other):
        if((self.date==other.date and self.number<other.number) or self.date<other.date):
            return True
        return False

    def get_by_url(self, url):
        """get changeset by url"""
        self.baseurl=url[:url.find(Changeset.ADDED_EXTENSION) + url.find(Changeset.DELETED_EXTENSION) + 1]
        url_part=url.split("/")
        pos=len(url_part)-5
        year=int(url_part[pos])
        month=int(url_part[pos+1])
        day=int(url_part[pos+2])
        hour=int(url_part[pos+3])
        self.number=int(url_part[pos+4].split(".")[0])
        self.date=datetime.datetime(year,month,day,hour)
        self.createurls()
        
    def get_by_date(self,date,number):
        """get changeset by date"""
        self.date=date
        self.number=number
        self.createurls()
    
    def increase_hour(self):
        """increase hour of changeset to be able to continue with next hour folder"""
        self.date=self.date+datetime.timedelta(hours=1)
        self.number=0
        self.createurls()

    def increase_number(self):
        """increase number to possible next changset"""
        self.number+=1
        self.createurls()
        
    def createurls(self):
        """Update URLs of changelog files"""
        self.baseurl="%s%s/%s/%s/%s/%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.date.strftime("%Y"),
            self.date.strftime("%m").zfill(2), self.date.strftime("%d").zfill(2), self.date.strftime("%H").zfill(2), str(self.number).zfill(6))
        self.addedurl="%s%s/%s/%s/%s/%s%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.date.strftime("%Y"), self.date.strftime("%m").zfill(2),
            self.date.strftime("%d").zfill(2), self.date.strftime("%H").zfill(2), str(self.number).zfill(6), Changeset.ADDED_EXTENSION)
        self.deletedurl="%s%s/%s/%s/%s/%s%s" % (Changeset.DBPEDIALIVE_UPDATE_URL, self.date.strftime("%Y"), self.date.strftime("%m").zfill(2),
            self.date.strftime("%d").zfill(2), self.date.strftime("%H").zfill(2), str(self.number).zfill(6), Changeset.DELETED_EXTENSION)

    def hasnext(self):
        url="http://live.dbpedia.org/liveupdates/lastPublishedFile.txt"
        urlhandler = urllib.urlopen(url)
        csmark=urlhandler.read()
        time=datetime.datetime.strptime(csmark[:13],"%Y-%m-%d-%H")
        cs=Changeset({'date' : time, 'number' : (int(csmark[14:])-1)}) # TODO: why not possible to download latest file (without -1)
        return (self<cs)
        
    def next(self):
        """return next changeset"""
        ncs=Changeset({'url' : self.baseurl}) # copy object
        while self.hasnext():
            """return next changeset"""
            max_fails=5
            failcounter=0
            while failcounter<=max_fails:
                ncs.increase_number()
                if (ncs.check()==200): # is cs with increased number available?
                    print "*** HTTP-Code: 200: %s" % ncs
                    return ncs
                elif(failcounter==max_fails): # max_fails with increasing number hit?
                    print "*** Could not find any more changesets in folder, increasing to next hour"
                    ncs.increase_hour()
                    failcounter=0
                    if(ncs.check()==200):
                        return ncs
                else:
                    failcounter+=1
        return False
    
    def check(self):
        """check response status of changeset """
        num_of_tries=3
        for i in range(1,num_of_tries):
            print "*** %i try to check status of %s" % (i,self.addedurl)
            try:
                urlh=urllib.urlopen(self.addedurl)
                self.status=urlh.getcode()
                if(self.status==200):
                    return self.status
                else:
                    print "Failed to load changeset %s" % self
                    return False
            except IOError as e:
                print ("### Failed to load changeset at %s -  %s" % (self.addedurl, e))
                return False

    def __str__(self):
        return self.baseurl
    
def main():
    """get next in range (cs,latest)"""
#    latest=DBpedia.get_latest_changeset()
#   cs=DBpedia.get_cs_by_url("http://live.dbpedia.org/liveupdates/2012/07/20/23/000062.added.nt.gz")
#    print cs.next(latest)
    
    """Get cs by url"""
#    print Changeset({'url' : 'http://live.dbpedia.org/liveupdates/2012/07/20/23/000062.added.nt.gz'})

    """Get latest cs"""
#   print DBpedia.get_latest_changeset() 
     
    """get cs by date"""
#   date=datetime.datetime.now()
#   print DBpedia.get_cs_by_date(date,0)
      
    """get all changesets between cs and latest"""
    cs=DBpedia.get_cs_by_url('http://live.dbpedia.org/liveupdates/2012/07/30/15/000018.added.nt.gz')
    while True:
        if(cs.hasnext()):
            cs=cs.next()
            graph=DBpedia.download_changeset(cs)
            print "Change Events of %s" % cs
            DBpedia.check_graph(graph[0],"added")
            DBpedia.check_graph(graph[1],"deleted")
        else:
            print "sleeping"
            time.sleep(10)
                    
if __name__ == '__main__':
    main()    