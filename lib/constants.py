
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
request_retry_backoff_factor_seconds = 0.3
request_timeout_seconds = 60
blocked_request_retry_backoff_factor_seconds = 2
connection_error_retry_attempts = 3
refresh_token_retry_delay_seconds = 3
refresh_token_retries_attempts = 3
user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'

otp_generation_secret = "U2FsdGVkX1/8BKMQFEZdL5uaOcmBjvW1/wVjY+qbEf/svmkAqgjgCWtR8ki7IQ9kVaXiEXUTA4Gp1FkQLqmpzA=="
vaccine_types = ["covaxin", "covishield", "sputnik v"]
minimum_age_limits = [18, 45]
doses = [1, 2]
payment_types = ["paid", "free"]
