
import sys
import http.server
import socketserver
import colorama
import json
import os
import time
import hashlib
import random
import string
from urllib import parse
from colorama import init,Fore,Back,Style
from http.server import HTTPServer,BaseHTTPRequestHandler
from pathlib import Path

re_config = {
##########################
#
#	*注意,这里也同时是脚本的配置默认值,
#	*请勿删除原有项目，除非你在其他配置方式中已经配置了它
#	*例如，如果你在这里删除了'port'项目,而其他配置方式(命令行,配置文件)中都没有定义'port'项目，则脚本会出错
#
#请在这里修改配置
	'passwd':'p@sswd',
	'host':'0.0.0.0',
	'port':'1024',
	}

#如果觉得页面太丑，你也可以在这里修改awa
pages = {
	#登入页面(如果开启了passwd)
	'login':'''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>login</title>
</head>
<body>
	<form enctype="application/x-www-form-urlencoded" action="./login" method="POST">
		<input type="text" name="passwd" value="pass">
		<input type="submit" value="submit">
		<p>%%note%%</p>
	</form>
</body>
</html>
	''',
	#首页
	'index':'''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>WebFileManager</title>
</head>
<body>
	<p><b><h1>WebFileManager</h1></b></p>
	<p>%%note%%</p>
	%%file_list%%
	</br>
	<form action="./upload" method="post" enctype="multipart/form-data">
	<input type="file" name="fileUpload" multiple/>
	<input type="submit" value="上传文件" />
    </form>
</body>
</html>
	''',
	}

version = 1
version_string = 'V0.1'

def cgi_main(request):
	print('[cgi_main]--'+request.wfm_get_url()+'--'+request.wfm_get_type()+'--')
	#如果设置了密码，先校验是否登入
	if config.get('passwd') != None :
	#
		if request.wfm_get_cookie('wfm') != config.get('token') :
		#如果token不正确
			if request.wfm_get_url() == '/login' and request.wfm_get_type() == 'POST':
			#如果是POST到/login以请求校验密码的话,验证密码是否正确，如果是，则设置token
				u_passwd = request.wfm_get_payload().decode().split('=')[1]
				if u_passwd == config.get('passwd') :
					#判断到这里说明用户正确完成鉴权
					#生成随机token
					token = ''
					for i in range(27):
						token=token+random.choice(string.ascii_letters + string.digits)
					request.wfm_set_cookie('wfm',token)
					config.set('token',token)
					
				else :
					return [403,pages.get('login').replace('%%note%%','密码错误')]
			else:
			#如果不是，则返回403和登入页面
				return [403,pages.get('login').replace('%%note%%','请先登入')]
	if request.wfm_get_url() == '/upload' and request.wfm_get_type() == 'POST':
		file = request.wfm_get_upload_file()
		for file_name in file:
			if os.path.isfile('./'+file_name):
				return [200,make_index('note=文件已存在')]
			disk_file = open('./'+file_name,mode='wb')
			disk_file.write(file[file_name])
			disk_file.close()

		return [200,make_index('note=文件上传')]
	if request.wfm_get_url().startswith('/download/') :
		req_file_name = request.wfm_get_url()[10:]
		#解URL编码以支持中文文件名
		req_file_name = parse.unquote(req_file_name)
		log('提取文件<'+req_file_name+">")
		if '/' in req_file_name or '<' in req_file_name or '>' in req_file_name or '"' in req_file_name or '*' in req_file_name or ':' in req_file_name or '?' in req_file_name or '|' in req_file_name or '\\' in req_file_name :
			return [200,make_index('note=提取的文件名不合法')]
			log('提取的文件名不合法','warning')
		req_file = open('./'+req_file_name,'rb')
		request.wfm_set_payload(req_file.read())
		request.wfm_set_header('Content-Type','application/octet-stream')
		return [200,None]
	return [200,make_index()]
		
