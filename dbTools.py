# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
import psycopg2


def datumExist(inConn, inTableName, inDateField, keyword, os, inSpecDate):
    print 'check if the datum of specsial date: {} is already inserted into DB:'.format(inSpecDate)
    cur = inConn.cursor()
    sql = "select * from {} where {} = '{}' and keyword = '{}' and os = '{}'".format(inTableName, inDateField,
                                                                                     inSpecDate.strftime('%Y-%m-%d'),
                                                                                     keyword, os)

    try:
        cur.execute(sql)
        resultnum = len(cur.fetchall())
        if resultnum == 0:
            return False
        else:
            return True
    except psycopg2.DatabaseError, e:
        print '**********got databaseerror: {}'.format(e.message)


def deleteDatum(inConn, inTableName, inDateField, keyword, os, inSpecDate):
    print 'datum of specsial date: {} is already inserted into DB:'.format(inSpecDate)
    print 'delete in advance before insert'
    cur = inConn.cursor()
    sql = "delete from {} where {} = '{}' and keyword = '{}' and os = '{}'".format(inTableName, inDateField,
                                                                                   inSpecDate.strftime('%Y-%m-%d'),
                                                                                   keyword, os)
    try:
        cur.execute(sql)
        inConn.commit()
        print 'delete success'
    except psycopg2.DatabaseError, e:
        print '**********got databaseerror: {}'.format(e.message)


def batchInsertToDB(inConn, inTableName, Feilds, inResults):
    print "beging write result"
    cur = inConn.cursor()
    mFeilds = '('
    mValues = '('
    length = len(Feilds)
    for i in range(0, length - 1):
        mFeilds += Feilds[i] + ', '
        mValues += '%s, '
    mFeilds += Feilds[length - 1] + ')'
    mValues += '%s)'

    strSql = "INSERT INTO {} {} VALUES {}".format(inTableName, mFeilds, mValues)
    try:
        cur.executemany(strSql, inResults)
        inConn.commit()
    except psycopg2.DatabaseError, e:
        print '**********got databaseerror: {}'.format(e.message)
        inConn.rollback()
        # inConn.close()
        return False

    print "write result end"
    return True


def getFocusCoutyies(inConn):
    ret = []
    inCur = inConn.cursor()
    sql = """select "country_name", "country_code" from basicinfo_country"""

    try:
        inCur.execute(sql)
        for countryName, CountryShortName_string in inCur.fetchall():
            ret.append((countryName, CountryShortName_string))
    except Exception, e:
        print e
        return None
    return ret


def getCurrencyPairs(inConn):
    ret = []
    inCur = inConn.cursor()
    sql = """select "country_name", "country_code", "currency" from basicinfo_country"""

    try:
        inCur.execute(sql)
        for countryName, CountryShortName_string, currency in inCur.fetchall():
            ret.append((countryName, CountryShortName_string, currency))
    except Exception, e:
        print e
        return None
    return ret
