# -*- coding: utf-8 -*-
import traceback
import requests
import web
from web import BadRequest, InternalError, HTTPError
import os, sys, logging
import config, types
from model import Data
from threading import Timer
import time
import pydblite
os.chdir(os.path.dirname(sys.argv[0]))
db = pydblite.Base('users.pdl')
db.create('ips', 'cfg', mode="open")

web.config.debug = False
_log = logging.getLogger(__name__)

urls = (
    '/', 'index',
    '/starttest', 'starttest',
    '/stoptest', 'stoptest',
    '/additem', 'additem',
    '/viewitem/(.*)', 'viewitem',
    '/delitem', 'delitem',
    '/singlepost', 'singlepost',
    '/freshpage', 'freshpage'
)

stop_code = ['4010', '5010', '100', '201','200']
t = None
app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={})
render = web.template.render('templates', globals={'context': session})


def _getModel(ips):
    cfg = Data()
    if _getdb(ips):
        cfg.from_json(_getdb(ips)[0]['cfg'])
    else:
        with open("data.json") as file:
            cfg.from_json(file.read())

        cfg.run = False
        cfg.error = False
        cfg.sc_run = 0  # 0 serials; 1 concurrence
        cfg.envs = '0'  # cfg. 0 self; 1 dev; 2 beta
        cfg.peerip = ''
        cfg.ips = web.ctx.ip
        cfg.peerport = ''
        _updatedb(ips, cfg.to_json())
    return cfg


def _testshutdown(ips):
    cfg = _getModel(ips)
    cfg.run = False
    cfg.error = True
    _updatedb(ips, cfg.to_json())


def _ticksession():
    global t
    t = Timer(3, _checktimer)
    t.start()


def _getdb(ips):
    if [x for x in db('ips') == ips]:
        return [x for x in db('ips') == ips]
    return []


def _updatedb(ips, d):
    if _getdb(ips):
        for x in db('ips') == ips:
            db.update(x, cfg=d)
    else:
        db.insert(ips, d)


def _checktimer():
    while True:
        try:
            time.sleep(2)
            # print 'check timer'
            db.commit()
            for item in db:
                cfg = Data()
                cfg.from_json(item['cfg'])
                flag = False
                for case in cfg.cases:
                    for twotask in case['data']:
                        if not twotask['resp'] or twotask['status'] not in stop_code or twotask['createtime'] == 0 or (
                                        twotask['createtime'] != 0 and time.time() - twotask['createtime'] > 350):
                            continue
                        if twotask['resp']['result']['code'] != 'success':
                            twotask['status'] = 'fail'
                            continue
                        flag = True
                        data = 'requestId=%s&taskey=%s' % (twotask['resp']['requestId'], twotask['resp']['taskkey'][5:])
                        it = _http_post(cfg.server[cfg.envs]['findtaskurl'], data)
                        ret = Data()
                        try:
                            ret.from_json(it)
                        except:
                            _log.error(traceback.format_exc())
                            ret.result = []
                        for r in ret.result:
                            twotask['status'] = r['taskStatus']
                            if r['taskStatus'] not in stop_code:
                                break
                        twotask['rawdata'] = ret.to_json()
                cfg.run = flag
                _updatedb(item['ips'], cfg.to_json())
        except:
            _log.error(traceback.format_exc())


def internalerror(message):
    return _response(500, message)


def notfound(message):
    return _response(400, message)


def my_loadhook():
    web.header('Content-Type', 'text/html; charset=utf-8', unique=True)


class index:
    def GET(self, name=None):
        cfg = _getModel(web.ctx.ip)
        return render.index(cfg)


class additem:
    def POST(self):
        orgg = web.input().orgg
        typee = web.input().typee
        logintypee = web.input().logintypee
        usernamee = web.input().usernamee
        pwdd = web.input().pwdd
        if not usernamee or not pwdd:
            return _response(400, 'empty value')
        cfg = _getModel(web.ctx.ip)
        if cfg.run:
            return _response(400, 'running')
        addi = Data()
        addi.id = str(int(time.time())) + ""
        addi.org = orgg
        addi.entry = typee
        addi.logintype = logintypee
        addi.user = usernamee
        addi.pwd = pwdd
        addi.resp = ''
        addi.status = '0'
        addi.createtime = 0
        findexist = False
        for ac in cfg.cases:
            if ac['bank'] == orgg:
                findexist = True
                ac['data'].append(addi.to_dict())
        if not findexist:
            newbank = Data()
            newbank.bank = orgg
            newbank.data = []
            newbank.data.append(addi)
            cfg.cases.append(newbank)
        _updatedb(web.ctx.ip, cfg.to_json())
        return _response(200, 'ok')


def _response(code, msg):
    ret = Data()
    ret.code = code
    ret.message = msg
    return ret.to_json()


