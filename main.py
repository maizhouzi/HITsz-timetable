# coding=utf-8

from interface import cmdInput, config, icalOutput
from excelParser import ProcessExcel
from crawler import excelCrawler

import click
import random
import logging
import time
import misc
import datetime
# import genIcs


def main():

    def wait_a_minute(prompt, extra_minutes=0):
        wait = 60 * extra_minutes + random.randint(0, 60)
        logging.warning(prompt.format(wait))
        time.sleep(wait)
    r = excelCrawler.Report(proxy_on=1, ports=[1080, 2080])
    form_url, form_inputs = r.get_text()
    form_url, form_inputs = r.login(form_url, form_inputs)
    excelCrawler.login(form_url, form_inputs)
    excelRawBytes = excelCrawler.getExcelRawData()

    cal_name, cal_data = ProcessExcel.process(excelRawBytes)
    cal_name = "你的课表"
    icalOutput.output(cal_name, cal_data)

    try:
        r.student_login()
    except excelCrawler.ReportException.LoginError:
        wait_a_minute("登录失败，将在 {} 秒后重试。", 1)
        r.login()
    except Exception as err:
        if r.proxy_on:
            logging.error(err)
            wait_a_minute("开启代理，将在 {} 秒后重试。")
            r.switch_proxies(r.student_login)
        else:
            raise err


@click.command()
@click.option('--username', '-u', help="Username")
@click.option('--password',
              '-p',
              help="Password",
              hide_input=True,
              prompt="Enter Password")
@click.option(
    '--filepath',
    '-f',
    help=
    "ics file path to be written. If not specified, contents will be written to stdout"
)
@click.option('-y', type=int, help="Date of 1st Monday of the 1st week: year")
@click.option('-m', type=int, help="Date of 1st Monday of the 1st week: month")
@click.option('-d', type=int, help="Date of 1st Monday of the 1st week: day")
@click.option(
    '--stdout',
    help=
    "Write iCalendar file content to stdout, this will override --filepath option",
    is_flag=True)



def execute(username, password, filepath, y, m, d, stdout):
    cmdInput.parseLoginParams(username, password)
    cmdInput.parseStartDate(y, m, d)
    cmdInput.parseOutputTarget(filepath, stdout)
    main()


if __name__ == "__main__":
    execute()