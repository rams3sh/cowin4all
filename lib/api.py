from hashlib import sha256
import re

from lib.utils import send_request
from lib.constants import otp_generation_secret


class APIClient:

    def __init__(self,  mobile_no=None,
                 otp_retrieval_method=None,
                 auto_refresh_token=True,
                 auto_refresh_retries_count=3):
        self.otp_retrieval_method = otp_retrieval_method  # Custom method for retrieval of OTP
        self.auto_refresh_token = auto_refresh_token    # Flag to enable / disable auto refreshing of token
        # Number of auto token retries to be attempted, if enabled.
        # None corresponds to unlimited retries. Definite value to be provided in int.
        self.auto_refresh_retries_count = auto_refresh_retries_count
        # Number of auto refresh token retries attempted so far
        self.auto_refresh_token_retries_attempted = 0
        self.mobile = mobile_no  # Mobile number of the user registered in Cowin portal

        # Both of the below variables keeps getting refreshed as part of auto refresh token process
        self.taxation_id = None  # Taxation Id received during most recent OTP query.
        self.token = None   # Auth token received during most recent OTP validation. This keeps getting refreshed.

    def get_otp(self):
        payload = {"mobile": self.mobile,
                   "secret": otp_generation_secret
                   }
        self.taxation_id = None
        self.token = None
        self.taxation_id = send_request(action="GENERATE_OTP", payload=payload).json()["txnId"]

    def validate_otp(self, otp=None):
        payload = {"otp": sha256(str(otp).encode('utf-8')).hexdigest(),
                   "txnId": self.taxation_id}
        self.token = None

        # Status 400 code is raised in case of Invalid OTP. This requires refreshing of token.
        # Hence it has been added as an explicit status code for initiating token refresh.
        self.token = send_request(action="VALIDATE_OTP", payload=payload, client=self,
                                  explicit_token_refresh_status_codes=[400]).json()["token"]

    def get_beneficiaries(self):
        beneficiaries = send_request(action="GET_BENEFICIARIES", client=self).json()["beneficiaries"]
        return beneficiaries

    def check_slot_pin_wise(self, pin_code=None, date=None):
        centres = send_request(action="CHECK_SLOTS_BY_PINCODE", pincode=pin_code, date=date,
                               client=self).json()["centers"]
        return centres

    def list_states(self):
        states = send_request(action="LIST_STATES",
                              client=self).json()["states"]
        return states

    def list_districts(self, state_id=None):
        districts = send_request(action="LIST_DISTRICTS", STATE_ID=state_id,
                                 client=self).json()["districts"]
        return districts

    def check_slot_district_wise(self, district_id=None, date=None):
        centres = send_request(action="CHECK_SLOTS_BY_DISTRICT", district_id=district_id,
                               date=date, client=self).json()["centers"]
        return centres

    def get_captcha(self):
        captcha = re.sub('(<path d=)(.*?)(fill=\"none\"/>)', '',
                         send_request(action="GET_CAPTCHA", client=self).json()['captcha'])
        return captcha

    def schedule_booking(self, beneficiaries=None, captcha=None,
                         dose_number=None, center_id=None, session_id=None, slot=None):
        payload = {
                    'beneficiaries': beneficiaries,
                    'dose': dose_number,
                    'center_id': center_id,
                    'session_id': session_id,
                    'slot': slot,
                    'captcha': captcha
                }

        appointment_id = send_request(action="SCHEDULE_BOOKING", payload=payload,
                                      client=self).json().get("appointment_confirmation_no")
        return appointment_id

    def download_confirmation(self, appointment_id=None, destination_file_path=None):
        response = send_request(action="GET_CONFIRMATION_FORM", appointment_id=appointment_id,
                                additional_headers={"Accept": "application/pdf"},
                                client=self)
        with open(destination_file_path, "wb") as f:
            f.write(response.content)

        return destination_file_path
