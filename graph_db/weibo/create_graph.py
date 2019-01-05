import os
from config import mysql_conf, gStore_conf, path


def create_graph():
    
    import pymysql as mdb    

    import rdflib
    from rdflib import URIRef, Literal, Namespace, Graph
    from rdflib.namespace import NamespaceManager

    con = mdb.connect(mysql_conf['host'], mysql_conf['username'], mysql_conf['password'], mysql_conf['db'])
    conn = con.cursor(mdb.cursors.DictCursor)

    g = Graph()
    namespace_manager = NamespaceManager(g)

    RDF = Namespace('rdf:')
    namespace_manager.bind('RDF', RDF, override=False)

    FOAF = Namespace('foaf:')
    namespace_manager.bind('foaf', FOAF, override=False)

    WB = Namespace('wb:')
    namespace_manager.bind('wb:', WB, override=False)


    print("Dump users")
    conn.execute("SELECT * FROM user;")
    for user in conn.fetchall():

        uid = URIRef(user['uid'])
        g.add( (uid, RDF.type, FOAF.Person) )

        for k, v in user.items():
            if k in ['uid']: continue
            g.add( (uid, FOAF[k], Literal(v)) )


    print("Dump user relations")
    conn.execute("SELECT * FROM userrelation;")
    for user_rel in conn.fetchall():

        suid = URIRef(user_rel['suid'])
        tuid = URIRef(user_rel['tuid'])
        g.add( (suid, FOAF.knows, tuid) )


    print("Dump weibo")
    conn.execute("SELECT * FROM weibo;")
    for weibo in conn.fetchall():

        uid = URIRef(weibo['uid'])
        mid = URIRef(weibo['mid'])
        g.add( (mid, RDF.type, WB.Post) )
        g.add( (uid, FOAF.posted, mid) )

        for k, v in weibo.items():
            if k in ['uid', 'mid']: continue
            g.add( (mid, WB[k], Literal(v)) )


    print("Dump weibo relations")
    conn.execute("SELECT * FROM weiborelation;")
    for weibo_rel in conn.fetchall():

        smid = URIRef(weibo_rel['smid'])
        tmid = URIRef(weibo_rel['tmid'])
        g.add( (smid, WB.shared, tmid) )

    g.serialize(destination=os.path.join(path, "data/weibo.nt"), format='nt')


def build_graph():

    import os
    from GstoreConnector import GstoreConnector

    # before you run this example, make sure that you have started up ghttp service (using bin/ghttp db_name port)
    gc =  GstoreConnector(ip=gStore_conf['host'], port=gStore_conf['port'])

    gc.drop(gStore_conf['username'], gStore_conf['password'], gStore_conf['db'])
    gc.build(gStore_conf['db'], os.path.join(path, "data/weibo.nt"), gStore_conf['username'], gStore_conf['password'])

create_graph()
build_graph()
