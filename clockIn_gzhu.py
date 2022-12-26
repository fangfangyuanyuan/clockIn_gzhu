import os
import sys
import traceback

import requests
import selenium.webdriver
from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.relative_locator import locate_with
from selenium.webdriver.support.wait import WebDriverWait


class clockIn():

    def __init__(self):
        self.xuhao = str(os.environ['XUHAO'])
        self.mima = str(os.environ['MIMA'])
        self.pushplus = str(os.environ['PUSHPLUS'])

        options = Options()
        optionsList = [
            "--headless", "--enable-javascript", "start-maximized",
            "--disable-gpu", "--disable-extensions", "--no-sandbox",
            "--disable-browser-side-navigation", "--disable-dev-shm-usage"
        ]

        for option in optionsList:
            options.add_argument(option)

        options.page_load_strategy = 'none'
        options.add_experimental_option(
            "excludeSwitches",
            ["ignore-certificate-errors", "enable-automation"])

        self.driver = selenium.webdriver.Chrome(options=options)
        self.wdwait = WebDriverWait(self.driver, 60)
        self.titlewait = WebDriverWait(self.driver, 10)

        # self.page用来表示当前页面标题，0表示初始页面
        self.page = 0

        # self.fail表示打卡失败与否
        self.fail = False

    def __call__(self):
        for retries in range(5):
            try:
                logger.info(f"第{retries+1}次运行")
                if retries:
                    self.refresh()

                if self.page == 0:
                    self.step0()

                if self.page in [0, 1]:
                    self.step1()

                if self.page in [0, 1, 2]:
                    self.step2()

                if self.page in [0, 1, 2, 3]:
                    self.step3()

                if self.page in [0, 1, 2, 3, 4]:
                    self.step4()
                    break
            except Exception:
                logger.error(traceback.format_exc())
                try:
                    if not self.driver.title:
                        logger.error(f'第{retries+1}次运行失败，当前页面标题为空')
                    else:
                        logger.error(
                            f'第{retries+1}次运行失败，当前页面标题为：{self.driver.title}')
                except Exception:
                    logger.error(f'第{retries+1}次运行失败，获取当前页面标题失败')

                if retries == 4:
                    self.fail = True
                    logger.error("健康打卡失败")

        self.driver.quit()
        self.notify()

    def refresh(self):
        """刷新页面，直到页面标题不为空

        Raises:
            Exception: 页面刷新次数达到上限
        """
        refresh_times = 0

        while True:
            logger.info('刷新页面')
            self.driver.refresh()

            try:
                self.titlewait.until(
                    EC.presence_of_all_elements_located(
                        (By.TAG_NAME, "title")))
            except Exception:
                pass

            title = self.driver.title

            # Unified Identity Authentication也就是统一身份认证界面
            if title == 'Unified Identity Authentication':
                self.page = 1
            elif title == '融合门户':
                self.page = 2
            elif title == '学生健康状况申报':
                self.page = 3
            elif title in ['填报健康信息 - 学生健康状况申报', '表单填写与审批::加载中']:
                self.page = 4
            elif not title:
                logger.info('当前页面标题为空')

                refresh_times += 1
                if refresh_times < 4:
                    continue
                else:
                    raise Exception("页面刷新次数达到上限")
            else:
                self.page = 0

            break

        logger.info(f'当前页面标题为：{title}')

    def step0(self):
        """转到统一身份认证界面
        """
        logger.info('正在转到统一身份认证页面')
        self.driver.get(
            'https://newcas.gzhu.edu.cn/cas/login?service=https%3A%2F%2Fnewmy.gzhu.edu.cn%2Fup%2Fview%3Fm%3Dup'
        )

    def step1(self):
        """登录融合门户
        """
        self.titlewait.until(
            EC.title_contains("Unified Identity Authentication"))
        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='robot-mag-win small-big-small']")))

        logger.info('正在尝试登陆融合门户')
        for script in [
                f"document.getElementById('un').value='{self.xuhao}'",
                f"document.getElementById('pd').value='{self.mima}'",
                "document.getElementById('index_login_btn').click()"
        ]:
            self.driver.execute_script(script)

    def step2(self):
        """转到学生健康状况申报页面
        """
        self.titlewait.until(EC.title_contains("融合门户"))
        logger.info('正在转到学生健康状况申报页面')
        self.driver.get('https://yqtb.gzhu.edu.cn/infoplus/form/XNYQSB/start')

    def step3(self):
        """转到填报健康信息 - 学生健康状况申报页面
        """
        self.titlewait.until(EC.title_contains("学生健康状况申报"))
        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.ID, "preview_start_button"))).click()

        logger.info('正在转到填报健康信息 - 学生健康状况申报页面')

    def step4(self):
        """填写并提交表单
        """
        self.titlewait.until(EC.title_contains("表单填写与审批::加载中"))
        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@align='right']/input[@type='checkbox']")))

        logger.info('开始填表')

        for xpath in [
                "//div[@align='right']/input[@type='checkbox']",
                "//nobr[contains(text(), '提交')]/.."
        ]:
            self.driver.find_element(By.XPATH, xpath).click()

        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//button[@class='dialog_button default fr']"))).click()

        formErrorContentList = self.driver.find_elements(
            By.XPATH, "//div[@class='line10']")

        for formErrorContent in formErrorContentList:
            button = self.driver.find_elements(
                locate_with(
                    By.XPATH,
                    "//input[@type='radio']").below(formErrorContent))[0]
            self.driver.execute_script("$(arguments[0]).click();", button)

        logger.info('尝试提交表单')
        self.driver.find_element(By.XPATH,
                                 "//nobr[contains(text(), '提交')]/..").click()

        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='form_do_action_error']")))

        message = self.driver.execute_script(
            "return document.getElementsByClassName('form_do_action_error')[0]['textContent']"
        )

        if message == '打卡成功':
            logger.info("健康打卡成功")
        else:
            logger.error(f"弹出框消息不正确，为:{message}")
            logger.error("健康打卡失败")
            self.fail = True

    def notify(self):
        """通知健康打卡成功与失败
        """
        if not self.pushplus:
            if self.fail:
                sys.exit("健康打卡失败")
            else:
                sys.exit()
        else:
            if self.fail:
                title = content = "健康打卡失败"
                logger.info("推送健康打卡失败的消息")
            else:
                title = content = "健康打卡成功"
                logger.info("推送健康打卡成功的消息")

        if self.pushplus:
            data = {"token": self.pushplus, "title": title, "content": content}
            url = "http://www.pushplus.plus/send/"
            logger.info(requests.post(url, data=data).text)


if __name__ == "__main__":
    cl = clockIn()
    cl()
