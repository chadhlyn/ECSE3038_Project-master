from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
import re
import requests
import datetime
import pydantic
import motor.motor_asyncio
import pytz

app = FastAPI()

origins = [
    "https://simple-smart-hub-client.netlify.app",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://horatiolyn:OeFONgBIzKZl69Ma@cluster0.zq6zvbv.mongodb.net/?retryWrites=true&w=majority")
db = client.sshub
sensor_data = db['sensor_data']
update = db['update']


def get_sunset_time():

    sunset_api_endpoint = f'https://api.sunrise-sunset.org/json?lat=18.0092&lng=-76.7495'

    sunset_api_response = requests.get(sunset_api_endpoint)
    sunset_api_data = sunset_api_response.json()

    sunset_time = datetime.datetime.strptime(sunset_api_data['results']['sunset'], '%I:%M:%S %p')+timedelta(hours=-5)
    sunset_time = sunset_time.time()
    return datetime.datetime.strptime(str(sunset_time), "%H:%M:%S")

regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)

@app.get("/")
async def home():
    return {"message": "ECSE3038 - Project"}

@app.get('/graph')
async def graph(request: Request):
    size = int(request.query_params.get('size'))
    readings = await update.find().sort('_id', -1).limit(size).to_list(size)
    data_info = []
    for reading in readings:
        temperature = reading.get("temperature")
        presence = reading.get("presence")
        current_time = reading.get("current_time")

        data_info.append({
            "temperature": temperature,
            "presence": presence,
            "datetime": current_time
        })

    return data_info

@app.put('/settings')
async def update_settings(request: Request):
    state = await request.json()
    user_temp = state["user_temp"]
    user_light = state["user_light"]
    light_time_off = state["light_duration"]

    if user_light == "sunset":
        user_light_scr = get_sunset_time()
    else:
        user_light_scr = datetime.datetime.strptime(user_light, "%H:%M:%S")

    new_user_light = user_light_scr + parse_time(light_time_off)

    output = {
        "user_temp": user_temp,
        "user_light": str(user_light_scr.time()),
        "light_time_off": str(new_user_light.time())
    }

    obj = await sensor_data.find().sort('_id', -1).limit(1).to_list(1)

    if obj:
        await sensor_data.update_one({"_id": obj[0]["_id"]}, {"$set": output})
        new_obj = await sensor_data.find_one({"_id": obj[0]["_id"]})
    else:
        new = await sensor_data.insert_one(output)
        new_obj = await sensor_data.find_one({"_id": new.inserted_id})
    return new_obj

@app.post("/temperature")
async def update_temperature(request: Request):
    state = await request.json()
    param = await sensor_data.find().sort('_id', -1).limit(1).to_list(1)

    if param:
        temperature = param[0]["user_temp"]
        user_light = datetime.datetime.strptime(param[0]["user_light"], "%H:%M:%S")
        time_off = datetime.datetime.strptime(param[0]["light_time_off"], "%H:%M:%S")
    else:
        temperature = 28
        user_light = datetime.datetime.strptime("18:00:00", "%H:%M:%S")
        time_off = datetime.datetime.strptime("20:00:00", "%H:%M:%S")

    now_time = datetime.datetime.now(pytz.timezone('Jamaica')).time()
    current_time = datetime.datetime.strptime(str(now_time), "%H:%M:%S.%f")

    state["light"] = ((current_time < user_light) and (current_time < time_off) and (state["presence"] == 1))
    state["fan"] = ((float(state["temperature"]) >= temperature) and (state["presence"] == 1))
    state["current_time"] = str(datetime.datetime.now())

    new_settings = await update.insert_one(state)
    new_obj = await update.find_one({"_id": new_settings.inserted_id})
    return new_obj

@app.get("/state")
async def get_state():
    last_entry = await update.find().sort('_id', -1).limit(1).to_list(1)

    if not last_entry:
        return {
            "presence": False,
            "fan": False,
            "light": False,
            "current_time": datetime.datetime.now()
        }

    return last_entry
