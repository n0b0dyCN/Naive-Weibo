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


# select *
# { 
#   <2053092304>    <foaf:knows>    ?user2
# ?user2 <foaf:knows>    ?user3
# ?user3 <foaf:knows>    ?user4
# ?user4 <foaf:knows>    ?user5
# } 



# 搜索用户
def search(request):

    if request.method == 'GET':

        # 从链接或者cookie中获取uid
        query = request.GET.get('q')
        uid = request.COOKIES.get("uid")

        sparql = """SELECT *
                    WHERE {{ 
                        ?uid <foaf:name> ?name . 
                        ?uid <foaf:screen_name> ?screen_name .
                        ?uid <foaf:name> ?name .
                        ?uid <foaf:location> ?location .
                        FILTER regex(?name, \"{query}\") .

                    }}""".format(query=query, uid=uid)

        users = normalize_list(query_graph(sparql))


        sparql = """SELECT *
                    WHERE {{ 
                        <uid> <foaf:knows> ?uid2 . 
                        ?uid2 <foaf:knows> ?uid3 .
                        ?uid3 <foaf:knows> ?uid4 .
                        ?uid4 <foaf:knows> ?uid5 .
                    }}""".format(uid=uid)

        suggested_users = normalize_list(query_graph(sparql))



        return render(request, 'weibo/search.html', {'users': users})

    return render(request, 'weibo/search.html')


# 加好友
def add_friend(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}

        sparql = """INSERT DATA {{
                        <{uid}> <foaf:knows> <{tuid}> . 
                    }}""".format(**form)

        save = query_graph(sparql)

        # 如果用户信息成功存到数据库，则跳转到用户页面，将uid和screen_name存到cookie中
        if save['StatusCode']=='402':
            pass


# 删除好友
def unfriend(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}

        sparql = """DELETE DATA {{
                        <{uid}> <foaf:knows> <{tuid}> .
                    }}""".format(**form)
        done = query_graph(sparql)
        if done:
            return True

    return False
    

# 创建帖子
def create_post(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}
        
        uid = request.COOKIES.get("uid")
        mid = -1

        # 为新的用户生成10位的uid用户编码
        while True:
            mid = random.randint(1000000000000000, 9999999999999999)
            sparql = """SELECT ?mid
                        WHERE {{ 
                            ?mid <rdf:type> <wb:Post> .
                            FILTER ( ?mid = \"{mid}\" ) .
                        }}""".format(mid=mid)
            if not query_graph(sparql):
                break

        form['uid'] = uid
        form['mid'] = mid
        form['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "source" not in form:
            form["source"] = mid
            form["repostsnum"] = 0
            form["commentsnum"] = 0
            form["attitudesnum"] = 0
            
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
        if save['StatusCode']=='402':
            return HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))

    return HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))


# 删除帖子
@csrf_exempt
def remove_post(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}
        form["uid"] = request.COOKIES.get("uid")
        print(form)

        sparql = """DELETE DATA {{
                        <{uid}> <foaf:posted> <{mid}> .
                        <{mid}> <wb:shared> ?tmid .
                    }}""".format(**form)
        done = query_graph(sparql)
        if done:
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





    sparql = """SELECT *
                WHERE {{ 
                    {{
                        <{uid}> <foaf:knows> ?uid
                        ?uid <foaf:posted> ?mid . 
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                    }} UNION {{ 
                        <{uid}> <foaf:knows> ?uid
                        ?uid <foaf:posted> ?tmid . 
                        ?mid <wb:shared> ?tmid .
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                    }} UNION {{
                        <{uid}> <foaf:posted> ?mid . 
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                    }} UNION {{ 
                        <{uid}> <foaf:posted> ?tmid . 
                        ?mid <wb:shared> ?tmid .
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                    }}
                }} LIMIT 10""".format(**post_dict)
    print(sparql)
    posts = normalize_list(query_graph(sparql))

    return render(request, 'weibo/newsfeed.html', {'posts': posts})

# 个人主页
def profile(request):

    # 从链接或者cookie中获取uid
    uid = request.GET.get('uid')
    if not uid and request.COOKIES.get('uid'):
        uid = request.COOKIES.get('uid')

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
    print(sparql)
    my_profile = normalize_list(query_graph(sparql))[0]
    print(my_profile["name"])

    # 获取用户发布的帖子，存到my_posts字典中
    post_dict = dict()
    post_dict['uid'] = uid
    post_dict['properties'] = ['date', 'text', 'source', 'repostsnum', 'commentsnum', 'attitudesnum', 'topic']
    post_dict['conditions'] = ' . '.join([ '?mid <wb:{}> ?{}'.format(p, p)  for p in post_dict['properties'] ]) + ' . '
    sparql = """SELECT *
                WHERE {{ 
                    {{
                        <{uid}> <foaf:posted> ?mid . 
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
                        }}
                    }} UNION {{ 
                        <{uid}> <foaf:posted> ?tmid . 
                        ?mid <wb:shared> ?tmid .
                        ?mid <rdf:type> <wb:Post> .
                        OPTIONAL {{ 
                            {conditions} 
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

    print("My profile")
    print(my_profile)
    print("My friends")
    print(my_friends)
    return render(request, 'weibo/profile.html', {'my_profile': my_profile, 'my_posts': my_posts, 'my_friends': my_friends})

# 注册
def register(request):

    if request.method == 'POST':

        # 获取用户输入的screen_name
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}

        # 从数据库里查询输入的用户名是否已注册
        sparql = """SELECT ?uid
                    WHERE {{ 
                        ?uid <foaf:screen_name> \"{screen_name}\" . 
                    }}""".format(**form)

                # 如果输入的用户名已被其他用户注册，则返回注册页
        if query_graph(sparql):
            return render(request, 'weibo/registration.html', {'error': 'User already exist'})

        # 为新的用户生成10位的uid用户编码
        while True:
            uid = random.randint(1000000000, 9999999999)
            sparql = """SELECT ?screen_name
                        WHERE {{ 
                            \"{uid}\" <foaf:screen_name> ?screen_name . 
                        }}""".format(uid=uid)
            if not query_graph(sparql):
                break
        
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
        form = dict()
        form.update(request.POST)
        form = {k:v[0] for k, v in form.items()}

        sparql = """SELECT ?uid
            WHERE {{ 
                ?uid <foaf:screen_name> \"{screen_name}\" .
                ?uid <foaf:password> \"{password}\" . 
            }}""".format(**form)

        # 从数据库里查询screen_name和password对应的uid
        exist = query_graph(sparql)
        print(exist)

        # 如果存在screen_name和password对应的uid，则登录用户，将uid和screen_name存到cookie中
        if exist:
            uid = exist[0]['uid']['value']
            print(uid)
            response = HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=uid))
            response.set_cookie('uid', uid)

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

    if result.get('StatusCode', '')=='403':
        return result
    else:
        return result['results']['bindings'] if 'results' in result else result


# 辅助功能2：从sparql语句返回的字典中获取value值
def normalize_list(items):
    return [{k: v['value'] for k, v in item.items()} for item in items]


def comment_post(response):
    pass


def share_post(response):
    pass


def like_post(response):
    pass