def make_index(*args):
	re = pages['index']
	args_map = {'note':'',
				'file_list':''}
	for arg in args:
		if arg.startswith('note='):
			tmp1 = arg.split('=')
			args_map['note'] = tmp1[1]
	iter = os.scandir()
	files_table = '''
<table border="1">
<tr>
<td>文件名/FileName</td>
<td>大小/Size</td>
<td>校验值/md5</td>
<td>修改日期/LastChangeTime</td>
</tr>
'''
	for file in iter:
		if not file.is_file(follow_symlinks=False):
			continue
		tmp2 = '<tr>'
		#文件名
		tmp2 = tmp2 + '<td><a href="/download/'+file.name+'">'+file.name+'</a></td>'
		tmp3 = file.stat()
		#大小
		tmp2 = tmp2 + '<td>'+str(tmp3.st_size)+'字节</td>'
#//TODO md5
		
		
		tmp2 = tmp2 + '<td>'+hashlib.md5(open('./'+file.name,'rb').read()).hexdigest()+'</td>'
		#最后更改时间
		tmp2 = tmp2 + '<td>'+time.ctime(tmp3.st_mtime)+'</td>'
		tmp2 = tmp2+'</tr>'
		files_table = files_table+tmp2
	files_table = files_table+'</table>'
	args_map['file_list'] = files_table
	for key in args_map:
		re = re.replace('%%'+key+'%%',args_map[key])
	return re

#用于向控制台输出一行日志，若开启了文件日志，则内容会一并写入指定文件中
def log(msg,level='info'):
	out = ''
	if level == 'warning':
		out = out +'\033[1;31;44m'
	elif level == 'error' :
		out = out +'\033[5;31;44m'
	else :
		pass
	out = out + '['+level+']:'+msg
	print(out)

#该类被设计为储存/处理一个配置列表
class Config:
	def __init__(self):
		self.data = {}
	def get(self,key):
		try:
			re = self.data[key]
		except:
			return
		return re
	def set(self,key,value):
		self.data[key] = value

def read_config_file(file):
	cfg = open(file)
	file_text = cfg.read()
	cfg_list = file_text.split('\n')
	for line in cfg_list :
		tmp1 = line.split('=')
		if len(tmp1) != 2 :
			log('配置文件条目<'+line+'>无法解析','warning')
			continue
		config.set(tmp1[0],tmp1[1])
	


#该函数被用于处理启动脚本时传入的参数
def initialization_args(args):
#	print(args)
	i=1
	tmp1 = 0
	while tmp1 == 0 :
		if i >= len(args) :
			break
		key = args[i]
		if key == '-v':
			log('+==========================+')
			log('Web File Manager')
			log('版本 = '+version_string)
			log('开源地址 = https://github.com/smyhw/WebFileManager')
			log('powered by smyhw OurWorld Community')
			log('+==========================+')
			break
		elif key == '-port':
			config.set('port',args[i+1])
			i=i+2
			continue
		elif key == '-host':
			config.set('host',args[i+1])
			i=i+2
			continue
		elif key == '-file_cfg' :
			read_config_file(args[i+1])
			i=i+2
			continue
		else :
			log('命令行参数<'+args[i]+'>未定义','warning')
		i=i+1

