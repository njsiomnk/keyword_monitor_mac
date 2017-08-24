# -*- coding: utf-8 -*-
import os

import atomac
import time
import re
import os
import sys
import datetime

reload(sys)
sys.setdefaultencoding('utf-8')


class iTunesStore:
    bundle_name = 'com.apple.iTunes'
    process_name = 'iTunes'

    def __init__(self, shortSleepTime, longSleepTime, tryTime):
        self.shortSleepTime = shortSleepTime
        self.longSleepTime = longSleepTime
        self.tryTime = tryTime

    def initialStore(self):
        print "initialing iTunesStore"
        atomac.launchAppByBundleId(self.bundle_name)
        pattern = re.compile(u'No role')
        trytime = self.tryTime

        while pattern.search(str(atomac.getAppRefByBundleId(self.bundle_name))):
            print "step 1 sleep 5 sec..."
            time.sleep(self.shortSleepTime)

        appStoreRef = atomac.getAppRefByBundleId(self.bundle_name)
        # print appStoreRef
        pattern = re.compile('None')

        # print appStoreRef.AXMainWindow.AXFrame
        while trytime > 0 and (pattern.search(str(appStoreRef.AXMainWindow)) or
                                   pattern.search(str(appStoreRef.AXMainWindow)) or pattern.search(
            str(appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findAll())) or len(
            appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findAll()) == 0):
            print "network excetion!try again in {}s, try_time remain {} times".format(self.shortSleepTime,
                                                                                       trytime)
            time.sleep(self.shortSleepTime)
            trytime -= 1

        return appStoreRef

    def selectRegion(self, appStoreRef, countryName):
        axGroupList = appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(AXRole='AXScrollArea') \
            .findFirst(AXRole='AXWebArea').findAll(AXRole='AXGroup')[-1].findAll(AXRole='AXGroup')
        targetLink = axGroupList[-1].findFirst(AXRole='AXLink')
        targetLink.Press()
        # .findFirst(AXRole='AXWebArea').findFirst(AXRole='AXGroup').findFirstR(AXRole='AXGroup')
        print 'Switching country/region to: {}'.format(countryName)
        time.sleep(self.longSleepTime)

        inTryTime = self.tryTime

        while (appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(
                AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findFirst(
            AXRole='AXHeading') is None or appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(
            AXRole="AXScrollArea").findFirst(AXRole='AXWebArea').findFirst(
            AXRole='AXHeading').findFirst(
            AXRole='AXStaticText').AXValue != 'Choose your country or region') and inTryTime > 0:
            print 'page still loading! please wait for a minute'
            time.sleep(self.shortSleepTime)
            inTryTime -= 1

        AllcountryList = appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(
            AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findAll(AXRole='AXGroup')

        for regionGroup in AllcountryList:
            countryList = regionGroup.findAll(AXRole='AXGroup')
            for countryItem in countryList:
                if countryItem.findAll(AXRole='AXGroup')[1].staticTexts()[0].AXValue == countryName:
                    print "find target link of country: {}".format(countryName)
                    countryItem.findAll(AXRole='AXGroup')[1].staticTexts()[0].Press()

                    inTryTime = self.tryTime
                    pattern_None = re.compile('None')

                    time.sleep(self.shortSleepTime)

                    pattern_noRole = re.compile(u'No role')

                    axGroupListAfter = \
                        appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup').findFirst(AXRole='AXScrollArea') \
                            .findFirst(AXRole='AXWebArea').findAll(AXRole='AXGroup')[-1].findAll(AXRole='AXGroup')

                    resultText = axGroupListAfter[-1].findFirst(AXRole='AXLink').findFirst(
                        AXRole='AXImage').AXDescription

                    resultCountry = resultText.split(',')[0].split(':')[1].strip()

                    print 'country after changing is: {}'.format(resultCountry)

                    return resultCountry

    def searchTextField(self, appStoreRef):
        time.sleep(self.shortSleepTime)
        _searchTextField = appStoreRef.AXMainWindow.findFirst(AXRole='AXTextField')
        while not _searchTextField.AXEnabled:
            time.sleep(self.shortSleepTime)
            _searchTextField = appStoreRef.AXMainWindow.findFirst(AXRole='AXTextField')
        return _searchTextField

    def doSearch(self, searchField):
        x, y = searchField.AXPosition
        width, height = searchField.AXSize
        print 'the position of search text is : {}'.format((x + width / 2, y + height / 2))
        time.sleep(self.shortSleepTime)
        searchField.doubleClickMouse((x + width / 2, y + height / 2))
        time.sleep(self.shortSleepTime)
        searchField.sendKey('<cursor_right>')
        searchField.sendKey('<space>')
        searchField.sendKey('<backspace>')
        searchField.sendKey('\r')
        time.sleep(self.shortSleepTime)

    def groupsOfSearchResults(self, appStoreRef, keyword):
        window = appStoreRef.AXMainWindow
        inTryTime = self.tryTime

        # print pattern.search(str(appStoreRef.AXMainWindow.findFirst(AXRole='AXSplitGroup')))
        while (window.findFirst(AXRole='AXSplitGroup').findFirst(AXRole='AXScrollArea').findFirst(
                AXRole='AXWebArea').findFirst(
            AXRole='AXGroup').findFirst(AXRole='AXStaticText').AXValue.find(keyword) == -1) and inTryTime > 0:
            print 'page still loading'
            time.sleep(self.shortSleepTime)
            inTryTime -= 1
        chooseIphoneApps(appStoreRef)
        time.sleep(self.shortSleepTime)
        results = \
            window.findFirst(AXRole='AXSplitGroup').findFirst(AXRole='AXScrollArea').findFirst(
                AXRole='AXWebArea').findAll(
                AXRole='AXGroup')[1].findAll()
        return results

    def reBoot(self):
        self.terminateAppByName(self.process_name)
        time.sleep(self.shortSleepTime)
        result = self.initialStore()
        return result

    def getAppinfoByUI(self, inAxGroup):
        ret = {}

        # return structure
        baseRatings = 0
        baseScore = 0
        baseAppName = ''
        baseAppId = ''
        basePricing = 0

        appinfoGroup1 = inAxGroup.findFirst(AXRole='AXLink')

        if appinfoGroup1 is not None:
            appinfoGroup1 = inAxGroup.findFirst(AXRole='AXLink')
            if len(appinfoGroup1.AXTitle) > 0:
                baseAppName = appinfoGroup1.AXTitle

            if len(appinfoGroup1.AXURL) > 0:
                downloadUrl = appinfoGroup1.AXURL
                try:
                    baseAppId = str(downloadUrl).split('/id')[1].split('?')[0]
                except Exception, e:
                    print 'exception occurs when crawling appid'
                    print e
        try:
            appinfoGroup2 = inAxGroup.findFirst(AXRole='AXGroup').findFirst(AXRole='AXButton')
            if appinfoGroup2 is not None:
                # grabbing price
                formattedPrice = appinfoGroup2.AXDescription.split(',')[0]
                price = re.findall(r"[0-9\.]+", formattedPrice)
                if len(price) > 0:
                    # Paid
                    basePricing = float(price[0])
        except Exception, e:
            print e
        ret['appname'] = baseAppName
        ret['appid'] = baseAppId
        ret['pricing'] = basePricing
        ret['ratings'] = baseRatings
        ret['score'] = baseScore

        return ret

    # 调用kill -9 {pid} 杀死APP
    def terminateAppByName(self, name):
        cmd = "ps -e | grep \"%s\"" % name
        f = os.popen(cmd)
        txt = f.readlines()
        if len(txt) == 0:
            print "no process \"%s\"!!" % name
            return
        else:
            for line in txt:
                colum = line.split()
                pid = colum[0]
                cmd = "kill -9 %d" % int(pid)
                rc = os.system(cmd)
            if rc == 0:
                print "exec \"%s\" success!!" % cmd
            else:
                print "exec \"%s\" failed!!" % cmd
        return


def toolbarOfAppStore(appStoreRef):
    window = appStoreRef.AXMainWindow
    return window.findAll()[4]


def chooseIphoneApps(appStoreRef):
    window = appStoreRef.AXMainWindow
    targetButtons = \
        window.findFirst(AXRole='AXSplitGroup').findFirst(AXRole='AXScrollArea').findFirst(AXRole='AXWebArea'). \
            findFirst(AXRole='AXTabGroup').findAll(AXRole='AXRadioButton')

    for targetButton in targetButtons:
        if targetButton.AXTitle == 'iPhone Apps':
            targetButton.Press()
            return
