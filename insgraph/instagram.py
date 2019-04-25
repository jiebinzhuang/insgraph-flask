import json
import sys

from flask import (
    Blueprint, request)
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

from insgraph.util import extractor
from insgraph.util.extractor import extract_posts
from insgraph.util.settings import Settings
from insgraph.utils import httputil
from .util.account import login
from .util.chromedriver import init_chromedriver

bp = Blueprint('instagram', __name__, url_prefix='/instagram')

chrome_options = Options()
chromeOptions = webdriver.ChromeOptions()
prefs = {'profile.managed_default_content_settings.images': 2, 'disk-cache-size': 4096}
chromeOptions.add_experimental_option("prefs", prefs)
chrome_options.add_argument('--dns-prefetch-disable')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--lang=en-US')
chrome_options.add_argument('--headless')
chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:1080")
chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en-US'})

capabilities = DesiredCapabilities.CHROME
try:
    browser = init_chromedriver(chrome_options, capabilities)
except Exception as exc:
    print(exc)
    sys.exit()


@bp.route('/getUserInfo', methods=['GET'])
def getUserInfo():
    username = request.args.get("username")

    print('xxxxxxxxxxx---Extracting information from ' + username)
    try:
        if len(Settings.login_username) != 0:
            login(browser, Settings.login_username, Settings.login_password)

        information = extractor.extract_userinfo(browser, username)
    except:
        print("Error with user " + username)
        sys.exit(1)

    # print(information)
    content = json.dumps(information)
    resp = httputil.Response_headers(content)
    return resp


@bp.route('/getPostList', methods=['GET'])
def getPostList():
    username = request.args.get("username")
    amount = request.args.get("amount")
    if amount == 0 or amount is None:
        amount = 2
    print('xxxxxxxxxxx---Extracting information from ' + username)
    try:
        from insgraph.util.settings import Settings
        if len(Settings.login_username) != 0:
            login(browser, Settings.login_username, Settings.login_password)
        post_infos = extract_posts(browser, username, amount)
    except:
        print("Error with user " + username)
        sys.exit(1)

    # print(information)
    content = json.dumps(post_infos)
    resp = httputil.Response_headers(content)
    return resp
