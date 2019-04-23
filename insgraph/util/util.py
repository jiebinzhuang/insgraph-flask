import errno
import os

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .exceptions import PageNotFound404
from .instalogger import logger


def web_adress_navigator(browser, link):
    """Checks and compares current URL of web page and the URL to be navigated and if it is different, it does navigate"""

    try:
        current_url = browser.current_url
        logger.info("current_url is :"+current_url)
    except WebDriverException:
        try:
            current_url = browser.execute_script("return window.location.href")
            logger.info("current_url is :" + current_url)
        except WebDriverException as err:
            logger.exception("%s____%s" % (WebDriverException, err))
            current_url = None


    response = browser.get(link)
    if current_url is None or current_url != link:

        if check_page_title_notfound(browser):
            logger.error("Failed to get page " + link)
            raise PageNotFound404("Failed to get page " + link)
        #if response.status_code == 404:
        #    logger.error("Failed to get page " + link)
        #   raise PageNotFound404()
        # update server calls

        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "viewport")))



def check_page_title_notfound(browser):
    """ little bit hacky but selenium doesn't shown if 404 is send"""
    """ more infos https://github.com/seleniumhq/selenium-google-code-issue-archive/issues/141 """

    title = browser.title
    if title.lower().startswith('page not found'):
        return True
    return False

def check_folder(folder):
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    return True
