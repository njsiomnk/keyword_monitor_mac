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


class AppleStore:

    bundle_name = 'com.apple.appstore'
    process_name = 'App Store.app'

    def __init__(self, shortSleepTime, longSleepTime, tryTime):
        self.shortSleepTime = shortSleepTime
        self.longSleepTime = longSleepTime
        self.tryTime = tryTime

    def initialStore(self):
        """
        start AppleStore
        :return:
        """
        print "initialing appStore"
        atomac.launchAppByBundleId(self.bundle_name)
        pattern = re.compile(u'No role')
        trytime = self.tryTime

        while pattern.search(str(atomac.getAppRefByBundleId(self.bundle_name))):
            print "step 1 sleep 5 sec..."
            time.sleep(self.shortSleepTime)

        appStoreRef = atomac.getAppRefByBundleId(self.bundle_name)
        # print appStoreRef
        pattern = re.compile('None')
        while trytime > 0 and pattern.search(str(appStoreRef.AXMainWindow.findAll()[0])):
            print "network excetion!try again in {}s,trytime remain {} times".format(self.shortSleepTime, self.tryTime)
            time.sleep(self.shortSleepTime)
            trytime -= 1

        return appStoreRef

    def selectRegion(self, appStoreRef, countryName):
        """
        choose country
        :param appStoreRef:
        :param countryName:
        :return:
        """
        axGroupList = appStoreRef.AXMainWindow.findFirst(AXRole='AXGroup').findFirst(AXRole='AXGroup').findFirst(
            AXRole='AXScrollArea') \
            .findFirst(AXRole='AXWebArea').findAll(AXRole='AXGroup')
        targetLink = axGroupList[len(axGroupList) - 2].findAll(AXRole='AXGroup')[1].findFirst(AXRole='AXLink')
        targetLink.Press()
        # .findFirst(AXRole='AXWebArea').findFirst(AXRole='AXGroup').findFirstR(AXRole='AXGroup')
        print 'Switching country/region to: {}'.format(countryName)
        time.sleep(self.longSleepTime)

        inTryTime = self.tryTime

        while (appStoreRef.AXMainWindow.findFirst(AXRole='AXGroup').findFirst(AXRole='AXGroup').findFirst(
                AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findFirst(
            AXRole='AXHeading') is None or appStoreRef.AXMainWindow.findFirst(AXRole='AXGroup').findFirst(
            AXRole='AXGroup').findFirst(AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findFirst(
            AXRole='AXHeading').findFirst(
            AXRole='AXStaticText').AXValue != 'Choose your country or region.') and inTryTime > 0:
            print 'page still loading! please wait for a minute'
            time.sleep(self.shortSleepTime)
            inTryTime -= 1

        AllcountryList = appStoreRef.AXMainWindow.findFirst(AXRole='AXGroup').findFirst(AXRole='AXGroup').findFirst(
            AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findAll(AXRole='AXGroup')

        for i in (1, 3, 5, 7, 9):
            countryList = AllcountryList[i].findAll(AXRole='AXGroup')
            for j in range(1, len(countryList), 2):
                if countryList[j].findFirst(AXRole='AXLink').staticTexts()[0].AXValue == countryName:
                    print "find target country's link: {}".format(
                        countryList[j].findFirst(AXRole='AXLink').staticTexts())
                    countryList[j].findFirst(AXRole='AXLink').Press()

        inTryTime = self.tryTime
        pattern = re.compile('None')
        while pattern.search(str(appStoreRef.AXMainWindow.findAll()[0])) and inTryTime > 0:
            print 'page still loading! please wait for a minute'
            time.sleep(self.shortSleepTime)
            inTryTime -= 1
        return

    def searchTextField(self, appStoreRef):
        """
        get obj of search text
        :param appStoreRef:
        :return:
        """
        time.sleep(self.shortSleepTime)
        toolbar = toolbarOfAppStore(appStoreRef)
        _searchTextField = toolbar.findAll()[6].findFirst()
        while not _searchTextField.AXEnabled:
            time.sleep(self.shortSleepTime)
            _searchTextField = toolbar.findAll()[6].findFirst()
        return _searchTextField

    def doSearch(self, searchField):
        """
        execute search action
        :param searchField:
        :return:
        """
        time.sleep(self.shortSleepTime)
        searchField.findFirst().Press()

    def groupsOfSearchResults(self, appStoreRef, keyword):
        """
        get results of search results
        :param appStoreRef:
        :param keyword:
        :return:
        """
        window = appStoreRef.AXMainWindow
        inTryTime = self.tryTime
        while (window.findAll()[0].findAll()[0].findAll()[0].findAll()[0].findAll()[
            1].AXDescription == u'' or window.findFirst(AXRole='AXGroup').findFirst(
            AXRole='AXGroup').findFirst(
            AXRole='AXScrollArea').findFirst(AXRole='AXWebArea').findFirst(AXRole='AXGroup') \
                .findFirst(AXRole='AXHeading').findFirst(
            AXRole='AXStaticText').AXValue.find(keyword) == -1) and inTryTime > 0:
            print 'page still loading'
            time.sleep(self.shortSleepTime)
            inTryTime -= 1

        results = window.findAll()[0].findAll()[0].findAll()[0].findAll()[0].findAll()
        return results

    def reBoot(self):
        """
        restart apps
        :return:
        """
        self.terminateAppByName(self.process_name)
        time.sleep(self.shortSleepTime)
        result = self.initialStore()
        return result

    # execute kill -9 {pid} kill app
    def terminateAppByName(self, name):
        """
        kill process by name
        :param name:
        :return:
        """
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
    """
    get toolbar obj of appStores
    :param appStoreRef:
    :return:
    """
    window = appStoreRef.AXMainWindow
    return window.findAll()[4]
