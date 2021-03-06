import os

COWIN4ALL_APP_ROOT_DIRECTORY = os.path.dirname(__file__)
COWIN4ALL_SERVICE_PORT = 8081
POLL_TIME_RANGE = (10.0, 15.0)
LOG_FORMAT = "%(asctime)s — [Module Name: %(name)s] — [PID: %(process)d] — [Thread : %(threadName)s] —  %(levelname)s" \
             " — [Method and Line  No: %(funcName)s:%(lineno)d] — %(message)s"

BOOKING_INFORMATION_FILE = "booking_information.json"
AUTO_TOKEN_REFRESH_ATTEMPTS = 3
OTP_REQUEST_TIMEOUT_SECONDS = 110
# AUDIO_FILE_PLAYING_COMMAND = "vlc --intf dummy --play-and-exit {audio_file_path}"
#
# BOOKING_ALERT_AUDIO_PATH = os.path.join("audio", "booking_siren_alert.mp3")
# OTP_ALERT_AUDIO_PATH = os.path.join("audio", "refresh_otp.mp3")

VACCINATION_DOSE_DATES = {"covishield": {"dose2": 84}, "covaxin": {"dose2": 28}, "sputnik v": {"dose2": 21}}

BOOKING_MODES = [{"mode": "all", "remarks": "Book only if slots are available for all selected beneficiaries"},
                 {"mode": "first_available",
                  "remarks": "Book for beneficiaries based on WHEREVER slot is available first. "}]

REPEATEDLY_TRY_WITHOUT_SLEEP_ERROR_REGEX = ["Your transaction didn't go through. Please try again later",
                                            "This vaccination center is completely booked for the selected date"]
