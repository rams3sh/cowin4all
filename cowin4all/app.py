import re
import time
import logging
import random
import json
import argparse
import os
import sys

from cowin4all.cowin4all_sdk.api import APIClient
from cowin4all.cowin4all_sdk.utils import get_applicable_sessions, refresh_token, break_captcha
from cowin4all.settings import POLL_TIME_RANGE, LOG_FORMAT, AUTO_TOKEN_REFRESH_ATTEMPTS,  BOOKING_INFORMATION_FILE, \
    REPEATEDLY_TRY_WITHOUT_SLEEP_ERROR_REGEX
from cowin4all.utils import get_booking_details, get_timestamp, get_platform  # , booking_alert

platform = get_platform()

if platform != "android":
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    from cowin4all.otp_plugins.webhook_service import get_webhook_service_worker, get_otp_from_webhook
else:
    from cowin4all.otp_plugins.android_termux import get_otp_from_termux_api


logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)

def auto_book(mobile_number=None,
              pin_codes=None, district_ids=None,
              vaccine_type=None, payment_type=None, dose=None, age_limit=None, dates=None,
              beneficiary_ids= None, booking_mode=None, otp_retrieval_method=None,
              ):

    client = APIClient(mobile_no=mobile_number, otp_retrieval_method=otp_retrieval_method, auto_refresh_token=True,
                       auto_refresh_retries_count=AUTO_TOKEN_REFRESH_ATTEMPTS)

    def schedule_appointment(slots=None,
                             client=None,
                             beneficiaries=None,
                             dose_number=None,
                             center_id=None,
                             session_id=None):
        # booking_alert()
        slot = slots[-1]
        c = client.get_captcha()
        captcha = break_captcha(captcha_svg=c)
        try:
            app_id = client.schedule_booking(beneficiaries=beneficiaries,
                                             session_id=session_id,
                                             captcha=captcha,
                                             dose_number=dose_number,
                                             center_id=center_id,
                                             slot=slot)
        except Exception:
            app_id = None

        if not app_id:
            return

        path = client.download_confirmation(appointment_id=app_id,
                                            destination_file_path=
                                            get_timestamp() + "_confirmation.pdf")
        logger.info("Successfully Booked for {} beneficiary(ies) "
                    "!!  Confirmation form is available at {}!!".format(len(beneficiaries), path))

        return app_id

    while True:
        exception_message = ""

        try:
            logger.info("Polling ...")
            client.get_beneficiaries()
            centres = get_applicable_sessions(client=client, district_ids=district_ids,
                                              vaccine_type=vaccine_type,
                                              payment_type=payment_type, dose=dose, age=age_limit, dates=dates)
            temp_centres = {}

            for centre in centres:
                if pin_codes:
                    if centres[centre]["pin_code"] in pin_codes:
                        temp_centres.update({centre: centres[centre]})
                else:
                    temp_centres.update({centre: centres[centre]})
            centres = temp_centres
            logger.info("Available centres:{}".format(centres))
            if centres:
                logger.info("Some centres found !!")
                for centre in centres:
                    for session in centres[centre]["sessions"]:
                        if session["available_capacity_dose{}".format(dose)] < len(beneficiary_ids):
                            if booking_mode == "first_available":
                                appointment_id = schedule_appointment(
                                    slots=session["slots"], client=client, dose_number=dose, center_id=centre,
                                    session_id=session["session_id"],
                                    beneficiaries=
                                    beneficiary_ids[0:session["available_capacity_dose{}".format(dose)]])
                                if not appointment_id:
                                    continue
                                else:
                                    # Removing the ones for whom slot is booked already
                                    booked_beneficiaries = \
                                        beneficiary_ids[0:session["available_capacity_dose{}".format(dose)]]
                                    beneficiary_ids = [b for b in beneficiary_ids if b not in booked_beneficiaries]

                                    # FIXME: to think on whether to update the booking info file once
                                    #  slot is booked
                                    if not beneficiary_ids:
                                        break
                                    else:
                                        continue

                            else:
                                logger.info("Available slots for dose {} : {} is less than the number of "
                                            "beneficiary !!".format(dose,
                                                                    session["available_capacity_dose{}"
                                                                            "".format(dose)]))
                                continue

                        appointment_id = schedule_appointment(
                            slots=session["slots"], client=client, dose_number=dose, center_id=centre,
                            session_id=session["session_id"],
                            beneficiaries=beneficiary_ids)

                        if not appointment_id:
                            continue

                        # FIXME: to think on whether to update the booking info file once
                        #  slot is booked
                        beneficiary_ids = []
                        break

                    if not beneficiary_ids:
                        break

                if not beneficiary_ids:
                    break

        except Exception as e:
            logger.error(e)
            client.auto_refresh_token_retries_attempted = 0
            exception_message = str(e)

        # Sleep only in case errors does not pertain to unavailability of slot or unsuccessful booking
        # There is a good chance that there could be other centres that could have opened immediately and can be tried

        if not any([re.search(p, exception_message) for p in REPEATEDLY_TRY_WITHOUT_SLEEP_ERROR_REGEX]):
            time.sleep(random.uniform(POLL_TIME_RANGE[0], POLL_TIME_RANGE[1]))


