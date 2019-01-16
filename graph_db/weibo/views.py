# -*- coding: utf-8 -*- 
import json, datetime, random

from django.shortcuts import render, redirect
from weibo.models import UserInfo
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

try:
    from . import GstoreConnector
    from .config import mysql_conf, gStore_conf, path
except:
    import GstoreConnector
    from config import mysql_conf, gStore_conf, path


# My uid: 3023515021
gc =  GstoreConnector.GstoreConnector(gStore_conf['host'], gStore_conf['port'])


# 4条边关系
def jrelation(request):
    # uid = 2773208055

    nodes = {}
    links = set()
    tuid = request.GET.get("tuid", "")
    if tuid == "":
        return HttpResponse("")
    tuid = int(tuid)
    uid = int(request.COOKIES.get("uid"))
    
    print("jrelation called", uid)
    for i in range(1,4):
        sparql = "SELECT * WHERE { <%d> " % (uid)
        for j in range(1, i+1):
            sparql += "<foaf:knows> ?u{j} . \n ?u{j} <foaf:screen_name> ?u{j}_name . ?u{j} ".format(j=j)
        sparql += "<foaf:knows> <%d>}" % (tuid)
        print(sparql)
        resp = normalize_list(query_graph(sparql))
        for rel in resp:
            # add nodes
            for j in range(1, j+1):
                node_id = int(rel["u%d"%(j)])
                nodes[node_id] = rel["u%d_name"%(j)]
            # add rel
            links.add((
                uid,
                int(rel["u1"])
            ))
            links.add((
                int(rel["u%d"%(i)]),
                tuid
            ))
            for j in range(1, i):
                links.add((
                    int(rel["u%d" % (j)]),
                    int(rel["u%d" % (j+1)])
                ))
    # get target screen_name
    sparql = "SELECT ?name WHERE {{ <{tuid}> <foaf:screen_name> ?name }}".format(tuid=tuid)
    t_name = normalize_list(query_graph(sparql))[0]["name"]
    sparql = "SELECT ?name WHERE {{ <{uid}> <foaf:screen_name> ?name }}".format(uid=uid)
    m_name = normalize_list(query_graph(sparql))[0]["name"]
    graph = {"nodes":[], "links":[]}
    graph["nodes"].append({"name": m_name, "label":"me", "id":uid})
    graph["nodes"].append({"name": t_name, "label":"target", "id":tuid})
    for k in nodes:
        if k == uid or k == tuid:
            continue
        graph["nodes"].append({"name": nodes[k], "label":"", "id":k})
    for l in links:
        graph["links"].append({"source":l[0], "target":l[1], "type":"FOLLOWS"})
    print(len(graph["nodes"]))
    print(len(graph["links"]))
    print(json.dumps(graph))
    return HttpResponse(json.dumps(graph), content_type="application/json")


# 我的朋友
def me(request):
    uid = request.COOKIES.get("uid")

    sparql = """SELECT ?tuid ?screen_name
                WHERE {{
                    ?tuid <foaf:knows> <{uid}> .
                    ?tuid <foaf:screen_name> ?screen_name .
                }}""".format(uid=uid)
    followers = normalize_list(query_graph(sparql))

    sparql = """SELECT ?tuid ?screen_name
                WHERE {{
                    <{uid}> <foaf:knows> ?tuid .
                    ?tuid <foaf:screen_name> ?screen_name .
                }}""".format(uid=uid)
    following = normalize_list(query_graph(sparql))
    return render(request, 'weibo/me.html', {'followers': followers, 'following': following})


# 搜索用户
def search(request):

    users = dict()

    if request.method == 'GET':

        # 从链接或者cookie中获取uid
        query = request.GET.get('q')
        if query:
            me = request.COOKIES.get("uid")

            sparql = """SELECT *
                        WHERE {{ 
                            ?uid <foaf:screen_name> ?screen_name .
                            ?uid <foaf:name> ?name .
                            ?uid <foaf:location> ?location .
                            FILTER regex(?name, \"{query}\") .
                            OPTIONAL {{ 
                                ?me <foaf:knows> ?uid . 
                                FILTER ( ?me = <{me}> ) . 
                            }}
                        }}""".format(query=query,me=me)
            users = normalize_list(query_graph(sparql))

    return render(request, 'weibo/search.html', {'users': users})


