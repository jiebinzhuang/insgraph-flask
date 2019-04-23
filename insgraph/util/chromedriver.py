import re

from selenium import webdriver

from .exceptions import WebDriverException
from .instalogger import logger
from .settings import Settings


def init_chromedriver(chrome_options, capabilities):
    chromedriver_location = Settings.chromedriver_location
    try:
        browser = webdriver.Chrome(chromedriver_location,
                                                desired_capabilities=capabilities,
                                                chrome_options=chrome_options)
    except WebDriverException as exc:
        logger.error('ensure chromedriver is installed at {}'.format(
            Settings.chromedriver_location))
        raise exc

    matches = re.match(r'^(\d+\.\d+)',
                       browser.capabilities['chrome']['chromedriverVersion'])
    if float(matches.groups()[0]) < Settings.chromedriver_min_version:
        logger.error('chromedriver {} is not supported, expects {}+'.format(
            float(matches.groups()[0]), Settings.chromedriver_min_version))
        browser.close()
        raise Exception('wrong chromedriver version')

    return browser