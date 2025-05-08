import requests
import pytz
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
import json

load_dotenv()

ALERTZY_DOMAIN = os.getenv("ALERTZY_DOMAIN")
TRANSIT_DOMAIN =  os.getenv("TRANSIT_DOMAIN")
ALERTZY_API_KEY = os.getenv("ALERTZY_API_KEY")
TRANSIT_API_KEY = os.getenv("TRANSIT_API_KEY")
    
def ms_to_datetime(ms):
    
    utc = datetime.fromtimestamp(ms / 1000)
    est = pytz.timezone('US/EASTERN')
    est_time = utc.astimezone(est).strftime("%H:%M")
    
    return est_time

def seconds_to_readable(sec):
    mins = sec // 60
    return f"{mins} min {sec % 60} sec"

def fethArriveByTime(jsonSettingsObject):
    
    today = datetime.now(ZoneInfo("America/Toronto")).strftime("%A")

    est_time_str = jsonSettingsObject["schedule"][today]
    
    if est_time_str == None:
        return None

 
    est_datetime = datetime.strptime(
        f"{datetime.now().strftime('%Y-%m-%d')} {est_time_str}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/Toronto"))

 
    utc_time = est_datetime.astimezone(ZoneInfo("UTC"))

    return utc_time.strftime("%H:%M") 
    
def getTransitApiData(route,payload):
    headers = {'apiKey': TRANSIT_API_KEY}
    result = requests.get(f'{TRANSIT_DOMAIN}/{route}', params=payload, headers=headers)
    return result.json()

def fethTripData():
    
    arriveByTime = fethArriveByTime(settings)
    
    if arriveByTime == None :
        return
    
    rawTripData = getTransitApiData(
        "/otp/plan", {
                "fromPlace": settings["coordinates"]["from"],
                "toPlace": settings["coordinates"]["to"],
                "numItineraries": 3,
                "mode": "TRANSIT",
                "arriveBy": "true",
                "date" : datetime.now().strftime('%Y-%m-%d'),
                "time": arriveByTime
            }
        )["plan"]["itineraries"]

    finalTripData = []
    seen_routes = set()

    for trip in rawTripData:
        
        route_number = trip["legs"][1]["routeShortName"]

        if route_number not in seen_routes:
            seen_routes.add(route_number)

            finalTripData.append({
                "duration": seconds_to_readable(trip["duration"]),
                "departure": ms_to_datetime(trip["startTime"]),
                "arrival": ms_to_datetime(trip["endTime"]),
                "bus": {
                    "name": trip["legs"][1]["routeLongName"],
                    "number": route_number,
                    "direction": trip["legs"][1]["headsign"],
                    "time": ms_to_datetime(trip["legs"][1]["startTime"]),
                    "stop": trip["legs"][1]["from"]["name"]
                }
            })

    sortedTripData = sorted(finalTripData, key=lambda x: x["duration"])
    
    return sortedTripData
    
def sendAlert(title,message,priority):
    
    result = requests.get(
        ALERTZY_DOMAIN , params={
            "accountKey" : ALERTZY_API_KEY,
            "title" : title,
            "message" : message,
            "priority" : priority
            }
        )
    
    return result.json()

def buildAllItenarariesMessage(rawTrips):
    message = ""
    for trip in rawTrips:
        message += (
            f"🚌 {trip['bus']['number']} {trip['bus']['name']} → {trip['bus']['direction']}\n"
            f"📍 Stop: {trip['bus']['stop']}\n"
            f"⏰ Bus @ {trip['bus']['time']}\n"
            f"🏃‍♂️ Leave home @ {trip['departure']}\n"
            f"🎯 ETA: {trip['arrival']} ({trip['duration']})\n\n"
        )
    return message

with open(r"./schedule.json", 'r', encoding='utf-8') as file:
    settings = json.load(file)
    
sendAlert("🚨 School Bus Alert",buildAllItenarariesMessage(fethTripData()),2)







