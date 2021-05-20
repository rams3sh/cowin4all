from threading import Thread
import threading
import time
import logging
import random
import os

from cowin4all_sdk.api import APIClient
from cowin4all_sdk.utils import get_applicable_sessions, get_captcha_input_manually
from cowin4all_app.utils import get_api_service_context

###### CUSTOM METHODS ##########


def get_otp(client=None):
    global otp_wait, otp, logger
    otp = None
    logger.info("Waiting for OTP !! ")
    otp_alert(sleep=10)
    otp_wait.wait()
    otp_wait.clear()
    logger.info("OTP Received: "+str(otp))
    return otp


def play_sound(file_path):
    os.system("vlc --intf dummy --play-and-exit".format(file_path))


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
            play_sound(os.path.join("audio", "refresh_OTP.mp3"))

    if not otp_alert_running:
        otp_alert_running = True
        alert = Thread(target=wait_and_alert, daemon=True)
        alert.start()
    else:
        return


def booking_alert(count=None):
    siren = Thread(target=play_sound, args=[os.path.join("audio", "Siren-SoundBible.com-1094437108.mp3")],
                   daemon=True)
    siren.start()


def auto_book():
    global pin_codes, vaccine_type, payment_type, dose, age, dates
    with get_api_service_context():
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


####### BEFECIARY BOOKING DETAILS #######

mobile_number = 0000000000  # Mobile Number of the user
beneficiary_ids = [0000000000, 1111111111]  # Get the beneficiary Id from client.get_beneficiary()
age = 18   # Example values: 18 / 45
dose = 1   # Example values: 1 /  2
pin_codes = [600000111]  # List of pin codes where you would want to book for a slot if available
district_ids = [571]  # District Id of the district where the above pin codes are present
dates = ["19-05-2021", "20-05-2021", "21-05-2021"]  # List of dates when you would want to book for a slot
vaccine_type = ["covishield", "sputnik v"]  # Example values : "any" / "covaxin" / ["covaxin", "covisheield"]
payment_type = "any"  # Example values: "any" / "paid" / "free"

######## GLOBAL SETTINGS ##########

otp = None
otp_wait = threading.Event()
otp_alert_running = False
poll_time_range = (15.0, 20.0)
client = APIClient(mobile_no=mobile_number, otp_retrieval_method=get_otp, auto_refresh_token=True,
                   auto_refresh_retries_count=3)
auto_book_worker = Thread(target=auto_book, daemon=True)
log_format = "%(asctime)s — [Module Name: %(name)s] — [PID: %(process)d] — " \
               "[Thread : %(threadName)s] —  %(levelname)s — [Method and Line " \
               "No: %(funcName)s:%(lineno)d] — %(message)s"
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(__name__)


auto_book_worker.start()
