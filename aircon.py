import sys
import RPi.GPIO as GPIO
import time
import requests
import json
import ipget
import concurrent.futures

SERVER = ""
URL = SERVER + "/api/ducrbcontrol/airconditioner/"
DEV_UCODE = ""
HEADERS = {'Content-type': 'application/json'}
INTERVAL = 0.001
ANODE_COMMON = False 
AIRCON_ID = 0
POWER_MODE = 0
TEMP = 0
FAN_SPEED = 0
MIN_TEMP = 20
MAX_TEMP = 35
DISPLAY_STRING = ""
AIRCON_SELECT = 0
ROOM = ""
AIRCON_ID_1 = 0
AIRCON_ID_2 = 0

GPIO.setmode(GPIO.BCM)

class GpioOutputPin:

    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(pin, GPIO.OUT)

    def on(self):
        if ANODE_COMMON:
            GPIO.output(self.pin, GPIO.LOW)
        else:
            GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        if ANODE_COMMON:
            GPIO.output(self.pin, GPIO.HIGH)
        else:
            GPIO.output(self.pin, GPIO.LOW)

class GpioInputPin:

    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def pin(self):
        return self.pin

class PutData:

    def __init__(self, settingBit):
        self.data = {
            'id': AIRCON_ID,
            'setting_bit': settingBit,
            'on_off': 0,
            'operation_mode': 0,
            'ventilation_mode': 0,
            'ventilation_amount': 0,
            'set_point': 0,
            'fan_speed': 0,
            'fan_direction': 0,
            'filter_sign_reset': 0
        }

    def data(self):
        return self.data

# GPIO ports for 8-segment LED pins
TOP = GpioOutputPin(11)
CENTER = GpioOutputPin(18)
BOTTOM = GpioOutputPin(8)
LEFT_UPPER = GpioOutputPin(10)
LEFT_LOWER = GpioOutputPin(7)
RIGHT_UPPER = GpioOutputPin(14)
RIGHT_LOWER = GpioOutputPin(23)
DOT = GpioOutputPin(25)

AIRCON_SELECT_LED1 = GpioOutputPin(6)
AIRCON_SELECT_LED2 = GpioOutputPin(13)

# GPIO ports for Button pins
POWER_BUTTON = GpioInputPin(21)
TEMP_UP_BUTTON = GpioInputPin(20)
TEMP_DOWN_BUTTON = GpioInputPin(19)
FAN_SPEED_BUTTON = GpioInputPin(26)
AIRCON_SELECT_BUTTON = GpioInputPin(16)

# GPIO ports for digit pins
DIGITS = (
    GpioOutputPin(22),  # the most left side
    GpioOutputPin(27),
    GpioOutputPin(17),
    GpioOutputPin(24),  # the most right side
)

class SegmentPattern:
    LIGHT_ON = 1
    LIGHT_OFF = 0
    SEGMENTS = (TOP, RIGHT_UPPER, RIGHT_LOWER, BOTTOM,
                LEFT_LOWER, LEFT_UPPER, CENTER, DOT)

    def __init__(self, *lights):
        self.lights = lights

    def display(self):
        for segment, light in zip(self.SEGMENTS, self.lights):
            if light == self.LIGHT_ON:
                segment.on()
            else:
                segment.off()

NUMBERS = {
    ' ': SegmentPattern(0, 0, 0, 0, 0, 0, 0, 0),
    '0': SegmentPattern(1, 1, 1, 1, 1, 1, 0, 0),
    '1': SegmentPattern(0, 1, 1, 0, 0, 0, 0, 0),
    '2': SegmentPattern(1, 1, 0, 1, 1, 0, 1, 0),
    '3': SegmentPattern(1, 1, 1, 1, 0, 0, 1, 0),
    '4': SegmentPattern(0, 1, 1, 0, 0, 1, 1, 0),
    '5': SegmentPattern(1, 0, 1, 1, 0, 1, 1, 0),
    '6': SegmentPattern(1, 0, 1, 1, 1, 1, 1, 0),
    '7': SegmentPattern(1, 1, 1, 0, 0, 0, 0, 0),
    '8': SegmentPattern(1, 1, 1, 1, 1, 1, 1, 0),
    '9': SegmentPattern(1, 1, 1, 1, 0, 1, 1, 0),
    'P': SegmentPattern(1, 1, 0, 0, 1, 1, 1, 0),
}

def postRaspberrypiIpaddress():
    url = SERVER + "/api/raspberrypi/ipaddress/"
    ip = ipget.ipget()
    ipaddress = ip.ipaddr("wlan0")

    data = {
        "dev_ucode": DEV_UCODE,
        "ip": ipaddress
    }

    try:
        conn = requests.post(url=url, data=json.dumps(data), headers=HEADERS, timeout=30.0)
    except:
        time.sleep(10)
        postRaspiIpaddress()

def httpPut(data):
    req = requests.put(url=URL, data=json.dumps(data), headers=HEADERS, auth=('ducrb', 'daiwaubiquitous'))
    return req.status_code

