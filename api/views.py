from django.shortcuts import render
from django.http import HttpResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from .scrape_light import Scraper
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime

options=Options()
# options.add_argument("--disable-extensions")
# options.add_argument("--headless")
api_timeout=20

def getDriver():
    print("Initializing Driver")
    driver=webdriver.Chrome("api/driver/chromedriver.exe",chrome_options=options)
    return driver

def homeView(request,id):
    driver=getDriver()
    try:
        scraper=Scraper(driver,10)
        scraper.init_args("2021-02-06","2021-02-07","DAC","BZL",oneway=False)
        json=scraper.get_flynovair_data()

    finally:

        driver.quit()
        
    return HttpResponse(f"{json}")


@api_view(['POST'])
def flynovoairData(request):
    dep_date,arr_date,dep_code,arr_code,adult,child,infant,oneway=get_args(request)
    scraper=Scraper('driver',10)
    scraper.init_args(
        dep_date=dep_date,
        arr_date=arr_date,
        dep_code=dep_code,
        arr_code=arr_code,
        adult=adult,
        child=child,
        infant=infant,
        oneway=oneway    
    )
    try:
        json=scraper.get_flynovair_data()
    except Exception as e:
        return Response({"error":str(e)})

    return Response(json)



@api_view(['POST'])
def getAllData(request):

    driver=getDriver()
    
    try:
        
        dep_date,arr_date,dep_code,arr_code,adult,child,infant,oneway=get_args(request)
        scraper=Scraper(driver,api_timeout)
        scraper.init_args(
            dep_date=dep_date,
            arr_date=arr_date,
            dep_code=dep_code,
            arr_code=arr_code,
            adult=adult,
            child=child,
            infant=infant,
            oneway=oneway    
        )

        json=scraper.getAllData()

    except Exception as e:
        return {"Error":str(e)}
    finally:
        driver.quit()

    return Response(json)



@api_view(['POST'])
def usbairData(request):

    driver=getDriver()
    try:
        
        dep_date,arr_date,dep_code,arr_code,adult,child,infant,oneway=get_args(request)
        scraper=Scraper(driver,api_timeout)
        scraper.init_args(
            dep_date=dep_date,
            arr_date=arr_date,
            dep_code=dep_code,
            arr_code=arr_code,
            adult=adult,
            child=child,
            infant=infant,
            oneway=oneway    
        )

        json=scraper.get_usbair_data()

    except Exception as e:
        return {"Error":str(e)}

    finally:

        driver.quit()

    return Response(json)



def getBoolfStr(str):

    if str.lower() in ["false","null","none","0","no"]:
        return False
    return True

def get_args(post):
    

    dep_date=post.data.get("departure_date",None)
    arr_date=post.data.get("arrival_date",'')

    if dep_date is None:
        today_date=datetime.date.today()

        dep_date=today_date.strftime("%Y-%m-%d")
        arr_date=(today_date+datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    dep_code=post.data.get("departure_code")
    arr_code=post.data.get("arrival_code")
    adult=post.data.get("adult",1)
    child=post.data.get("child",0)
    infant=post.data.get("infant",0)
    oneway=post.data.get("oneway",'False')
    oneway=getBoolfStr(oneway)

    return (dep_date,arr_date,dep_code,arr_code,adult,child,infant,oneway)