"""Methods to extract the data for the given usernames profile"""
import math
from time import sleep

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from insgraph.util.extractor_posts import extract_post_info
from .exceptions import PageNotFound404, NoInstaProfilePageFound
from .instalogger import logger
from .settings import Settings
from .util import web_adress_navigator


def extract_user_posts(browser, num_of_posts_to_do):
    """Get all posts from user"""
    links2 = []
    preview_imgs = {}

    try:
        body_elem = browser.find_element_by_tag_name('body')

        previouslen = 0
        breaking = 0

        print("number of posts to do: ", num_of_posts_to_do)
        num_of_posts_to_scroll = 12 * math.ceil(num_of_posts_to_do / 12)
        print("Getting first", num_of_posts_to_scroll,
              "posts but checking ", num_of_posts_to_do,
              " posts only, if you want to change this limit, change limit_amount value in crawl_profile.py\n")
        while (len(links2) < num_of_posts_to_do):

            prev_divs = browser.find_elements_by_tag_name('main')
            links_elems = [div.find_elements_by_tag_name('a') for div in prev_divs]
            links = sum([[link_elem.get_attribute('href')
                          for link_elem in elems] for elems in links_elems], [])

            for elems in links_elems:
                for link_elem in elems:

                    href = link_elem.get_attribute('href')
                    try:
                        if "/p/" in href:
                            try:
                                img = link_elem.find_element_by_tag_name('img')
                                src = img.get_attribute('src')
                                preview_imgs[href] = src
                            except NoSuchElementException:
                                print("img exception 132")
                                continue
                    except Exception as err:
                        print(err)

            for link in links:
                if "/p/" in link:
                    if (len(links2) < num_of_posts_to_do):
                        links2.append(link)
            # links2 = list(set(links2))
            print("Scrolling profile ", len(links2), "/", num_of_posts_to_scroll)
            body_elem.send_keys(Keys.END)
            sleep(Settings.sleep_time_between_post_scroll)

            ##remove bellow part to never break the scrolling script before reaching the num_of_posts
            if (len(links2) == previouslen):
                breaking += 1
                print("breaking in ", 4 - breaking,
                      "...\nIf you believe this is only caused by slow internet, increase sleep time 'sleep_time_between_post_scroll' in settings.py")
            else:
                breaking = 0
            if breaking > 3:
                print("Not getting any more posts, ending scrolling")
                sleep(2)
                break
            previouslen = len(links2)
            ##

    except NoSuchElementException as err:
        logger.error('Something went terribly wrong')

    post_infos = []

    counter = 1
    # into user_commented_total_list I will add all username links who commented on any post of this user
    user_commented_total_list = []

    for postlink in links2:

        print("\n", counter, "/", len(links2))
        counter = counter + 1

        try:
            caption, location_url, location_name, location_id, lat, lng, imgs, \
            imgdesc, tags, likes, commentscount, date, user_commented_list, user_comments, \
            mentions, user_liked_post, views, video_url = extract_post_info(
                browser, postlink)

            location = {
                'location_url': location_url,
                'location_name': location_name,
                'location_id': location_id,
                'latitude': lat,
                'longitude': lng,
            }

            post_infos.append({
                'caption': caption,
                'location': location,
                'imgs': imgs,
                'imgdesc': imgdesc,
                'preview_img': preview_imgs.get(postlink, None),
                'date': date,
                'tags': tags,
                'likes': {
                    'count': likes,
                    'list': user_liked_post
                },
                'views': views,
                'url': postlink,
                'comments': {
                    'count': commentscount,
                    'list': user_comments
                },
                'mentions': mentions,
                'video_url': video_url
            })
            user_commented_total_list = user_commented_total_list + user_commented_list
        except NoSuchElementException as err:
            logger.error("Could not get information from post: " + postlink)
            logger.error(err)
        except:
            logger.error("Could not get information from post: " + postlink)
    return post_infos, user_commented_total_list


def zjb_extract_tag_posts(browser, tagname, limit_amount):
    # print 222
    # print username

    logger.info("Extracting extract_posts from " + tagname)
    # print 123
    isprivate = False
    try:
        user_link = "https://www.instagram.com/explore/tags/{}/".format(tagname)
        web_adress_navigator(browser, user_link)
    except PageNotFound404 as e:
        raise NoInstaProfilePageFound(e)

    try:
        post_infos, user_commented_total_list = extract_user_posts(browser, limit_amount)
    except:
        logger.error("Couldn't get user posts.")

    return post_infos


def zjb_search(browser, content):
    logger.info("Extracting extract_posts from " + content)
    try:
        user_link = "https://www.instagram.com/web/search/topsearch/?context=blended&query=" + content + "&rank_token=0.7952663657241419&include_reel=true"
        response = browser.get(user_link)
        jsonEle = browser.find_element_by_tag_name('pre')
        jsonEle.text
        logger.info(jsonEle.text)
        return jsonEle.text
    except PageNotFound404 as e:
        raise NoInstaProfilePageFound(e)

    return ""


def zjb_extract_postlist(browser, num_of_posts_to_do):
    """Get all posts from user"""
    links2 = []

    post_infos = []



    try:
        body_elem = browser.find_element_by_tag_name('body')

        previouslen = 0
        breaking = 0

        print("number of posts to do: ", num_of_posts_to_do)
        num_of_posts_to_scroll = 12 * math.ceil(num_of_posts_to_do / 12)
        print("Getting first", num_of_posts_to_scroll,
              "posts but checking ", num_of_posts_to_do,
              " posts only, if you want to change this limit, change limit_amount value in crawl_profile.py\n")
        while (len(links2) < num_of_posts_to_do):

            prev_divs = browser.find_elements_by_tag_name('main')
            links_elems = [div.find_elements_by_tag_name('a') for div in prev_divs]
            links = sum([[link_elem.get_attribute('href')
                          for link_elem in elems] for elems in links_elems], [])

            for elems in links_elems:
                for link_elem in elems:

                    href = link_elem.get_attribute('href')

                    try:
                        if "/p/" in href:
                            try:
                                img = link_elem.find_element_by_tag_name('img')
                                src = img.get_attribute('src')
                                post_info = {}
                                post_info["href"] = href
                                post_info["preview_img"] = src

                                try:
                                    span = link_elem.find_element_by_tag_name('span')
                                    post_info["video"] = "true"
                                except NoSuchElementException:
                                    print("video exception 132")
                                    post_info["video"] = "false"

                                post_infos.append(post_info)

                            except NoSuchElementException:
                                print("img exception 132")
                                continue
                    except Exception as err:
                        print(err)

            for link in links:
                if "/p/" in link:
                    if (len(links2) < num_of_posts_to_do):
                        links2.append(link)
            # links2 = list(set(links2))
            print("Scrolling profile ", len(links2), "/", num_of_posts_to_scroll)
            body_elem.send_keys(Keys.END)
            sleep(Settings.sleep_time_between_post_scroll)

            ##remove bellow part to never break the scrolling script before reaching the num_of_posts
            if (len(links2) == previouslen):
                breaking += 1
                print("breaking in ", 4 - breaking,
                      "...\nIf you believe this is only caused by slow internet, increase sleep time 'sleep_time_between_post_scroll' in settings.py")
            else:
                breaking = 0
            if breaking > 3:
                print("Not getting any more posts, ending scrolling")
                sleep(2)
                break
            previouslen = len(links2)
            ##

    except NoSuchElementException as err:
        logger.error('Something went terribly wrong')

    return post_infos

# def zjb_get_post_detail(browser,url):