def httpGet():
    url = URL + str(AIRCON_ID) + "/"
    req = requests.get(url, auth=('ducrb', 'daiwaubiquitous'))
    if str(req.status_code) != "200":
        return req.status_code

    # Setting LCDBorad DISPLAY_STRING
    global POWER_MODE
    global TEMP
    global FAN_SPEED
    data = req.json()

    if type(data) == dict:
        POWER_MODE = int(data["on_off"])
        TEMP = int(str(data["set_temp"])[:2])
        if data["fan_speed"] != -1:
            FAN_SPEED = data["fan_speed"]
    elif type(data) == list:
        POWER_MODE = int(data[0]["on_off"])
        TEMP = int(str(data[0]["set_temp"])[:2])
        if data[0]["fan_speed"] != -1:
            FAN_SPEED = data[0]["fan_speed"]
    displayString()
    return req.status_code

def getTime():
    now = time.strftime('%I%M')
    return now

def changePowerMode(mode):
    putData = PutData(1)
    putData.data["on_off"] = mode
    return httpPut(putData.data)

def changeTempValue(temp):
    putData = PutData(16)
    putData.data["set_point"] = temp
    return httpPut(putData.data)

def changeFanSpeed(speed):
    putData = PutData(32)
    putData.data["fan_speed"] = speed
    return httpPut(putData.data)

def powerButton(self):
    #print("PUSH POWER BUTTON")
    global POWER_MODE
    if (POWER_MODE == 0):
        if str(changePowerMode(1)) == "204":
            httpGet()
            POWER_MODE = 1
            #print("CHANGE POWER ON")
    else:
        if str(changePowerMode(0)) == "204":
            POWER_MODE = 0
            #print("CHANGE POWER OFF")

def powerMode():
    if POWER_MODE == 1:
        return True
    else:
        return False

def displayString():
    global DISPLAY_STRING
    DISPLAY_STRING = str(TEMP) + "P" + str(FAN_SPEED)

def changeTempUpButton(self):
    if not powerMode():
        return
    #print("PUSH TEMP UP BUTTON")
    global TEMP
    if not TEMP < MAX_TEMP:
        return
    TEMP += 1
    if str(changeTempValue(TEMP)) == "204":
        displayString()
        #print("TEMP UP: " + str(TEMP))

def changeTempDownButton(self):
    if not powerMode():
        return
    #print("PUSH TEMP DOWN BUTTON")
    global TEMP
    if not TEMP > MIN_TEMP:
        return
    TEMP -= 1
    if str(changeTempValue(TEMP)) == "204":
        displayString()
        #print("TEMP DOWN: " + str(TEMP))

def changeFanSpeedButton(self):
    if not powerMode():
        return
    #print("PUSH CHANGE FAN BUTTON")
    global FAN_SPEED
    if FAN_SPEED == 2:
        FAN_SPEED = 0
    else:
        FAN_SPEED += 1
    if str(changeFanSpeed(FAN_SPEED)) == "204":
        displayString()
        #print("CHANGE FAN SPEED: " + str(FAN_SPEED))

def changeAirconSelectButton(self):
    global AIRCON_SELECT
    global AIRCON_ID
    if AIRCON_SELECT < 2:
        AIRCON_SELECT += 1
    else:
        AIRCON_SELECT = 0
    airconSelect()

def airconSelect():
    global AIRCON_ID
    if AIRCON_SELECT == 0:
        AIRCON_ID = ROOM
        AIRCON_SELECT_LED1.on()
        AIRCON_SELECT_LED2.on()
    elif AIRCON_SELECT == 1:
        AIRCON_ID = AIRCON_ID_1
        AIRCON_SELECT_LED1.on()
        AIRCON_SELECT_LED2.off()
    else:
        AIRCON_ID = AIRCON_ID_2
        AIRCON_SELECT_LED1.off()
        AIRCON_SELECT_LED2.on()
    httpGet()

def display():
    global DISPLAY_STRING
    while True:
        if POWER_MODE == 0:
            DISPLAY_STRING = "    "

        for digit, number in zip(DIGITS, DISPLAY_STRING):
            NUMBERS[number].display()
            digit.off()
            time.sleep(INTERVAL)
            digit.on()

def httpGetSleep():
    while True:
        httpGet()
        time.sleep(120)

def event():
    GPIO.add_event_detect(POWER_BUTTON.pin, GPIO.FALLING, callback=powerButton, bouncetime=2000)
    GPIO.add_event_detect(TEMP_UP_BUTTON.pin, GPIO.FALLING, callback=changeTempUpButton, bouncetime=500)
    GPIO.add_event_detect(TEMP_DOWN_BUTTON.pin, GPIO.FALLING, callback=changeTempDownButton, bouncetime=500)
    GPIO.add_event_detect(FAN_SPEED_BUTTON.pin, GPIO.FALLING, callback=changeFanSpeedButton, bouncetime=500)
    GPIO.add_event_detect(AIRCON_SELECT_BUTTON.pin, GPIO.FALLING, callback=changeAirconSelectButton, bouncetime=1000)

def main():
    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        postRaspberrypiIpaddress()
        event()
        airconSelect()
        executor.submit(httpGetSleep)
        display()
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
