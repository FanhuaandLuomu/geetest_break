#coding:utf-8
# 爬取“国家企业信用信息公示系统”
# http://www.gsxt.gov.cn/corp-query-search-1.html
# geetest 行为验证码 【未解决】X 【已于2017.4.25解决】
# 暂时使用cookie爬取
from __future__ import division
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import socket
socket.setdefaulttimeout(60)

import os
import re
import time
import cPickle
import random
import requests
from lxml import etree
from geetest_break import get_validate

# 请求gt和challenge  异常或出错返回空
def get_gt_challenge(url):
	# url='http://www.gsxt.gov.cn/SearchItemCaptcha?v=1493114887662'
	headers = {
		"Accept-Language": "zh-CN,zh;q=0.8", 
		"Accept-Encoding": "gzip, deflate, sdch", 
		"X-Requested-With": "XMLHttpRequest", 
		"Host": "www.gsxt.gov.cn", 
		"Accept": "application/json, text/javascript, */*; q=0.01", 
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36", 
		"Connection": "keep-alive", 
		#"Cookie": "__jsluid=eb8523c9655107d177806597beb43f57; UM_distinctid=15b0d57141c23d-08caf973d-4349052c-1fa400-15b0d57141d940; tlb_cookie1=114ui_8280; Hm_lvt_d7682ab43891c68a00de46e9ce5b76aa=1492692994; Hm_lpvt_d7682ab43891c68a00de46e9ce5b76aa=1493024386; JSESSIONID=E7E8CC28F2EA0ABAF34E5B0B28A76730-n1:0; tlb_cookie=24query_8080; CNZZDATA1261033118=1201860774-1490573985-%7C1493103540; Hm_lvt_cdb4bc83287f8c1282df45ed61c4eac9=1490577462,1492505367; Hm_lpvt_cdb4bc83287f8c1282df45ed61c4eac9=1493104058", 
		#"Referer": "http://www.gsxt.gov.cn/corp-query-search-1.html"
	}
	try:
		res=requests.get(url,headers=headers).content
		if '"challenge"' in res and '"gt"' in res:
			gt=re.findall('"gt":"(.*?)"',res)[0]
			challenge=re.findall('"challenge":"(.*?)"',res)[0]
			return gt,challenge
		else:
			return '',''
	except Exception,e:
		return '',''

# 得到查询结果的页数 10piece/page
def get_pageNum(page):
	alist=page.xpath(u'//div[contains(@class,"search")]/span')
	if len(alist)>0:
		pageNum=alist[-1].text
		return int(pageNum)
	else:
		return 1

# 获取一页上所有查询结果的link
def get_uri(page):
	links=[]
	alist=page.xpath(u'//a[@class="search_list_item db"]')
	for item in alist:
		# print item.attrib['href']
		links.append(item.attrib['href'])
	return links

# 爬取一个公司的信息
def crawl_one_piece(s,href,headers):
	tt=1
	# 若页面未能成功加载 尝试3次
	while tt<=3:
		tt+=1
		html=s.get(href,headers=headers,timeout=60)
		time.sleep(4)

		page=etree.HTML(html.content)

		info_list=[]
		dlist=page.xpath(u'//*[@id="primaryInfo"]/div/div[@class="overview"]/dl')
		print 'len(dlist):',len(dlist)

		if len(dlist)>0:
			break
	
	for dl in dlist:
		tmp1=dl.xpath('dt/text()')
		tmp2=dl.xpath('dd/text()')

		if len(tmp1)>0 and len(tmp2)>0:

			info_list.append([''.join(tmp1).strip(),''.join(tmp2).strip()])
			# info_list.append([tmp1[0].strip(),tmp2[0].strip()])
	
	return info_list

# 规则化文件名
def regular_filename(fname):
	invalid_chars=['\\','/',':','?','？','\"','<','>','|','*']
	for c in fname:
		if c in invalid_chars:
			fname=fname.replace(c,'')
	return fname

