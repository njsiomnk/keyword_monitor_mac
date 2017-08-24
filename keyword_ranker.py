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
from appleStore import AppleStore
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
    DCTableName = unicode(config.get('keywords', 'dctablename'), 'utf-8')
    DSTableName = unicode(config.get('keywords', 'dstablename'), 'utf-8')
    PagingLimit = int(config.get('keywords', 'paginglimit'))
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
    database = 'DrMacdb'
    user = 'Administrator'
    password = '111111'
    host = '10.206.132.126'
    port = '5432'

    # KeywordList = 'memory,optimize,disk,clean,clear,cache,save'.split(',')
    DCTableName = 'basicinfo_uikeywordssearchranks'
    DSTableName = 'basicinfo_uikeywordssearchranks'
    PagingLimit = 30


def getKeywords(inPath):
    """
    fetch keywords from local files
    :param inPath:
    :return:
    """
    return [line.strip('\r\n') for line in open(inPath, 'rb')]


def getAppinfo(inAppName, inCountryShortName, useproxy=False):
    """
       Try to get app detail infos through apple api
       :param inAppName: app's name
       :param inCountryShortName: country code, e.g US
       :param useproxy: whether to use proxy to get rid of GFW
       :return: Dict of app infos
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


def getAppinfoByUI(inAxGroup):
    """
    get App Infos from UI interface
    :param inAxGroup: father UI block
    :return: Dict of app infos
    """
    ret = {}

    # return structure
    baseRatings = 0
    baseScore = 0
    baseAppName = ''
    baseAppId = ''
    basePricing = 0

    if inAxGroup.AXDescription is not None or len(inAxGroup.AXDescription) > 0:
        baseAppName = inAxGroup.AXDescription

    if len(inAxGroup.findAll()) > 0 and inAxGroup.findAll()[0].AXRole == 'AXLink':
        downloadUrl = inAxGroup.findAll()[0].AXURL
        try:
            baseAppId = str(downloadUrl).split('/id')[1].split('?')[0]
        except Exception, e:
            print 'exception occurs when crawling appid'
            print e
    try:
        contentList = inAxGroup.findAll()[1]

        if contentList is not None:
            # grabbing price
            formattedPrice = contentList.findAll()[3].findAll()[0].findAll()[0].AXDescription.split(',')[-1]
            price = re.findall(r"[0-9\.]+", formattedPrice)
            if len(price) > 0:
                # Paid
                basePricing = float(price[0])

            # grabbing ratings and score
            if len(contentList.findAll()[2].AXChildren) > 0:
                # ratings
                ratingString = contentList.findAll()[2].AXChildren[0].AXDescription
                formattedRating = str(ratingString).split(',')[1]
                rating = re.findall(r"[0-9]+", formattedRating)
                if len(rating) > 0:
                    baseRatings = int(rating[0])
                # score
                formattedScore = str(ratingString).split(',')[0]
                score = re.findall(r"[0-9]+", formattedScore)

                if len(score) > 0:
                    baseScore += int(score[0])

                if formattedScore.find('a half') != -1:
                    baseScore += 0.5
    except Exception, e:
        print e
    ret['appname'] = baseAppName
    ret['appid'] = baseAppId
    ret['pricing'] = basePricing
    ret['ratings'] = baseRatings
    ret['score'] = baseScore

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

    countryPairs = getCurrencyPairs(connapp)
    KeywordList = getKeywords(DCKeywordsPath)
    countryPairs = [('United States', 'us', 'USD')]
    dateField = 'update_date'
    Feilds = 'country,keyword,rank,total_nm,app_name,app_id,pricing,currency,score,ratings,update_date'.split(',')
    storeInstance = AppleStore(ShortSleep, LongSleep, TryTime)
    automator = storeInstance.reBoot()
    today_date = datetime.now().date()
    today = datetime.now().date().strftime("%Y-%m-%d")

    try:
        for countryPair in countryPairs:
            count = 0
            for keyword in KeywordList:
                inTryTime = TryTime
                while inTryTime > 0:
                    try:
                        print 'the keyword is: {}'.format(keyword)
                        count += 1
                        _searchTextField = storeInstance.searchTextField(automator)
                        _searchTextField.AXValue = keyword
                        storeInstance.doSearch(_searchTextField)
                        resultlist = storeInstance.groupsOfSearchResults(automator, keyword)
                        if len(resultlist) == 0 or automator.AXMainWindow.findFirst(AXRole='AXGroup').findFirst(
                                AXRole='AXGroup').findFirst(
                            AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findFirst(AXRole='AXGroup') \
                                .findFirst(AXRole='AXHeading').findFirst(
                            AXRole='AXStaticText').AXValue.find(keyword) == -1:
                            print 'ranks:', -1, ' total:', len(resultlist) - 3, ' [', keyword, ']'
                        else:
                            array = []
                            print len(resultlist)
                            if resultlist[0].findFirst(AXRole='AXStaticText') is not None:
                                totalAppNumber = int(
                                    str(resultlist[0].findFirst(AXRole='AXStaticText').AXValue).split(' ')[-1])
                            else:
                                totalAppNumber = len(resultlist) - 3
                            for i in range(1, len(resultlist) - 2):
                                # print "appName: {}".format(resultlist[i].AXDescription)
                                appName = resultlist[i].AXDescription
                                # appInfo = getAppinfo(appName, countryPair[1], useproxy=True)
                                appInfo = getAppinfoByUI(resultlist[i])
                                if len(appInfo) > 0:
                                    # print 11111
                                    array.append((countryPair[0], keyword, i, totalAppNumber,
                                                  appInfo['appname'], appInfo['appid'],
                                                  appInfo['pricing'], countryPair[2], appInfo['score'],
                                                  appInfo['ratings'],
                                                  today))

                            if datumExist(connapp, DCTableName, dateField, keyword, inSpecDate=today_date):
                                deleteDatum(connapp, DCTableName, dateField, keyword, inSpecDate=today_date)
                            batchInsertToDB(connapp, DCTableName, Feilds, array)
                    except Exception, e:
                        print 'exception occurs: {}'.format(e)
                        inTryTime -= 1
                        print 'Retrying, times remain: {}'.format(inTryTime)
                        continue
                    break

                if count == 30:
                    count = 0
                    print 'up to paging limit, reboot AppStore'
                    automator = storeInstance.reBoot()

    except Exception, e:
        print e
    finally:
        print 'Apple Store Closed!'
        # storeInstance.terminateAppByName('App Store.app')
        connapp.close()
