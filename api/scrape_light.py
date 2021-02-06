from selenium import webdriver
from string import Template
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import json
from selenium.webdriver.chrome.options import Options
import requests
import datetime


class Scraper:
    def __init__(self,driver,timeout=5):
        self.driver=driver
        self.usbair_url="https://www.usbair.com"
        self.timeout=timeout
        self.flynovoair_url="https://secure.flynovoair.com/bookings/Vues/flight_selection.aspx?ajax=true&action=flightSearch"    


    def init_args(self,dep_date,arr_date,dep_code,arr_code,currency="BDT",adult=1,child=0,infant=0,oneway=True):

        self.dep_date=self.get_valid_date(dep_date)
        self.arr_date=self.get_valid_date(arr_date)

        self.dep_city=dep_code
        self.arr_city=arr_code
        self.ad_num=adult
        self.currency=currency
        self.child_num=child
        self.infant_num=infant
        self.oneway=oneway

        print("Initialised Variables")
    def get_function(self,dep_date,arr_date,dep_city="DAC",arr_city="BZL",currency="INR",ad_num=1,child_num=0,infant_num=0):

        getFun="""function getSpecialFareURL()
        {

            var departureDate = '$dep_date';
            var arrivalDate = '$arr_date';
            var departureCity= '$dep_city';
            var arrivalCity = '$arr_city';
            var currency= '$currency'
            var AdultNumber= '$ad_num';
            var ChildNumber='$child_num';
            var InfantNumber='$inf_num';


            var URL = 'https://fo-asia.ttinteractive.com/Zenith/FrontOffice/usbangla/en-GB/BookingEngine/SearchResult?OutboundDate=';
            
            URL = $url
            URL = URL+'&Currency='+currency+'&TravelerTypes[0].Key=AD&TravelerTypes[0].Value='+AdultNumber;
            URL = URL+'&TravelerTypes[1].Key=CHD&TravelerTypes[1].Value='+ChildNumber+'&TravelerTypes[2].Key=INF&TravelerTypes[2].Value='+InfantNumber;

            window.location = URL;

            return URL;
        }"""

        if self.oneway:
            url="""URL+departureDate+'&OriginAirportCode='+departureCity+'&DestinationAirportCode='+arrivalCity;"""
        else:
            url="""URL+departureDate+'&InboundDate='+arrivalDate+'&OriginAirportCode='+departureCity+'&DestinationAirportCode='+arrivalCity;"""
        
        temp=Template(getFun)
        args={'dep_date':dep_date,'arr_date':arr_date,'dep_city':dep_city,'arr_city':arr_city,'currency':currency,'ad_num':ad_num,'child_num':child_num,'inf_num':infant_num,'url':url}
        
        return temp.substitute(args)

    def get_valid_date(self,date):
        date_chunks=[]
        for chunk in date.split("-"):
            if len(chunk)==1:
                chunk="0"+chunk
            date_chunks.append(chunk)
        return '-'.join(date_chunks)

    
    def parse_data(self,data_str):
        lines=data_str.split("\n")
        data={}
        for line in lines:
            line_split=line.split(":")
            data[line_split[0].strip()]=line_split[1].strip()
        
        return data

    def get_flynovair_data(self):
        oneway=self.oneway

        error=self.validate_date(self.dep_date,self.arr_date,self.oneway)

        # if CONTAINS no error it will not enter 
        if error is not False:
            return error


        TT="OW" if self.oneway else "RT"
        DC=self.dep_city
        AC=self.arr_city
        DDATE=self.dep_date.split("-")  # Departure Date "2020-02-02".split("-")
       
        DM='-'.join(DDATE[:-1]) #'-'.join(["2020","02"])
        DD=DDATE[-1] # "02"

        if not self.oneway:
            ADATE=self.arr_date.split("-") # Arrival Date "2020-02-02".split("-")
            RM='-'.join(ADATE[:-1]) #Return Month
            RD=ADATE[-1]
        else:
            RM=''
            RD=''

        PA=self.ad_num
        PC=self.child_num
        PI=self.infant_num


        params_str=f"""SS: 
                            RT: 
                            FL: on
                            TT: {TT}
                            DC: {DC}
                            AC: {AC}
                            AM: {DM}
                            AD: {DD}
                            RM:{RM}
                            RD: {RD}
                            CC: 
                            CR: 
                            NS: false
                            PA: {PA}
                            PC: {PC}
                            PI: {PI}
                            CX: 
                            CD: 
                            RF: 2"""
    
        params=self.parse_data(params_str)
        resp=requests.post(self.flynovoair_url,data=params)
        
        data=resp.json()
        print(data)
        # pdb.set_trace()
        flights={}
        fareFamily={}
        try:
            for fm in data['flightSelections']['fareFamilies']:
                fareFamily[fm['code']]=fm['name']

            for trip in data['flightSelections']['flightBlocks']:
                currency=data['flightSelections']['currency']['code']
                
                spec_date=trip['date']
                for flightDate in trip['flightDates']:
                    if spec_date==flightDate['date']:
                        for flight_info in flightDate['flights']:
        #                     print(flightDate)
                            for flight in flight_info["itinerary"]:
                #                 print(flight)
                                price_info={}
                                for family,prices in flight_info['familyFares'].items():
                                    family=fareFamily.get(family,family)
                                    price_info[family]=prices['one']

                                takeoff_time=flight['TOD'].split("T")[-1]
                                landing_time=flight['TOA'].split("T")[-1]

                                flights[flight['flight']]={'prices':price_info,
                                                        'TOD':flight['TOD'],
                                                        'TOA':flight['TOA'],
                                                        'from':trip['from'],
                                                        'into':trip['into'],
                                                        'currency':currency,
                                                        "take_off":takeoff_time,
                                                        "landing":landing_time}

                #                 print(price_info)

                #             print(flight_info)

                        break
                
                if oneway:
                    break
            
            return flights

        except Exception as e:
            return data

    def validate_date(self,dep_date,arr_date,oneway):
          # print("Page Loaded 1")
        
        try:
            departure_date=datetime.datetime.strptime(dep_date,"%Y-%m-%d").date()
        except ValueError as e:
            return {"Error":"The departure date format is not valid"}


        if not (departure_date>=datetime.date.today()):
            return {"Error":"The departure date is not valid"}

        if not self.oneway:
            try:
                
                after_date=datetime.datetime.strptime(self.arr_date,"%Y-%m-%d").date()
                before_date=datetime.datetime.strptime(self.dep_date,"%Y-%m-%d").date()
            
                if after_date<before_date:
                    return {"Error":"The arrival date is not valid"}
                    
            except ValueError as e:
                                
                return {"Error":"The dates are not valid"}
        return False


    def get_usbair_data(self):
        driver=self.driver
        # self.driver.get(self.usbair_url)
        error=self.validate_date(self.dep_date,self.arr_date,self.oneway)

        if error is not False:
            return error

        func_to_override=self.get_function(dep_date=self.dep_date,arr_date=self.arr_date,
                                            dep_city=self.dep_city,arr_city=self.arr_city,
                                            currency=self.currency,ad_num= self.ad_num,child_num= self.child_num,
                                         infant_num=self.infant_num)

        # if self.oneway:
        #     pre_script="document.getElementById('oneway').checked=true;"
        # else:
        #     pre_script="document.getElementById('oneway').checked=false;"

        driver.execute_script("""
                                window.getSpecialFareURL={0}
                                getSpecialFareURL();""".format(func_to_override))
        # driver.execute_script(""""")

        try:
            element_present = EC.presence_of_element_located((By.CSS_SELECTOR, 'li.flight'))
            WebDriverWait(driver, self.timeout).until(element_present)

        except TimeoutException:
        
            return {"error":"Flights not found"}
        
        print("PAGE Loaded 2")
        html=driver.page_source
        soup=BeautifulSoup(html,'html.parser')

        flights={}
        for flight in soup.findAll("li",class_='flight'):

            flight_prices=flight.select(".PriceFlight")[0].select('.select-classe')
            # prices=[]

            prices={}

            # currency=None

            for price in flight_prices:
                price_type=price.select(".hidden-lg.visible-md.visible-sm.visible-xs")[0]

                text=price.select(".montant")[0].getText()
                comps=text.strip().split(" ")
                price=comps[0].strip()

    
                currency=comps[-1].strip()

                Ffamily=price_type.text.strip()
                prices[Ffamily]=price
                # prices.append(price_info)

            travel={}
            travel_dep_row=flight.select('.InfoFlight')
            from_,time1=travel_dep_row[0].select(".departure")
            to_,time2=travel_dep_row[0].select(".arrival")
            travel["take_off"]=time1.getText().strip()
            travel["landing"]=time2.getText().strip()
            travel["from"]=from_.getText().strip()
            travel["into"]=to_.getText().strip()

            flight_number=flight.select(".flight-number")[0].getText().strip()

            flights[flight_number]={'prices':prices,**travel,"currency":currency}

            
        return flights

    def getAllData(self):
        usbair_data=self.get_usbair_data()
        flynovoair_data=self.get_flynovair_data()

        return {"usbair":usbair_data,"flynovoair":flynovoair_data}


    def save_json_data(self,usbair_filename,flyon_filename):
        try:
            usbair_data=json.dumps(self.get_usbair_data())

            with open(usbair_filename,"w") as f:
                f.write(usbair_data)
        except Exception as e:
            print("Something is wrong with usbair.com")
            print(f"The error is {e}")

        try:
            flyonvair_data=json.dumps(self.get_flynovair_data())

            with open(flyon_filename,"w") as f:
                f.write(flyonvair_data)

        except Exception as e:
            print("Something is wrong with flyonvair website")
            print(f"The error is {e}")

        self.driver.quit()
        # self.driver.quit()