# 对于每个关键字 按页爬取信息
def crawl_by_page(s,searchword,pageNo,challenge,validate,headers):
	global data_path

	data = {
		"searchword": searchword, 
		"geetest_challenge": challenge, 
		"token": "41111854", 
		"tab": "", 
		"geetest_seccode": validate+"|jordan", 
		"geetest_validate": validate,
		'page':str(pageNo)
	}

	href='http://www.gsxt.gov.cn/corp-query-search-%s.html' %(pageNo)
	html=s.post(href,headers=headers,data=data)
	time.sleep(2)
	html=html.content
	# print html
	page=etree.HTML(html)

	pageNum=-1  # -1 表示不是首页 未计算页数
	Num=-1
	# 爬取第一页的时候 计算下查询条数 页数
	if pageNo==1:
		Num=get_pageNum(page)
		print 'Num:',Num

		pageNum=int((Num-1)/10+1)  # 页数  10/页  1~10  11~20
		print 'pageNum:',pageNum

	# 每一页上的链接  若页面异常 则len(links)==0
	links=get_uri(page)
	print 'len(links) of page-%s:' %(pageNo),len(links)

	# 标志位 表示页面是否未加载 通过len(links)==0来判断
	# flag=1

	# 遍历 该页所有结果
	web_site='http://www.gsxt.gov.cn'
	for i,link in enumerate(links):
		try:
			print 'crawling...',link
			info_list=crawl_one_piece(s,web_site+link,headers)

			print 'len(info_list):',len(info_list)

			for item in info_list:
				print item[0],item[1]

			if len(info_list)>1:
				fname=info_list[1][1]+'(%s)' %info_list[0][1]
				fname=regular_filename(fname)
				# 1.方便可视化 保存为.txt
				f=open(data_path+os.sep+searchword+os.sep+fname+'.txt','w')
				f.write('\n'.join([' '.join(item) for item in info_list]))
				f.close()
			else:
				# 该项未能成功加载 len(info_list)==0
				f=open(data_path+os.sep+searchword+os.sep+'piece_failed.txt','a')
				f.write('%s-%s %s:%s\n' %(pageNo,i+1,web_site+link,'load failed'))
				f.close()

			# 2.提高效率 保存为cPickle文件  后期再处理为.txt文件
			# cPickle.dump(info_list,open(searchword+os.sep+fname+'.pkl','w'))

			print '%s page:%s-%s has load successed...' %(searchword,pageNo,i+1)

		except Exception,e:
			# 一项公司信息爬取错误
			f=open(data_path+os.sep+searchword+os.sep+'piece_failed.txt','a')
			f.write('%s-%s %s:%s\n' %(pageNo,i+1,web_site+link,e))
			f.close()
			print '%s page:%s-%s has load failed...' %(searchword,pageNo,i+1)
	print '%s page:%s has load success...' %(searchword,pageNo)

	# 返回pageNum 若第一页返回真实页数 否则返回-1 忽略
	return Num,pageNum,len(links)