# 加好友
@csrf_exempt
def follow(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name

        form = init_request(request.POST)

        sparql = """INSERT DATA {{
                        <{uid}> <foaf:knows> <{tuid}> . 
                    }}""".format(uid=request.COOKIES.get("uid"), tuid=form["tuid"])
        save = query_graph(sparql)

        if save['StatusCode']=='402':
            return HttpResponse("Followed.")


# 删除好友
@csrf_exempt
def unfollow(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = init_request(request.POST)

        sparql = """DELETE DATA {{
                        <{uid}> <foaf:knows> <{tuid}> .
                    }}""".format(uid=request.COOKIES.get("uid"), tuid=form["tuid"])
        save = query_graph(sparql)

        if save['StatusCode']=='402':
            return HttpResponse("Unfollowed.")


# 创建帖子
def create_post(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = init_request(request.POST)
        
        uid = request.COOKIES.get("uid")

        mid = random_mid()

        form['uid'] = uid
        form['mid'] = mid
        form['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "source" not in form:
            form["source"] = mid
            form["repostsnum"] = 0
            form["commentsnum"] = 0
            form["attitudesnum"] = 0
            
        #form["text"] = form["text"].encode('unicode-escape').decode('utf8').replace('\\n', '\n')
        #form["topic"] = form["topic"].encode('unicode-escape').decode('utf8').replace('\\n', '\n')
        sparql = """INSERT DATA {{
                        <{uid}> <foaf:posted> <{mid}> . 
                        <{mid}> <rdf:type> <wb:Post> .
                        <{mid}> <wb:date> \"{datetime}\" .
                        <{mid}> <wb:text> \"{text}\" .
                        <{mid}> <wb:source> \"{source}\" .
                        <{mid}> <wb:repostsnum> \"{repostsnum}\" .
                        <{mid}> <wb:commentsnum> \"{commentsnum}\" .
                        <{mid}> <wb:attitudesnum> \"{attitudesnum}\" .
                        <{mid}> <wb:topic> \"{topic}\" .
                    }}""".format(**form)

        save = query_graph(sparql)
        # 如果用户信息成功存到数据库，则跳转到用户页面，将uid和screen_name存到cookie中
        print("Create Post")
        print(save)
        if save['StatusCode']=='402':
            sparql = """ SELECT (COUNT(DISTINCT ?mid) AS ?count)
            WHERE {{ <{uid}> <foaf:posted> ?mid . }}""".format(uid=uid)
            result = normalize_list(query_graph(sparql))[0]
            print(result)
            nr_posts = int(result["count"])
            print(nr_posts)
            sparql = """ DELETE DATA {{
                        <{uid}> <foaf:statusesnum> \"{nr_posts}\"
            }}""".format(nr_posts=nr_posts-1, uid=uid)
            query_graph(sparql)
            sparql = """ INSERT DATA {{
                        <{uid}> <foaf:statusesnum> \"{nr_posts}\"
            }}""".format(nr_posts=nr_posts, uid=uid)
            query_graph(sparql)
            return HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))
        else:
            print("Unsuccess insert")
            print(save)

    return HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))

