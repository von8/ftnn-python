#!/usr/bin/python2.6  
# -*- coding: utf-8 -*-  
'''
Created on 2015年9月9日
#脚本说明: !!!
#
#每隔2秒， 回显相关股票报价数据  
#
@author: futu
'''

import socket
import json
import string
import sys
import threading
import time
import datetime
import MySQLdb, MySQLdb.cursors
import numpy as np

############################s###################################################################### 
class Refresher:
    #look for mouse clicks
    def __init__(self, fig):
        self.canvas = fig.canvas
        self.cid = fig.canvas.mpl_connect('button_press_event', self.onclick)

    #when there is a mouse click, redraw the graph
    def onclick(self, event):
        self.canvas.draw()

#timer定时器的一个实现
class Timer(threading.Thread):
    """
    very simple but useless timer.
    """
    def __init__(self, seconds):
        self.runTime = seconds
        threading.Thread.__init__(self)
    def run(self):
        time.sleep(self.runTime)
        print "Buzzzz!! Time's up!"
class CountDownTimer(Timer):
    """
    a timer that can counts down the seconds.
    """
    def run(self):
        counter = self.runTime
        for sec in range(self.runTime):
            time.sleep(1.0)
            counter -= 1
class CountDownExec(CountDownTimer):
    """
    a timer that execute an action at the end of the timer run.
    """
    def __init__(self, seconds, action, args, po_sum, ave_5day):
        self.args = args
        self.po_sum = po_sum
        self.ave_5day = ave_5day
        self.action = action
        CountDownTimer.__init__(self, seconds)
    def run(self):
        CountDownTimer.run(self)
        self.action(self.args, self.po_sum, self.ave_5day)

        

################################################################################################## 

#futnn plubin会开启本地监听服务端 
# 请求及发送数据都是jason格式, 具体详见插件的协议文档 
host="localhost"
port=11111

#发送请求: 当前报价 
def fun_GetQuotePrice(args, po_sum, ave_5day):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect((host,port))
    req = {'Protocol':'1001', 'ReqParam':{'Market':'2','StockCode':'TSLA'},'Version':'1'}
    print u'正在获取%s报价...' %req['ReqParam']['StockCode']
    str = json.dumps(req) + "\r\n"
    s.send(str) 
    rsp = s.recv(4096)
    str = rsp[:rsp.index("\r\n")]
    decode = json.loads(str) 
    err = decode["ErrCode"]
    print "GetPrice Err=%s"%err
    trade_time = int(decode["RetData"]["Time"])
    print trade_time
    if err == "0":
            cp, lc, hi, lo, SvrTime = save_data(decode)
            print u'现价=%.3f, 昨收价=%.3f, 最高价=%.3f, 最低价=%.3f' %(cp, lc, hi, lo)
            print "+------------------------------------------------------------+"
            print ''
            args.append(cp)
            args.pop(0)
            a = [args[1]-args[0], args[2]-args[1], args[3]-args[2], args[4]-args[3]]
            RSI, po_sum, ave_5day = compute_rsi5min(a, po_sum, ave_5day)
            print u'相对强弱指标RSI=%.3f 前五个收盘价=%s' %(RSI, args)

    s.close()
   
    t1 = CountDownExec(2, fun_GetQuotePrice, args, po_sum, ave_5day)
    t1.start()

def save_data(data):
    cp = data["RetData"]["Close"]
    cp = float(cp)/1000
    lc = data["RetData"]["LastClose"]
    lc = float(lc)/1000
    hi = data["RetData"]["High"]
    hi = float(hi)/1000
    lo = data["RetData"]["Low"]
    lo = float(lo)/1000
    ti = data["RetData"]["Time"]
    now = datetime.datetime.now() #get system clock
    date = datetime.datetime.date(now) #split date from datetime.now()
    st = convert_seconds(int(ti))
    str_date = date.strftime('%Y-%m-%d')
    SvrTime = str_date+' '+st
    db, cursor = conn_db()
    sql = u'''
    INSERT INTO Tencent (`Close`, `LastClose`, `High`, `Low`, `SysTime`, `SvrTime`) 
    VALUES (%s, %s, %s, %s, %s, %s)
    '''
    print u'Saving.... %s' %now
    print ''
    print "+---------------------%s--------------------+" %SvrTime
    cursor.execute(sql, (cp, lc, hi, lo, now, SvrTime))
    db.commit() #In InnoDB, need to add this 
    db.close() #db close
    return cp, lc, hi, lo, SvrTime    

def convert_seconds(int_time):
    hhmmss = time.strftime('%H:%M:%S', time.gmtime(int_time))
    return hhmmss

#db connect
def conn_db():
    host = 'localhost'
    user = 'root'
    password = '654321'
    dbname = 'price2s'
    coon = MySQLdb.connect(host=host, user=user, passwd=password, db=dbname, charset="utf8", cursorclass=MySQLdb.cursors.DictCursor)
    cursor = coon.cursor()

    sql = 'set names utf8'
    cursor.execute(sql)
    return coon, cursor

#compute 5 minutes RSI
def compute_rsi5min(a,po_sum, ave_5day):
    po=[]
    ne=[]
    all_5days = map(abs,a)
    for x in a:
        if x>0:
            po.append(x)

    po_sum_last = po_sum
    po_sum = (sum(po) + 4*po_sum_last)/5

    ave_5day_last = ave_5day
    ave_5day = (sum(all_5days) + 4*ave_5day_last)/5


    try:
        RSI5 = po_sum/ave_5day*100
    except ZeroDivisionError:
        print 'Division by zero'
        RSI5 = -1
        return RSI5
    else:
        print po, po_sum, ave_5day
        return RSI5, po_sum, ave_5day

def makeFig():
    plt.ylim(0,105)
    plt.title('Two minutes RSI')
    plt.grid(True)
    plt.ylabel('RSI')
    plt.plot(y, 'ro-', label='Degrees F')
    plt.legend(loc='upper left')

b = [0, 0, 0, 0, 0]
po_sum = 0
ave_5day = 0
t1 = CountDownExec(2, fun_GetQuotePrice, b, po_sum, ave_5day)
t1.start()
