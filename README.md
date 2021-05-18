# Cowin4All 

Simple automation to automate the booking of vaccine slot in CoWin.

## 1 Setup
1. Clone this repo and traverse to the code directory
    ```shell
   git clone git@github.com:rams3sh/cowin4all.git && cd cowin4all
   ```
   
2. Create a virtual environment
    ```shell
    python3 -m virtualenv env
    ````
3. Install the package requirements
    ```shell
   pip3 install -r requirements.txt 
   ```

## 2. Usage

Below snippet should give you an idea of using the cowin4all SDK.

```python3
from threading import Thread
import logging
import random
import time
import os

from lib.api import APIClient
from lib.utils import get_applicable_sessions, get_captcha_input_manually

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Below data are dummy. Refer lib/constants.py for the applicable values for each variable below.
mobile_number = 1234567890
beneficiary_ids = [1234567, 12345678, 8765432, 123456789]
age = 18
dose = 1
district_ids = 123456 # Using district then filtering the pincodes further to filter will reduce network calls
pin_codes = [600035, 600006]
dates = ["18-05-2021", "19-05-2021", "20-05-2021", "21-05-2021"] 
vaccine_type = "covishield"
payment_type = "any"


# Other Settings
poll_time_range = (15.0, 20.0) 

# Very Linux specific. My system has cvlc , hence used it. You might have to reconsider using the command.

def play_sound(file_path):
        os.system("cvlc {} --play-and-exit".format(file_path))


        
def booking_alert(count=None):
    siren = Thread(target=play_sound, args=["resources/Siren-SoundBible.com-1094437108.mp3",], daemon=True)
    siren.start()
    
    
def auto_book():
    global pin_codes, vaccine_type, payment_type, dose, age, dates
    client = APIClient(mobile_no=mobile_number)
    while True:
        try:
            logger.info("Polling ...")
            client.get_beneficiaries()
            centres = get_applicable_sessions(client=client, district_ids=district_ids,
                                              vaccine_type=vaccine_type,
                                              payment_type=payment_type, dose=dose, age=age, dates=dates)
            temp_centres = {}
            for centre in centres:
                if centres[centre]["pin_code"] in pin_codes:
                    temp_centres.update({centre: centres[centre]})
            centres = temp_centres
            logger.info("Available centres:{}".format(centres))
            if centres:
                logger.info("Some centres found !!")
                for centre in centres:
                    for session in centres[centre]["sessions"]:
                        if session["available_capacity_dose{}".format(dose)] < len(beneficiary_ids):
                            logger.info("Available slots for dose {} : {} is less than the number of beneficiary !!"
                                         "".format(dose, session["available_capacity_dose{}".format(dose)]))
                            continue
                        booking_alert(3)
                        # for slot in session["slots"]: slot is not important for consideration
                        slot = session["slots"][-1]
                        c = client.get_captcha()
                        captcha = get_captcha_input_manually(captcha=c, client=client)
                        appointment_id = None
                        try:
                            appointment_id = client.schedule_booking(beneficiaries=beneficiary_ids,
                                                                     session_id=session["session_id"],
                                                                     captcha=captcha,
                                                                     dose_number=dose,
                                                                     center_id=centre,
                                                                     slot=slot)
                        except Exception as e:
                            appointment_id = None
                        if not appointment_id:
                            continue
                        path = client.download_confirmation(appointment_id=appointment_id,
                                                            destination_file_path="confirmation.pdf")
                        logger.info("Successfully Booked!!  Confirmation form is available at {}!!".format(path))
                        return
        except Exception as e:
            logger.error(e)
            client.auto_refresh_token_retries_attempted = 0
        time.sleep(random.uniform(poll_time_range[0], poll_time_range[1]))
```


## 3. Custom OTP Retrieval method plugin

The SDK supports external pluggable otp_retrieval_method. This is to support faster retrieval OTP mechanisms.

One possible method is to install an app that can forward an SMS to a webhook and the webhook can fixate the OTP 
back in your workflow. Below pseduo snippet based on FastAPI library should give an idea on how that can be done.

```python
def otp_alert(sleep=10):
    global otp_alert_running, otp

    def wait_and_alert():
        global otp_alert_running
        logger.info("Waiting for alerting the user for OTP in case not received !!")
        time.sleep(10)
        if otp:
            otp_alert_running = False
            return
        else:
            play_sound("resources/refresh_OTP.mp3")

    if not otp_alert_running:
        otp_alert_running = True
        alert = Thread(target=wait_and_alert, daemon=True)
        alert.start()
    else:
        return
    
def get_otp(client=None):
    global otp_wait, otp, logger
    otp = None
    logger.info("Waiting for OTP !! ")
    otp_alert(sleep=10)
    otp_wait.wait()  # Waited for SMS to be hit on below webhook
    otp_wait.clear()
    logger.info("OTP Received: "+str(otp))
    return otp

@app.put("/put_otp")
async def put_otp(request: Request):
    global otp_wait, otp
    body = await request.json()
    logger.info("Received SMS: " + str(body))
    if body["from"] == "AX-NHPSMS":
        match = re.findall("(?<=CoWIN is )[0-9]{6}", body["message"])
        if match:
            otp = match[0]
            otp_wait.set()

client = APIClient(mobile_no=mobile_number, 
                   otp_retrieval_method=get_otp,  # Custom OTP method
                   auto_refresh_token=True, # This ensures the token is auto-refreshed once token expires
                   auto_refresh_retries_count=3)


```
The above snippet if from my internal app which uses beautiful app from [ushahidi](https://github.com/ushahidi/SMSSync/).

One can setup a simpleweb server and expose it to public / local network and configure the above mentioned app to 
forward the SMS from CoWIN to the hosted web api. This ensures that OTP gets automatically fed without much effort.

This idea was inspired from the earlier code opensourced by [bombardier-gif](https://github.com/bombardier-gif/covid-vaccine-booking)].

This code base differs from the other code in terms of auto-refresh and pluggable module support of the base code.

The ideas are limitless in terms of how an input can be retrieved.

The OTP can be fed into a telegram bot by the user manually and bot can feed it back to the auto book system. 
Same case for captchas as well. 


## 4. Thanks to

1. [ushahidi](https://github.com/ushahidi/SMSSync/) for the wonderfull SMS gateway app. 
   This is way more efficient than IFTTT in terms of customisation. Also good part is , it is open source.

   
2. Couple of people who worked on earlier version of automation of various cowinibooking apps.

    i. [pallupz](https://github.com/pallupz/covid-vaccine-booking)
   
   ii. [bombardier-gif](https://github.com/bombardier-gif/covid-vaccine-booking)


## 5. Please donate

If you like this project. Kindly donate to [TN CM Public Relief Fund](https://ereceipt.tn.gov.in/Cmprf/Cmprf)