# 删除帖子
@csrf_exempt
def remove_post(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = init_request(request.POST)
        form["uid"] = request.COOKIES.get("uid")
        uid = form["uid"]
        print(form)

        sparql = """DELETE DATA {{
                        <{uid}> <foaf:posted> <{mid}> .
                        <{mid}> <wb:shared> ?tmid .
                    }}""".format(**form)
        print("Delete post")
        print(sparql)
        done = query_graph(sparql)
        if done:
            sparql = """ SELECT (COUNT(DISTINCT ?mid) AS ?count)
            WHERE {{ <{uid}> <foaf:posted> ?mid . }}""".format(uid=uid)
            try:
                result = normalize_list(query_graph(sparql))[0]
                print(result)
                nr_posts = int(result["count"])
            except:
                nr_posts = 0
            print(nr_posts)
            sparql = """ DELETE DATA {{
                        <{uid}> <foaf:statusesnum> \"{nr_posts}\"
            }}""".format(nr_posts=nr_posts+1, uid=uid)
            query_graph(sparql)
            sparql = """ INSERT DATA {{
                        <{uid}> <foaf:statusesnum> \"{nr_posts}\"
            }}""".format(nr_posts=nr_posts, uid=uid)
            query_graph(sparql)
            return HttpResponse("Successfully deleted.")

    return HttpResponse("Failed to delete.")


# 发现页面
def newsfeed(request):

    # 从链接或者cookie中获取uid
    uid = request.GET.get('uid')
    if not uid and request.COOKIES.get('uid'):
        uid = request.COOKIES.get('uid')

    # 如果链接或者cookie中没有uid，则跳转到登录页面
    if not uid:
        return HttpResponseRedirect('/weibo/login')

    # 获取用户相关的帖子数据
    post_dict = dict()
    post_dict['uid'] = uid
    post_dict['properties'] = ['date', 'text', 'source', 'repostsnum', 'commentsnum', 'attitudesnum', 'topic']
    post_dict['conditions'] = ' . '.join([ '?mid <wb:{}> ?{}'.format(p, p)  for p in post_dict['properties'] ]) + ' . '
    post_dict['share_conditions'] = ' . '.join([ '?source_mid <wb:{}> ?source_{}'.format(p, p)  for p in post_dict['properties'] ]) + ' . '

    sparql = """SELECT *
                WHERE {{ 
                        {{ 
                            ?uid <foaf:posted> ?mid . FILTER ( ?uid = <{uid}> ) . 
                        }} UNION {{ 
                            <{uid}> <foaf:knows> ?uid . 
                        }} 

                        ?uid <foaf:posted> ?mid . 
                        ?uid <foaf:screen_name> ?screen_name .
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                        OPTIONAL {{
                            ?mid <wb:shared> ?source_mid .
                            ?source_uid <foaf:posted> ?source_mid .
                            ?source_uid <foaf:screen_name> ?source_screen_name .
                            {share_conditions}
                        }}
                }} LIMIT 10""".format(**post_dict)

    posts = normalize_list(query_graph(sparql))

    return render(request, 'weibo/newsfeed.html', {'posts': posts})


# 个人主页
def profile(request):

    # 从链接或者cookie中获取uid
    is_me = False
    uid = request.GET.get('uid')
    if not uid and request.COOKIES.get('uid'):
        uid = request.COOKIES.get('uid')
        is_me = True
    elif uid == request.COOKIES.get('uid'):
        is_me = True

    # 如果链接或者cookie中没有uid，则跳转到登录页面 
    if not uid:
        return HttpResponseRedirect('/weibo/login')

    # 获取用户个人信息，存到my_profile字典中
    user_dict = dict()
    user_dict['uid'] = uid
    user_dict['properties'] = ['screen_name', 'name', 'province', 'city', 'url', 'gender', \
                                'followersnum', 'friendsnum', 'statusesnum', 'favouritesnum', 'created_at']
    user_dict['conditions'] = ' . '.join([ '<{}> <foaf:{}> ?{}'.format(uid, p, p)  for p in user_dict['properties'] ]) + ' . '
    sparql = """SELECT *
                WHERE {{
                      <{uid}> <rdf:type> <foaf:Person> .
                      OPTIONAL {{ {conditions} }}
                }}""".format(**user_dict)
    my_profile = normalize_list(query_graph(sparql))[0]
    my_profile["uid"] = uid

    try:
        sparql = """SELECT * WHERE {{ <{me}> <foaf:knows> <{uid}>  }}""".format(me=request.COOKIES.get('uid'), uid=uid)
        result = normalize_list(query_graph(sparql))[0]
        is_friend = True
    except:
        is_friend = False

    # 获取用户发布的帖子，存到my_posts字典中
    post_dict = dict()
    post_dict['uid'] = uid
    post_dict['properties'] = ['date', 'text', 'source', 'repostsnum', 'commentsnum', 'attitudesnum', 'topic']
    post_dict['conditions'] = ' . '.join([ '?mid <wb:{}> ?{}'.format(p, p)  for p in post_dict['properties'] ]) + ' . '
    post_dict['share_conditions'] = ' . '.join([ '?source_mid <wb:{}> ?source_{}'.format(p, p)  for p in post_dict['properties'] ]) + ' . '
    sparql = """SELECT *
                WHERE {{ 
                    {{
                        <{uid}> <foaf:posted> ?mid . 
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                        OPTIONAL {{
                            ?mid <wb:shared> ?source_mid .
                            ?source_uid <foaf:posted> ?source_mid .
                            ?source_uid <foaf:screen_name> ?source_screen_name .
                            {share_conditions}
                        }}
                    }} 
                }} LIMIT 10""".format(**post_dict)

    my_posts = normalize_list(query_graph(sparql))

    # 获取用户的好友信息，存到my_friends字典中
    friend_dict = dict()
    friend_dict['uid'] = uid
    friend_dict['properties'] = ['screen_name', 'name', 'province', 'city', 'location', 'url', 'gender', \
                                'followersnum', 'friendsnum', 'statusesnum', 'favouritesnum', 'created_at']
    friend_dict['conditions'] = ' . '.join([ '?tuid <foaf:{}> ?{}\n'.format(p, p)  for p in friend_dict['properties'] ]) + ' . '
    sparql = """SELECT *
                WHERE {{
                      <{uid}> <rdf:type> <foaf:Person> .
                      <{uid}> <foaf:knows> ?tuid . 
                      OPTIONAL {{ {conditions} }}
                }} LIMIT 6""".format(**friend_dict)
    my_friends = normalize_list(query_graph(sparql))

    return render(request, 'weibo/profile.html',
                  {'my_profile': my_profile, 'my_posts': my_posts, 'my_friends': my_friends, "is_me": is_me, "is_friend":is_friend})


# 注册
def register(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = init_request(request.POST)

        # 从数据库里查询输入的用户名是否已注册
        sparql = """SELECT ?uid
                    WHERE {{ 
                        ?uid <foaf:screen_name> \"{screen_name}\" . 
                    }}""".format(**form)

        # 如果输入的用户名已被其他用户注册，则返回注册页
        if query_graph(sparql):
            return render(request, 'weibo/registration.html', {'error': 'User already exist'})

        uid = random_uid()

        # 将新用户的注册信息存到数据库中
        form['uid'] = uid
        form['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sparql = """INSERT DATA {{
                      <{uid}> <rdf:type> <foaf:Person> .
                      <{uid}> <foaf:screen_name> \"{screen_name}\" .
                      <{uid}> <foaf:name> \"{name}\" .
                      <{uid}> <foaf:password> \"{password}\" .
                      <{uid}> <foaf:province> \"{province}\" .
                      <{uid}> <foaf:city> \"{city}\" .
                      <{uid}> <foaf:url> \"{url}\" .
                      <{uid}> <foaf:gender> \"{gender}\" .
                      <{uid}> <foaf:followersnum> \"0\" .
                      <{uid}> <foaf:friendsnum> \"0\" .
                      <{uid}> <foaf:statusesnum> \"0\" .
                      <{uid}> <foaf:favouritesnum> \"0\" .
                      <{uid}> <foaf:created_at> \"{datetime}\" .
                    }}""".format(**form)
        save = query_graph(sparql)

        # 如果用户信息成功存到数据库，则跳转到用户页面，将uid和screen_name存到cookie中
        if save['StatusCode']=='402':
            response = HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))
            response.set_cookie('uid', form['uid'])         
            response.set_cookie('screen_name', form['screen_name'])

            return response

    return render(request, 'weibo/registration.html')


# 登录页面
def login(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name和password
        form = init_request(request.POST)

        sparql = """SELECT ?uid
            WHERE {{ 
                ?uid <foaf:screen_name> \"{screen_name}\" .
                ?uid <foaf:password> \"{password}\" . 
            }}""".format(**form)

        # 从数据库里查询screen_name和password对应的uid
        exist = query_graph(sparql)

        # 如果存在screen_name和password对应的uid，则登录用户，将uid和screen_name存到cookie中
        if exist:
            uid = exist[0]['uid']['value']
            screen_name = form['screen_name']

            response = HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=uid))
            response.set_cookie('uid', uid)
            response.set_cookie('screen_name', screen_name)

            return response

    return render(request, 'weibo/login.html')


# 注销页面
def logout(request):

    # 跳转到登录页面
    response = HttpResponseRedirect('/weibo/login')

    # 删除用户的uid和screen_name的cookie
    if request.COOKIES.get('uid'):
        response.delete_cookie('uid')
        response.delete_cookie('screen_name')

    return response


# 辅助功能1：执行sparql语句
def query_graph(sparql):
    
    # 执行sparql语句，将返回的结果转换成json格式
    result = gc.query(gStore_conf['username'], gStore_conf['password'], gStore_conf['db'], sparql)
    result = json.loads(result)

    # 如果返回的statusCode是304，则重新加载数据库，再次执行sparql语句
    if result.get('StatusCode', '')=='304':

        ret = gc.load(gStore_conf['db'], gStore_conf['username'], gStore_conf['password'])

        result = gc.query(gStore_conf['username'], gStore_conf['password'], gStore_conf['db'], sparql)
        result = json.loads(result)

    print(result)

    if result.get('StatusCode', '')=='403':
        return result
    else:
        return result['results']['bindings'] if 'results' in result else result


# 辅助功能2：从sparql语句返回的字典中获取value值
def normalize_list(items):
    return [{k: v['value'] for k, v in item.items()} for item in items]


# 辅助功能3：从request里获取form数据
def init_request(form):
    return {k: v if v else '' for k, v in form.items()}


# 随机帖子编码
def random_mid():

    while True:
        mid = random.randint(1000000000000000, 9999999999999999)
        sparql = """SELECT *
                    WHERE {{ 
                        ?mid <rdf:type> <wb:Post> .
                        FILTER ( ?mid = <{mid}> ) .
                    }}""".format(mid=mid)
        if not query_graph(sparql):
            return mid


# 随机用户编码
def random_uid():

    while True:
        uid = random.randint(1000000000, 9999999999)
        sparql = """SELECT *
                    WHERE {{ 
                        ?uid <rdf:type> <foaf:Person> . 
                        FILTER ( ?uid = <{uid}> ) .
                    }}""".format(uid=uid)
        if not query_graph(sparql):
            return uid


def comment_post(response):
    pass


def share_post(response):
    pass


def like_post(response):
    pass
