# coding=utf-8

from requests.models import HTTPError
from interface import config
from errors import CrawlerError

import typing
import interface.config as config
import requests
import bs4
import json
import misc
import logging


class ReportException(Exception):
    """上报异常错误信息"""
    class LoginError(Exception):
        """登录失败"""

    class SubmitError(Exception):
        """上报失败"""

    class ReportExistError(Exception):
        """已经上报"""


class Report(object):
    def __init__(self, proxy_on=True, ports=None):
        """参数初始化"""

        self.proxy_on = proxy_on
        self.proxy_ports = [] if ports is None else ports

        self.proxies = self.config_proxies()
        self.session = requests.session()

    def start_new_session(self):
        sess = requests.session()
        sess.headers.update({
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36'
        })
        self.session = sess

    def config_proxies(self, port: int = None):
        if port and self.proxy_on:
            socks5 = f"socks5h://127.0.0.1:{port}"
            proxies = {"http": socks5, "https": socks5}
            return proxies
        else:
            return None

    def switch_proxies(self, func):
        for p in self.proxy_ports:
            try:
                self.config_proxies(p)
                func()
            except Exception as error:
                logging.debug(error)
            else:
                logging.info(f"代理端口设定为：{p}")
                break
        else:
            raise ReportException.LoginError("无可用代理。")

    # log in jw system
    def login(self, loginFormPage, allLoginParams):

        self.start_new_session()
        # Add the given username and password into login params.
        allLoginParams["username"] = config.CrawlerParams.username
        allLoginParams["password"] = config.CrawlerParams.password

        # Login!
        # Get a validated COOKIE for our session.
        response = self.session.post(config.URLs.login_domain + loginFormPage,
                                     params=allLoginParams,
                                     proxies=self.proxies)

        if response.status_code != 200:
            raise CrawlerError("Login: Server responded error code: " +
                               str(response.status_code) + ".")
        elif response.text.find("账号密码验证失败") != -1:
            raise CrawlerError("Login: Incorrect username or password.")

    def getExcelRawData(self) -> bytes:
        response = self.session.post(config.URLs.uid_query,
                                     proxies=self.proxies)
        if response.status_code != 200:
            raise CrawlerError("Query User UID: Server responded error code" +
                               str(response.status_code) + ".")
        try:
            j = json.loads(response.text)
            UID = j["ID"]
        except json.JSONDecodeError:
            raise CrawlerError(
                "Query User UID: Get userinfo json from session failed.")
        except KeyError:
            raise CrawlerError(
                "Query User UID: Cannot find id in requested userinfo json.")

        excel_params = {"format": "excel", "_filename_": "export"}

        year, smcount = misc.semester(config.DateTime.startDate)
        # param "reportlets" seems to be a json-like stuff.
        # inelegant, indeed. But I'm too lazy to make a change. ;)
        excel_params[
            "reportlets"] = """%5B%7B%22reportlet%22%3A%22%2Fbyyt%2Fpkgl%2F%E5%AD%A6%E7%94%9F%\
    E4%B8%BB%E9%A1%B5%E8%AF%BE%E8%A1%A8%E5%AF%BC%E5%87%BA.cpt%22%2C%22xn%22%3A%22""" + year + """%22%2C\
    %22xq%22%3A%22""" + str(
                smcount) + "%22%2C%22dm%22%3A%22" + UID + "%22%7D%5D"

        response = self.session.post(config.URLs.excel_export,
                                     params=excel_params,
                                     proxies=self.proxies)
        if response.status_code != 200:
            raise CrawlerError("Get Excel: Server responded error code" +
                               response.status_code + ".")
        elif response.headers["content-type"].find("excel")==-1 and\
             response.headers["content-type"].find("xls")==-1:
            raise CrawlerError(
                "Get Excel: Server not responding excel format.")

        return response.content

    def get_text(self) -> typing.Tuple[str, dict]:
        response = self.session.get(config.URLs.login_page,
                                    proxies=self.proxies)
        if response.status_code != 200:
            raise CrawlerError("Get Login Page: Server responded error code" +
                               str(response.status_code) + ".")

        pageSoup = bs4.BeautifulSoup(response.text, "html.parser")
        formSoup = pageSoup.find("form")

        # Get form's attribute "action", which means action page
        form_page = formSoup.get("action")

        # Get all form input key and default values
        default_values = dict()
        inputSoups = formSoup.find_all("input")
        for i in inputSoups:
            default_values[i.get("name")] = i.get("value")

        return form_page, default_values
