import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import asyncio
from bs4 import BeautifulSoup
from utils import (
    getChannelItems,
    updateChannelUrlsTxt,
    updateFile,
    getUrlInfo,
    compareSpeedAndResolution,
    getTotalUrls,
    filterSortedDataByIPVType,
    filterByIPVType,
)
import logging

logging.basicConfig(
    filename="result_new.log",
    filemode="a",
    format="%(message)s",
    level=logging.INFO,
)


class UpdateSource:

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("start-maximized")
        options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("blink-settings=imagesEnabled=false")
        driver = webdriver.Chrome(options=options)
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def __init__(self):
        self.driver = self.setup_driver()

    async def visitPage(self, channelItems):
        for cate, channelObj in channelItems.items():
            channelUrls = {}
            for name in channelObj.keys():
                isFavorite = name in config.favorite_list
                pageNum = (
                    config.favorite_page_num if isFavorite else config.default_page_num
                )
                infoList = []
                for page in range(1, pageNum):
                    try:
                        page_url = f"http://tonkiang.us/?page={page}&s={name}"
                        self.driver.get(page_url)
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.tables")
                            )
                        )
                        soup = BeautifulSoup(self.driver.page_source, "html.parser")
                        tables_div = soup.find("div", class_="tables")
                        results = (
                            tables_div.find_all("div", class_="result")
                            if tables_div
                            else []
                        )
                        if not any(
                            result.find("div", class_="m3u8") for result in results
                        ):
                            break
                        for result in results:
                            try:
                                url, date, resolution = getUrlInfo(result)
                                if url:
                                    infoList.append((url, date, resolution))
                            except Exception as e:
                                print(f"Error on result {result}: {e}")
                                continue
                    except Exception as e:
                        print(f"Error on page {page}: {e}")
                        continue
                try:
                    sorted_data = await compareSpeedAndResolution(infoList)
                    ipvSortedData = filterSortedDataByIPVType(sorted_data)
                    if ipvSortedData:
                        channelUrls[name] = (
                            getTotalUrls(ipvSortedData) or channelObj[name]
                        )
                        for (url, date, resolution), response_time in ipvSortedData:
                            logging.info(
                                f"Name: {name}, URL: {url}, Date: {date}, Resolution: {resolution}, Response Time: {response_time}ms"
                            )
                    else:
                        channelUrls[name] = filterByIPVType(channelObj[name])
                except Exception as e:
                    print(f"Error on sorting: {e}")
                    continue
            updateChannelUrlsTxt(cate, channelUrls)
            # await asyncio.sleep(1)

    def main(self):
        asyncio.run(self.visitPage(getChannelItems()))
        updateFile(config.final_file, "result_new.txt")
        updateFile("result.log", "result_new.log")


UpdateSource().main()
