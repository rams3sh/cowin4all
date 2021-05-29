import os.path
import json

base_url = "https://cdn-api.co-vin.in/api/v2/"

endpoint_map = {
    "GENERATE_OTP": {"METHOD": "POST", "ENDPOINT": base_url + "auth/generateMobileOTP"},
    "VALIDATE_OTP": {"METHOD": "POST", "ENDPOINT": base_url + "auth/validateMobileOtp"},
    "GET_BENEFICIARIES": {"METHOD": "GET", "ENDPOINT": base_url + "appointment/beneficiaries"},
    "CHECK_SLOTS_BY_PINCODE": {"METHOD": "GET", "ENDPOINT": base_url + "appointment/sessions/public/calendarByPin"},
    "LIST_STATES": {"METHOD": "GET", "ENDPOINT": base_url + "admin/location/states"},
    "LIST_DISTRICTS": {"METHOD": "GET", "ENDPOINT": base_url + "admin/location/districts/{STATE_ID}"},
    "CHECK_SLOTS_BY_DISTRICT": {"METHOD": "GET", "ENDPOINT": base_url + "appointment/sessions/calendarByDistrict"},
    "GET_CAPTCHA": {"METHOD": "POST", "ENDPOINT": base_url + "auth/getRecaptcha"},
    "SCHEDULE_BOOKING": {"METHOD": "POST", "ENDPOINT": base_url + "appointment/schedule"},
    "GET_CONFIRMATION_FORM": {"METHOD": "GET", "ENDPOINT": base_url + "appointment/appointmentslip/download"}
}
# Timeout in seconds case of ConnectionTimeout / ReadTimeout
default_request_timeout_seconds = 3
# Number of times refresh of a token is to be attempted
delay_refresh_token_retry_delay_seconds = 5

# Delay factor in seconds to be given during every retry in case of ConnectionTimeout / ReadTimeout
default_request_retry_backoff_factor_seconds = 0.3
# Delay factor in seconds to be given during every retry in case of request is blocked
default_blocked_request_retry_backoff_factor_seconds = 5

# Number of retries to be attempted in case of ConnectionTimeout / ReadTimeout
default_connection_error_retry_attempts = 3
# Number of retries to be attempted in case of unsuccessful token refresh
default_refresh_token_retries_attempts = 3

default_auto_refresh_token = True
default_retry_blocked_request = True

default_user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'
default_otp_generation_secret = \
    "U2FsdGVkX1/8BKMQFEZdL5uaOcmBjvW1/wVjY+qbEf/svmkAqgjgCWtR8ki7IQ9kVaXiEXUTA4Gp1FkQLqmpzA=="


vaccine_types = ["covaxin", "covishield", "sputnik v"]
minimum_age_limits = [18, 45]
doses = [1, 2]
payment_types = ["paid", "free"]

captcha_char_mapping = {}
with open(os.path.join(os.path.dirname(__file__), "captcha_char_mapping.json"), "r") as f:
    captcha_char_mapping = json.loads(f.read())
