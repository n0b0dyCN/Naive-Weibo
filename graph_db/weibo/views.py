import json, datetime, random

from django.shortcuts import render, redirect
from weibo.models import UserInfo
from django.http import HttpResponse, HttpResponseRedirect

try:
	from . import GstoreConnector
	from .config import mysql_conf, gStore_conf, path
except:
	import GstoreConnector
	from config import mysql_conf, gStore_conf, path


# My uid: 3023515021

gc =  GstoreConnector.GstoreConnector(gStore_conf['host'], gStore_conf['port'])


def addfriend(response):
	pass

def unfriend(response):
	pass

def create_post(response):
	pass

def remove_post(response):
	pass

def newsfeed(request):

	# Get uid from url or cookie
	uid = request.GET.get('uid')
	if not uid and request.COOKIES.get('uid'):
		uid = request.COOKIES.get('uid')

	# If no uid in url or cookie, ask user to login
	if not uid:
		return HttpResponseRedirect('/weibo/login')

	# Get user posts data
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
	posts = normalize_list(query_graph(sparql))

	return render(request, 'weibo/newsfeed.html', {'posts': posts})

def profile(request):

	# Get uid from url or cookie
	uid = request.GET.get('uid')
	if not uid and request.COOKIES.get('uid'):
		uid = request.COOKIES.get('uid')

	# If no uid in url or cookie, ask user to login
	if not uid:
		return HttpResponseRedirect('/weibo/login')

	# Get user profile data
	user_dict = dict()
	user_dict['uid'] = uid
	user_dict['properties'] = ['screen_name', 'name', 'province', 'city', 'location', 'url', 'gender', \
								'followersnum', 'friendsnum', 'statusesnum', 'favouritesnum', 'created_at']
	user_dict['conditions'] = ' . '.join([ '<{}> <foaf:{}> ?{}'.format(uid, p, p)  for p in user_dict['properties'] ]) + ' . '
	sparql = """SELECT *
				WHERE {{
					  <{uid}> <rdf:type> <foaf:Person> .
					  OPTIONAL {{ {conditions} }}
				}}""".format(**user_dict)
	my_profile = normalize_list(query_graph(sparql))

	# Get user posts data
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

	# Get user friends data
	friend_dict = dict()
	friend_dict['uid'] = uid
	friend_dict['properties'] = ['screen_name', 'name', 'province', 'city', 'location', 'url', 'gender', \
								'followersnum', 'friendsnum', 'statusesnum', 'favouritesnum', 'created_at']
	friend_dict['conditions'] = ' . '.join([ '?tuid <foaf:{}> ?{}'.format(p, p)  for p in friend_dict['properties'] ]) + ' . '
	sparql = """SELECT *
				WHERE {{
					  <{uid}> <rdf:type> <foaf:Person> .
					  <{uid}> <foaf:knows> ?tuid . 
					  OPTIONAL {{ {conditions} }}
				}} LIMIT 6""".format(**friend_dict)
	my_friends = normalize_list(query_graph(sparql))

	return render(request, 'weibo/profile.html', {'my_profile': my_profile, 'my_posts': my_posts, 'my_friends': my_friends})

def register(request):

	if request.method == 'POST':

		# Get user registration inputs: screen_name, password, etc
		form = dict()
		form.update(request.POST)
		form = {k:v[0] for k, v in form.items()}

		# Check if the user already exists
		sparql = """SELECT ?uid
					WHERE {{ 
						?uid <foaf:screen_name> \"{screen_name}\" . 
					}}""".format(**form)
		if query_graph(sparql):
			return render(request, 'weibo/registration.html', {'error': 'User already exist'})

		# Generate random 10 digit "uid" for the new user
		while True:
			uid = random.randint(1000000000, 9999999999)
			sparql = """SELECT ?screen_name
						WHERE {{ 
							\"{uid}\" <foaf:screen_name> ?screen_name . 
						}}""".format(uid=uid)
			if not query_graph(sparql):
				break
		
		# Insert new user data into the graph DB
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

		# If the user data is successfully saved, login the user
		if save['StatusCode']=='402':
			response = HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=form['uid']))
			response.set_cookie('uid', form['uid'])			
			response.set_cookie('screen_name', form['screen_name'])

			return response

	return render(request, 'weibo/registration.html')

def login(request):

	if request.method == 'POST':

		# Get user login inputs: screen_name, password
		form = dict()
		form.update(request.POST)
		form = {k:v[0] for k, v in form.items()}

		sparql = """SELECT ?uid
			WHERE {{ 
				?uid <foaf:screen_name> \"{screen_name}\" .
				?uid <foaf:password> \"{password}\" . 
			}}""".format(**form)

		exist = query_graph(sparql)

		# If the cridentials are correct, login the user
		if exist:
			uid = exist[0]['uid']['value']
			response = HttpResponseRedirect('/weibo/user?uid={uid}'.format(uid=uid))
			response.set_cookie('uid', uid)
			response.set_cookie('uid', form['screen_name'])

			return response

	return render(request, 'weibo/login.html')

def logout(request):

	response = HttpResponseRedirect('/weibo/login')

	if request.COOKIES.get('uid'):
		response.delete_cookie('uid')
		response.delete_cookie('screen_name')

	return response

def query_graph(sparql):

	result = gc.query(gStore_conf['username'], gStore_conf['password'], gStore_conf['db'], sparql)
	result = json.loads(result)

	if result.get('StatusCode', '')=='304':
		ret = gc.load(gStore_conf['db'], gStore_conf['username'], gStore_conf['password'])

		result = gc.query(gStore_conf['username'], gStore_conf['password'], gStore_conf['db'], sparql)
		result = json.loads(result)

	print(sparql, result)

	return result['results']['bindings'] if 'results' in result else result



def normalize_list(items):
	return [{k: v['value'] for k, v in item.items()} for item in items]