# 按关键字爬取信息
# 验证码破解失败-1
# 关键字不可查 0
# 否则返回 1
# 页面加载异常  返回2 待重新爬取
def crawl_by_key(searchword):
	global data_path

	headers = {
		"Accept-Language": "zh-CN,zh;q=0.8",
		"Accept-Encoding": "gzip, deflate, sdch", 
		"Host": "www.gsxt.gov.cn", 
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", 
		"Upgrade-Insecure-Requests": "1", 
		"Connection": "keep-alive", 
		# "Cookie": "__jsluid=eb8523c9655107d177806597beb43f57; UM_distinctid=15b0d57141c23d-08caf973d-4349052c-1fa400-15b0d57141d940; tlb_cookie1=114ui_8280; Hm_lvt_d7682ab43891c68a00de46e9ce5b76aa=1492692994; Hm_lpvt_d7682ab43891c68a00de46e9ce5b76aa=1493116163; JSESSIONID=A4ED466AC6C5324C6F6CD02E079D70E2-n2:0; tlb_cookie=42query_8080; CNZZDATA1261033118=1201860774-1490573985-%7C1493114715; Hm_lvt_cdb4bc83287f8c1282df45ed61c4eac9=1490577462,1492505367; Hm_lpvt_cdb4bc83287f8c1282df45ed61c4eac9=1493116859", 
		#"Referer": "http://www.gsxt.gov.cn/corp-query-search-2.html?geetest_seccode=d0186455515f9c23f60ea99293ea7dd1%7Cjordan&tab=&geetest_validate=d0186455515f9c23f60ea99293ea7dd1&searchword=%E7%99%BE%E5%BA%A6&geetest_challenge=81245508634092e365977f9b6111140f5b&token=41111854&page=2", 
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36"
	}

	# 1 测试关键字是否可查
	test_url='http://www.gsxt.gov.cn/corp-query-search-test.html?searchword=%s' %searchword
	try:
		res=requests.get(test_url,headers=headers).content
		print res
		if res=='false':
			print 'searchword invaild,please input again!'
			f=open(data_path+os.sep+searchword+os.sep+'searchword_invalid.txt','a')
			f.write('%s:invalid\n' %(searchword))
			f.close()
			return 0
	except Exception,e:
		return 0

	#===========关键字可查

	url='http://www.gsxt.gov.cn/SearchItemCaptcha?v=%s' %(1493114887662+random.randint(0,10000))
	gt,challenge=get_gt_challenge(url)

	# gt,challenge请求失败 返回0
	if gt=='' or challenge=='':
		return -1

	print 'gt:',gt
	print 'challenge:',challenge

	# 请求破解验证码
	challenge,validate=get_validate(gt,challenge)

	# challenge,validate破解失败 返回0
	if validate=='' or challenge=='':
		return -1

	print 'new_challenge:',challenge
	print 'validate:',validate

	# ===============验证码破解成功

	s=requests.Session()

	# 首页
	try:
		Num,pageNum,len_links=crawl_by_page(s,searchword,1,challenge,validate,headers)
		time.sleep(2)

		f=open(data_path+os.sep+'piecesNum.txt','a')
		f.write('searchword:%s has :%s\n' %(searchword,Num))
		f.close()

	except Exception,e:
		# 首页爬取错误
		f=open(data_path+os.sep+searchword+os.sep+'page_failed.txt','a')
		f.write('%s-page:%s %s\n' %(searchword,1,e))
		f.close()
		pageNum=-1
	
	# 若首页得到的总页数>1 则继续爬取
	# 若首页爬取错误 pageNum==-1 for.. 不执行
	for i in range(2,pageNum+1):
		try:
			_,_,len_links=crawl_by_page(s,searchword,i,challenge,validate,headers)
			time.sleep(2)
		except Exception,e:
			# 页爬取错误
			f=open(data_path+os.sep+searchword+os.sep+'page_failed.txt','a')
			f.write('%s-page:%s %s\n' %(searchword,i,e))
			f.close()

	print 'key word:%s has crawled over...' %(searchword)

	# 页面加载异常  返回2 待重新爬取
	if len_links==0:
		return 2

	return 1



def main():
	global data_path
	data_path='data2'
	if not os.path.exists(data_path):
			os.mkdir(data_path)

	# searchword_list=[u'阿里',u'阿里巴巴',u'甲骨文',u'网易',u'微软',u'百度',u'爱奇艺',u'腾讯',u'优酷',u'华为',u'乐视']
	searchword_list=[u'微信']

	tmp_list=searchword_list

	run_count=0
	# 未成功爬取的关键字列表不为空  且  轮询次数<=3
	# tmp_list存放每次迭代爬取后 失败的关键字 
	# 供新的一轮继续重新爬取
	while len(tmp_list)>0 and run_count<=3:  
		run_count+=1
		searchword_list=tmp_list
		tmp_list=[]
		for searchword in searchword_list:
			try:
				# 创建文件夹 保存数据
				if not os.path.exists(data_path+os.sep+searchword):
					os.mkdir(data_path+os.sep+searchword)
				# 按关键字爬取信息
				# 验证码破解失败-1
				# 关键字不可查 0
				# 页面列表为空（未加载） 返回2
				# 否则返回 1
				tag=crawl_by_key(searchword)
				time.sleep(1)

				if tag==-1:
					print '%s captcha err.' %(searchword)
					tmp_list.append(searchword)   # 重新爬取
				if tag==0:
					print '%s key word invalid.' %(searchword)	
				if tag==1:
					print '%s not find err.' %(searchword)
				if tag==2:
					print '%s not load all...' %(searchword)
					tmp_list.append(searchword)  # 重新爬取

			except Exception,e:
				# 关键字 未知错误
				print '%s has occured err:%s' %(searchword,e)
				f=open(data_path+os.sep+searchword+os.sep+'unknown_failed.txt','a')
				f.write('%s:%s\n' %(searchword,e))
				f.close()
		time.sleep(2)
	print 'searchword_list crawled over...'

	if len(tmp_list)>0:
		f=open(data_path+os.sep+'crawled_failed.txt','a')
		f.write('\n'.join(tmp_list))
		f.close()

if __name__ == '__main__':
	main()