class CgiConnect(http.server.BaseHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		self.wfm_set_cookie_map = {}
		self.wfm_set_header_map = {}
		self.wfm_set_payload_data = b''
		super().__init__(*args, **kwargs)
		
	#实现get
	def do_GET(self):
		re = cgi_main(self)
		self.send_response(re[0],'')
		for key in self.wfm_set_cookie_map:
			self.send_header('Set-Cookie',key + '=' + self.wfm_set_cookie_map[key])
		for key in self.wfm_set_header_map:
			self.send_header(key,self.wfm_set_header_map[key])
		self.end_headers()
		self.wfile.write(self.wfm_set_payload_data)
		try :
			re_data = re[1].encode('utf-8')
		except:#返回空载荷时抑制报错
			re_data = ''
		self.wfile.write(re_data)
	def do_POST(self):
		re = cgi_main(self)
		self.send_response(re[0],'')
		for key in self.wfm_set_cookie_map:
			self.send_header('Set-Cookie',key + '=' + self.wfm_set_cookie_map[key])
		self.end_headers()
		self.wfile.write(self.wfm_set_payload_data)
		self.wfile.write(re[1].encode('utf-8'))
	
	#覆盖
	#隐藏head中的版本信息
	def version_string(self):
		return ''
		
	#覆盖
	#隐藏head中的时间信息
	def date_time_string(self,timestamp = None):
		return ''
		
	#覆盖
	def log_message(self, format, *args):
		log("%s - - [%s] %s\n" % (self.address_string(),self.log_date_time_string(),format%args),'http')
	
	#设置cookie
	#这会把本次请求需要设置的cookie暂存起来，在cgi_main返回后在send_header
	def wfm_set_cookie(self,key,value):
		self.wfm_set_cookie_map[key] = value
	
	#设置返回载荷(payload)
	#同理，这也会将数据暂存，在cgi_main返回后再写入到wfile里
	def wfm_set_payload(self,data):
		self.wfm_set_payload_data = self.wfm_set_payload_data+data

	#获取指定请求头项目
	def wfm_get_header(self,key):
		return self.headers[key]

	#获取指定cookie
	def wfm_get_cookie(self,key):
		tmp1 = self.wfm_get_header('Cookie')
		try:
			cookie_list = tmp1.split(';')
		except:#一般是一个cookie都没有
			return
		for tmp2 in cookie_list:
			if tmp2.split('=')[0].strip() == key :
				return tmp2.split('=')[1].strip()
		return
	
	#同理，会暂存
	def wfm_set_header(self,key,value):
		self.wfm_set_header_map[key] = value
	
	def wfm_get_args(self):
		pass

	#获取请求载荷(一般仅存在于post)
	#注意，这里获取的是字节数据，不是文本数据，请自行处理，比如.decode()解码
	def wfm_get_payload(self):
		return self.rfile.read(int(self.headers['content-length']))
	#若此次请求为post并附带文件，则返回文件数据
	#若含有多个文件则返回一个列表
	#若请求不为post或不存在文件，则返回none
	def wfm_get_upload_file(self):
		if self.wfm_get_type() != 'POST' :
			return
		re = {}
		#获取分隔符
		separator = self.wfm_get_header('Content-Type')
		separator = separator.split(';')[1]
		separator = separator.split('=')[1]
		separator = "--"+separator
#		print('separator='+separator)
		#将多份文件(如果有)解析成list
		#事实上，
		data = self.wfm_get_payload()
		#这里的".split(separator+"--".encode('utf-8'))[0]"是为了取结束符之前的内容
		data = data.split((separator+'--').encode('utf-8'))[0]
#		print('data='+str(data))
		r_files = data.split(separator.encode('utf-8'))
		#去除开始符
		r_files = r_files[1:]
		for o_file in r_files:
			#获取文件信息
			file_name = o_file.split('\r\n'.encode('utf-8'))[1]#取第一行(其实是第二行，因为有前一行那个分隔符剩下的\r\n)
			file_name = file_name.decode('utf-8')
			file_name = file_name.split(';')[2]#取filename选项
			file_name = file_name.split('=')[1]#取filename的值
			#去除引号
			file_name = file_name[1:-1]
			#寻找第一个空行并将其之前的部分截去
			file_data = o_file[o_file.find('\r\n\r\n'.encode('utf-8')):]
			#截去\r\n\r\n
			file_data = file_data[4:-2]
			re[file_name] = file_data
		return re
		
	
	#获取当前请求url
	def wfm_get_url(self):
		return self.path
		
	def wfm_get_type(self):
		return self.command

def main():
	global config
	config = Config()
	config.data = re_config
	config.set('token','abc')
	#win下解决控制台染色问题
	init(autoreset=True)
	#处理命令行附加的参数
	initialization_args(sys.argv)
	#启动http服务器
	server_address = (config.get('host'), int(config.get('port')))
	httpd = HTTPServer(server_address, CgiConnect)
	httpd.serve_forever()



if __name__ == '__main__':
	main()