def confirm_and_save_booking_details():
    booking_details = None
    if os.path.exists(BOOKING_INFORMATION_FILE):
        with open(BOOKING_INFORMATION_FILE, "r") as f:
            js = f.read()
        try:
            booking_details = json.loads(js)
            if not booking_details:
                print(js)
                os.remove(BOOKING_INFORMATION_FILE)
            else:
                print("Previous booking information file has been identified !!")
        except Exception:
            print("Booking information file at {} is corrupted. Removing it. Please re-enter the details !!"
                  "".format(BOOKING_INFORMATION_FILE))
            os.remove(BOOKING_INFORMATION_FILE)

    booking_details = get_booking_details(booking_details=booking_details)

    with open(BOOKING_INFORMATION_FILE, 'w') as f:
        f.write(json.dumps(booking_details))

    return


def read_booking_info():
    booking_info = dict()
    if os.path.exists(BOOKING_INFORMATION_FILE):
        with open(BOOKING_INFORMATION_FILE, "r") as f:
            js = f.read()
        try:
            booking_details = json.loads(js)
            booking_info["mobile_number"] = booking_details["mobile_number"]
            booking_info["beneficiary_ids"] = [b["id"] for b in booking_details["beneficiaries"]]
            booking_info["age_limit"] = booking_details["beneficiaries"][0]["booking_age_limit"]
            booking_info["dose"] = booking_details["beneficiaries"][0]["awaited_dose"]
            booking_info["pin_codes"] = booking_details["pin_codes"]
            booking_info["district_ids"] = [d['district_id'] for d in booking_details["district_ids"]]
            booking_info["dates"] = booking_details["dates"]
            booking_info["vaccine_type"] = booking_details["preferred_vaccine_types"]
            booking_info["payment_type"] = booking_details["payment_types"]
            booking_info["booking_mode"] = booking_details["booking_mode"]["mode"]

        except Exception as e:
            print(e)
            print("Booking information file at {} is corrupted. Removing it. Please re-enter the details again !!"
                  "".format(BOOKING_INFORMATION_FILE))
            os.remove(BOOKING_INFORMATION_FILE)
    else:
        print("There is no booking information available !!")
        return

    return booking_info


def main():
    if len(sys.argv) < 2:
        confirm_and_save_booking_details()
        booking_info = read_booking_info()
        if platform != "android":
            api_service = get_webhook_service_worker()
            with api_service():
                auto_book(**booking_info, otp_retrieval_method=get_otp_from_webhook)
        else:
            auto_book(**booking_info, otp_retrieval_method=get_otp_from_termux_api)

    elif sys.argv[1] == "test":
        pass

    elif sys.argv[1] == "test":
        binfo = read_booking_info()
        if binfo:
            mob = binfo["mobile_number"]
            if platform != "android":
                print("Testing SMSSync integration :")
                service = get_webhook_service_worker()
                with service():
                    client = APIClient(mobile_no=mob, otp_retrieval_method=get_otp_from_webhook,
                                       auto_refresh_token=False)
                    while True:
                        try:
                            refresh_token(client=client)
                            print("\n\nIntegration working fine !! Exiting ..")
                            break
                        except Exception as e:
                            print(e)

                        time.sleep(20)
            else:
                client = APIClient(mobile_no=mob, otp_retrieval_method=get_otp_from_termux_api,
                                   auto_refresh_token=False)
                while True:
                    try:
                        refresh_token(client=client)
                        print("\n\nIntegration working fine !! Exiting ..")
                        break
                    except Exception as e:
                        print(e)

        else:
            print("Booking information is not available !! Kindly ")

    else:
        print("Invalid argument !! \n Usage:- \n cowin4all ")


if __name__ == "__main__":
    main()
