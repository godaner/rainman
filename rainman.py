#!/usr/bin/env python3
import json
import logging
import random
import smtplib
import urllib.request
from email.header import Header
from email.mime.text import MIMEText
from logging import handlers

import sys
import time
import yaml


class weather:
    time: str
    date: str
    whole_wea: str
    # day_wea: str
    # night_wea: str
    # whole_temp: str
    day_temp: str
    # night_temp: str


class email:
    pwd: str
    user: str
    to: []
    smtp: str

    def __init__(self):
        self._logger = logging.getLogger()

    def send(self, subject: str, content: str):
        smtp = smtplib.SMTP(self.smtp)
        smtp.login(self.user, self.pwd)
        try:
            message = MIMEText(content, 'plain', 'utf-8')
            message['From'] = Header("rainman", 'utf-8')
            # message['To'] = Header(self.to, 'utf-8')
            message['Subject'] = Header(subject, 'utf-8')
            smtp.sendmail(self.user, self.to, message.as_string())
            self._logger.error("send email to {} success".format(self.to))
        except smtplib.SMTPException as e:
            self._logger.error("send email to {} fail: {}".format(self.to, e))
        finally:
            smtp.quit()


class alarm:
    def __init__(self, email: email):
        self._logger = logging.getLogger()
        self._rain_change = []
        self._tmp_dec_change = []
        self._rain_days = []
        self._email = email

    def try_alarm(self, pre_old_weather: weather, old_weather: weather, pre_new_weather: weather, new_weather: weather):
        if "雨" not in old_weather.whole_wea and "雨" in new_weather.whole_wea:
            self._rain_change.append(
                "{}: {} -> {}".format(old_weather.date, old_weather.whole_wea, new_weather.whole_wea))
        old_tmp = pre_old_weather is not None and (int(pre_old_weather.day_temp) - int(old_weather.day_temp)) < 5
        new_tmp = pre_new_weather is not None and (int(pre_new_weather.day_temp) - int(new_weather.day_temp)) >= 5
        if old_tmp and new_tmp:
            self._tmp_dec_change.append(
                "{}: {} -> {}: {}".format(pre_new_weather.date, pre_new_weather.day_temp, new_weather.date,
                                          new_weather.day_temp))

    def do_it(self):
        content = []
        if len(self._rain_change) > 0:
            content.append("下雨天预报改变：\n" + "\n".join(self._rain_change))
        if len(self._tmp_dec_change) > 0:
            content.append("气温下降预报改变：\n" + "\n".join(self._tmp_dec_change))
        if len(content) > 0:
            content = "\n".join(content)
            self._logger.info(content)
            self._email.send("天气预报改变", content)


class rainman:
    def __init__(self, conf: {}):
        self._logger = logging.getLogger()
        self._conf = conf
        self._emails = []
        self._weather_m = {}
        self._email = email()
        try:
            self._email.pwd = self._conf["email"]['pwd']
        except BaseException as e:
            raise Exception("get email pwd err: {}".format(e))

        try:
            self._email.user = self._conf["email"]['user']
        except BaseException as e:
            raise Exception("get email user err: {}".format(e))
        try:
            self._email.to = str(self._conf["email"]['to']).split(",")
        except BaseException as e:
            raise Exception("get email to err: {}".format(e))
        try:
            self._email.smtp = self._conf["email"]['smtp']
        except BaseException as e:
            raise Exception("get email smtp err: {}".format(e))

        try:
            self._url = self._conf["url"]
        except BaseException as e:
            raise Exception("get url err: {}".format(e))
        try:
            self._headers = self._conf["headers"]
        except BaseException as e:
            raise Exception("get headers err: {}".format(e))
        return

    def __str__(self):
        return str(self._conf)

    def start(self):
        while 1:
            self.analyze()
            # sec = random.randint(30, 300)
            sec = random.randint(1, 5)
            self._logger.info("analyze in {}s...".format(sec))
            time.sleep(sec)

    def analyze(self):
        req = urllib.request.Request(self._url, data=None, headers=self._headers)
        resp = urllib.request.urlopen(req)
        resp = json.loads(resp.read())
        self._logger.info("resp: {}".format(resp))
        new_weather_m = {}
        old_weather_m = self._weather_m
        for data in resp['data']:
            # self._logger.info("data: {}".format(data))
            weather_d = weather()
            weather_d.time = time.localtime(data['time'])
            weather_d.date = data['date']
            weather_d.whole_wea = data['whole_wea']
            weather_d.day_wea = data['day_wea']
            weather_d.night_wea = data['night_wea']
            weather_d.whole_temp = data['whole_temp']
            weather_d.day_temp = data['day_temp']
            weather_d.night_temp = data['night_temp']
            new_weather_m[weather_d.date] = weather_d

        if len(old_weather_m) != 0:
            al = alarm(self._email)
            pre_new_weather = None
            pre_old_weather = None
            for k in old_weather_m:
                old_weather = old_weather_m[k]
                new_weather = new_weather_m.get(k)
                if new_weather is None:
                    continue
                al.try_alarm(pre_old_weather, old_weather, pre_new_weather, new_weather)
                pre_new_weather = new_weather
                pre_old_weather = old_weather
            al.do_it()
        self._weather_m = new_weather_m


def main():
    if len(sys.argv) != 2:
        config_file = "./rainman.yaml"
    else:
        config_file = sys.argv[1]
    with open(config_file, 'r') as f:
        conf = yaml.safe_load(f)
    lev = logging.INFO
    try:
        debug = conf['debug']
    except BaseException as e:
        debug = False
    if debug:
        lev = logging.DEBUG
    hs = []
    file_handler = handlers.TimedRotatingFileHandler(filename="./rainman.log", when='D', backupCount=1,
                                                     encoding='utf-8')
    hs.append(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    hs.append(console_handler)
    logging.basicConfig(level=lev, format='%(message)s', handlers=hs)
    logger = logging.getLogger()
    rm = rainman(conf)
    logger.info("rainman info: {0}".format(rm))
    rm.start()


if __name__ == "__main__":
    main()