class singlepost:
    def POST(self):
        id = web.input().id
        value = web.input().value
        if not id or not value:
            return _response(200, 'no id or value')
        cfg = _getModel(web.ctx.ip)
        if not cfg.run:
            return _response(200, 'not run')
        for sc in cfg.cases:
            for scd in sc['data']:
                if scd['id'] == id:
                    if not scd['resp'] or scd['status'] != '4010':
                        _log.info('4010 redo')
                        return _response(200, 'null')
                    try:
                        scd['status'] = '4010 '
                        _updatedb(web.ctx.ip, cfg.to_json())
                        data = 'org=%s&taskName=%s&channel=hywechat&loginType=%s&passWord=%s' \
                               '&login=%s&extralParams=1001&extralParamsValue=%s&extralParamsA=' \
                               '&extralParamsValueA=&extralParamsB=&extralParamsValueB=&host=%s&port=%s' \
                               '&id=%s&timeout=0&signature=&taskey=%s&crawlChange=1000' % (
                                   scd['org'], scd['entry'], scd['logintype'], scd['pwd'], scd['user'], value,
                                   cfg.peerip, cfg.peerport, scd['resp']['id'], scd['resp']['taskkey'])
                        sit = _http_post(cfg.server[cfg.envs]['sendtaskurl'], data)
                        singleret = Data()
                        singleret.from_json(sit)
                        tmpp = Data()
                        tmpp.from_json(singleret.result)
                        singleret.result = tmpp
                        scd['resp'] = singleret
                    except:
                        return _response(500, 'single post error')
        _updatedb(web.ctx.ip, cfg.to_json())
        return _response(200, 'ok')


class freshpage:
    def GET(self):
        web.header('Content-Type', 'text/json; charset=utf-8', unique=True)
        cfg = _getModel(web.ctx.ip)
        return _response(200, cfg.to_json())


class delitem:
    def POST(self):
        id = web.input().id
        if not id:
            return _response(200, '')

        cfg = _getModel(web.ctx.ip)
        if cfg.run:
            return _response(400, 'running')

        for dc in cfg.cases:
            dc['data'] = [dci for dci in dc['data'] if dci['id'] != id]
        _updatedb(web.ctx.ip, cfg.to_json())
        return _response(200, 'ok')


class freshimg:
    def POST(self):
        pass


class viewitem:
    def GET(self, id):
        if not id:
            return ''
        web.header('Content-Type', 'text/json; charset=utf-8', unique=True)
        cfg = _getModel(web.ctx.ip)
        for vc in cfg.cases:
            for vcd in vc['data']:
                if vcd['id'] == id:
                    try:
                        vi = Data()
                        if vcd.has_key('rawdata'):
                            vi.from_json(vcd['rawdata'])
                            if len(vi.result) == 0 and isinstance(vcd['resp'], types.DictType):
                                vi.from_dict(vcd['resp'])
                        else:
                            vi.from_dict(vcd['resp'])
                        return vi.to_json()
                    except:
                        return vcd['resp']
        return ''


class starttest:
    def POST(self):
        cfg = _getModel(web.ctx.ip)
        if cfg.run:
            return _response(400, u'测试中')
        cfg.run = True
        _log.info("starttest")
        cfg.sc_run = web.input().sc_run
        cfg.envs = web.input().envs
        org = web.input().org
        _log.info('sc_run:' + cfg.sc_run + ' envs:' + cfg.envs + ' org:' + org)
        if cfg.envs == '0':
            cfg.peerip = web.ctx.ip
            if web.ctx.ip == '127.0.0.1':
                cfg.peerip = '172.18.40.8'
            cfg.peerport = '8088'
        else:
            cfg.peerip = ''
            cfg.peerport = ''
        for testi in cfg.cases:
            for onetask in testi['data']:
                if org == 'all' or testi['bank'] == org:
                    data = 'org=%s&taskName=%s&channel=hywechat&loginType=%s&passWord=%s' \
                           '&login=%s&extralParams=1000&extralParamsValue=&extralParamsA=' \
                           '&extralParamsValueA=&extralParamsB=&extralParamsValueB=&host=%s&port=%s' \
                           '&id=&timeout=0&signature=&taskey=&crawlChange=1000' % (
                               onetask['org'], onetask['entry'], onetask['logintype'], onetask['pwd'], onetask['user'],
                               cfg.peerip,
                               cfg.peerport)
                    try:
                        it = _http_post(cfg.server[cfg.envs]['sendtaskurl'], data)
                        oneret = Data()
                        oneret.from_json(it)
                        tmpp = Data()
                        tmpp.from_json(oneret.result)
                        oneret.result = tmpp
                    except:
                        _log.error(traceback.format_exc())
                        _testshutdown(web.ctx.ip)
                        return _response(500, 'remote server error')
                    onetask['createtime'] = time.time()
                    onetask['status'] = '100'
                    onetask['rawdata'] = ''
                    onetask['resp'] = oneret
        _updatedb(web.ctx.ip, cfg.to_json())
        return _response(200, "success")


class stoptest:
    def POST(self):
        pass


def _http_post(url, data):
    try:
        _log.info(data)
        s = requests.session()
        s.headers.update({'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        resp = s.post(url, verify=False, timeout=40, data=data.encode('utf-8'))
        _log.info(resp.content)
        return resp.content
    except:
        _log.error(traceback.format_exc())
    return '{"result": {"code": "fail","result":{"success":false,"error":"post to remote server time out"}}}'


if __name__ == "__main__":
    _log.info("server start~")
    _ticksession()
    # app.add_processor(web.loadhook(my_loadhook))
    # app.internalerror = internalerror
    # app.notfound = notfound
    app.run()
