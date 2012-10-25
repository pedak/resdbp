# ResourceSync DBPedia Adapter

The ResourceSync DBPedia Adapter downloads and handle DBPedia changesets


## Quick start

Make sure Python 2.7.1 is running on your system:

    python --version

Install the [Tornado](http://www.tornadoweb.org/) and [SleekXMPP](https://github.com/fritzy/SleekXMPP), [PyYAML](http://pyyaml.org/), and [APScheduler](http://packages.python.org/APScheduler/) libraries:

    sudo easy_install tornado
    sudo easy_install sleekxmpp    
    sudo easy_install PyYAML
    sudo easy_install apscheduler
    sudo easy_install rdflib
    sudo easy_install rdfextras
    
Get the ResourceSync DBPedia adapter from [Github](http://www.github.com/pedak/resdb):

    git clone git://github.com/pedak/resdbp.git
    
Run the adapter:
    
    chmod u+x resync/dbpedia
    ./dbpedia.py
