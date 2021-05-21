import time
import logging
import random
import json
import os


from cowin4all_sdk.api import APIClient
from cowin4all_sdk.utils import get_applicable_sessions, get_captcha_input_manually
from api_service import get_api_service_worker, get_otp_from_webhook
from settings import POLL_TIME_RANGE, LOG_FORMAT, AUTO_TOKEN_REFRESH_ATTEMPTS, CONFIRMATION_PDF_PREFIX, \
    BOOKING_INFORMATION_FILE
from utils import booking_alert, get_booking_details

logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

logger = logging.getLogger(__name__)


def auto_book():
    global pin_codes, vaccine_type, payment_type, dose, age, dates
    api_service = get_api_service_worker()

    client = APIClient(mobile_no=mobile_number, otp_retrieval_method=get_otp_from_webhook, auto_refresh_token=True,
                       auto_refresh_retries_count=AUTO_TOKEN_REFRESH_ATTEMPTS)

    with api_service():
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
                            booking_alert()
                            # Most latest slot
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
                                                                destination_file_path=
                                                                CONFIRMATION_PDF_PREFIX + "_confirmation.pdf")
                            logger.info("Successfully Booked!!  Confirmation form is available at {}!!".format(path))
                            return
            except Exception as e:
                logger.error(e)
                client.auto_refresh_token_retries_attempted = 0
            time.sleep(random.uniform(POLL_TIME_RANGE[0], POLL_TIME_RANGE[1]))


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

if __name__ == "__main__":
    booking_details = None
    if os.path.exists(BOOKING_INFORMATION_FILE):
        with open(BOOKING_INFORMATION_FILE, "r") as f:
            j = f.read()
        try:
            booking_details = json.loads(j)
        except Exception as e:
            print("Booking information file at {} is corrupted. Removing it. Please re-enter the details !!"
                  "".format(BOOKING_INFORMATION_FILE))
            os.remove(BOOKING_INFORMATION_FILE)
        if not booking_details:
            os.remove(BOOKING_INFORMATION_FILE)
        else:
            print("Previous booking information file has been identified !!")

    booking_details = get_booking_details(booking_details=booking_details)

    with open(BOOKING_INFORMATION_FILE, 'w') as f:
        f.write(json.dumps(booking_details))
