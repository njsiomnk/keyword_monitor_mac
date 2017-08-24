__author__ = 'xianyu_wang'
# -*- coding: utf-8 -*-
import atomac
import time
import re
from datetime import datetime, date, timedelta
import urllib, urllib2, smtplib, json
import psycopg2
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dbTools import *
from iTunesStore import iTunesStore
import ConfigParser
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

ConfigPath = 'config.ini'
DCKeywordsPath = 'Drcleanerwords.txt'
DSKeywordsPath = 'safetywords.txt'

try:
    # get config
    config = ConfigParser.ConfigParser()
    config.read(ConfigPath)
    ShortSleep = int(config.get('config', 'ShortSleep'))
    LongSleep = int(config.get('config', 'LongSleep'))
    TryTime = int(config.get('config', 'TryTime'))
    FilePath = unicode(config.get('config', 'OutputPath'), 'utf-8')
    EmailList = unicode(config.get('email', 'EmailList'), 'utf-8')
    CCList = unicode(config.get('email', 'CCList'), 'utf-8')
    Sender = unicode(config.get('email', 'Sender'), 'utf-8')
    database = unicode(config.get('database', 'dbName'), 'utf-8')
    user = unicode(config.get('database', 'userName'), 'utf-8')
    password = unicode(config.get('database', 'pwd'), 'utf-8')
    host = unicode(config.get('database', 'dbHost'), 'utf-8')
    port = unicode(config.get('database', 'port'), 'utf-8')
    # KeywordList = config.get('keywords', 'test_dc').split(',')
    TableName = unicode(config.get('IOSKeyword', 'tablename'), 'utf-8')
    PagingLimit = int(config.get('IOSKeyword', 'paginglimit'))
except Exception, e:
    print e
    print 'exception occurs!use default configs'
    EmailList = "xianyu_wang@trendmicro.com.cn"
    CCList = "xianyu_wang@trendmicro.com.cn"
    Sender = "Xianyu Wang"
    LongSleep = 60
    ShortSleep = 5
    TryTime = 3
    FilePath = 'currentResult.xls'
    database = ''
    user = ''
    password = ''
    host = ''
    port = ''
    # KeywordList = 'memory,optimize,disk,clean,clear,cache,save'.split(',')
    TableName = 'basicinfo_uikeywordssearchranks'
    PagingLimit = 30


def getKeywords(inConn):
    """
    fetch keywords from db
    :param inConn:
    :return:
    """
    ret = {}
    cur = inConn.cursor()

    query = """select basicinfo_country.country_name, basicinfo_country.country_code, basicinfo_country.currency, a.keyword
            from
            (select keyword, country_list
            from basicinfo_localkeywordsconfig where os = 'Ios' and is_enabled = true
            group by country_list, keyword
            order by country_list, keyword) a
            join basicinfo_country
            on a.country_list = basicinfo_country.country_code"""

    cur.execute(query)
    for country_name, country_code, currency, keyword in cur.fetchall():

        if not country_name in ret:
            ret[country_name] = []
        else:
            ret[country_name].append((country_name, country_code, currency, keyword))

    return ret


def getAppinfo(inAppName, inCountryShortName, useproxy=False):
    """
    Try to get app detail infos through apple api
    :param inAppName: app's name
    :param inCountryShortName: country code, e.g US
    :param useproxy: whether to use proxy to get rid of GFW
    :return: json Obj of app infos
    """
    ret = {}
    if useproxy:
        proxy_handler = urllib2.ProxyHandler({"http": "http://xx.xx.x.xx:xxxx"})
        opener = urllib2.build_opener(proxy_handler)
        urllib2.install_opener(opener)
    httpRequest = 'https://itunes.apple.com/{}/search?term={}&limit=100&entity=macSoftware'.format(inCountryShortName,
                                                                                                   urllib.quote(
                                                                                                       inAppName.encode(
                                                                                                           'utf-8')))
    response = urllib2.urlopen(httpRequest)
    jsonList = json.load(response)['results']
    for jsonObject in jsonList:
        if inAppName == jsonObject['trackName']:
            ret['appid'] = jsonObject['trackId']
            ret['appname'] = jsonObject['trackName']
            ret['pricing'] = jsonObject['price']
            ret['currency'] = jsonObject['currency']
            ret['score'] = jsonObject.get('averageUserRatingForCurrentVersion', 0)
            ret['ratings'] = jsonObject.get('userRatingCountForCurrentVersion', 0)
            break
    return ret


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename='keyword_ranker.log',
                        filemode='w')

    connapp = psycopg2.connect(database=database,
                               user=user,
                               password=password,
                               host=host,
                               port=port)

    KeywordList = getKeywords(connapp)
    dateField = 'update_date'
    Feilds = 'country,keyword,rank,total_nm,app_name,app_id,pricing,currency,update_date,os'.split(',')
    OS = 'Ios'
    storeInstance = iTunesStore(ShortSleep, LongSleep, TryTime)
    automator = storeInstance.reBoot()
    today_date = datetime.now().date()
    today = datetime.now().date().strftime("%Y-%m-%d")
    count = 0
    try:
        for country_name, info in KeywordList.items():
            inTryTime = TryTime

            while (not storeInstance.selectRegion(automator, country_name) == country_name) and inTryTime > 0:
                print 'country change failed! Retrying, times remain: {}'.format(inTryTime)
                inTryTime -= 1
                time.sleep(ShortSleep)

            for country_name, country_code, currency, keyword in info:
                inTryTime = TryTime
                while inTryTime > 0:
                    try:
                        print 'the keyword is: {}'.format(keyword)
                        count += 1
                        _searchTextField = storeInstance.searchTextField(automator)
                        _searchTextField.AXValue = keyword
                        storeInstance.doSearch(_searchTextField)
                        resultlist = storeInstance.groupsOfSearchResults(automator, keyword)
                        if len(resultlist) == 0 or automator.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(
                                AXRole='AXScrollArea').findFirst(
                            AXRole='AXWebArea').findFirst(AXRole='AXGroup').findFirst(
                            AXRole='AXStaticText').AXValue.find(keyword) == -1:
                            print 'ranks:', -1, ' total:', len(resultlist), ' [', keyword, ']'
                        else:
                            array = []
                            totalAppNumber = len(resultlist)
                            for rank in range(0, totalAppNumber):
                                appInfo = storeInstance.getAppinfoByUI(resultlist[rank])
                                if len(appInfo) > 0:
                                    array.append((country_name, keyword, rank + 1, totalAppNumber,
                                                  appInfo['appname'], appInfo['appid'],
                                                  appInfo['pricing'], currency,
                                                  today, OS))

                            if datumExist(connapp, TableName, dateField, keyword, inSpecDate=today_date, os=OS):
                                deleteDatum(connapp, TableName, dateField, keyword, inSpecDate=today_date, os=OS)
                            batchInsertToDB(connapp, TableName, Feilds, array)
                    except Exception, e:
                        print 'exception occurs: {}'.format(e)
                        inTryTime -= 1
                        print 'Retrying, times remain: {}'.format(inTryTime)
                        continue
                    break

    except Exception, e:
        print e
    finally:
        print 'Apple Store Closed!'
        connapp.close()
