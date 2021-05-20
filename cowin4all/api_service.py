from fastapi import FastAPI, Request
import contextlib
import uvicorn
import time
import threading
import logging
import re

from settings import COWIN4ALL_SERVICE_PORT

logger = logging.getLogger(__name__)

app = FastAPI(title="cowin4all")

otp = None
event_waiter = threading.Event()


def get_otp():
    global otp, event_waiter
    logger.info("Waiting for OTP !! ")
    event_waiter.wait()
    event_waiter.clear()
    logger.info("OTP Received: " + str(otp))
    return otp


@app.put("/put_otp")
async def put_otp(request: Request):
    global otp, event_waiter
    body = await request.body()
    body = body.decode("utf-8")
    logger.info("Received SMS: " + str(body))
    match = re.findall("(?<=CoWIN is )[0-9]{6}", body)
    if match:
        otp = match[0]
        event_waiter.set()


class HelperService(uvicorn.Server):

    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def running(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started and thread.is_alive():
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


def get_api_service_context():
    global app
    config = uvicorn.Config(app, host="0.0.0.0", port=COWIN4ALL_SERVICE_PORT,
                            log_level="debug",
                            debug=True)

    helper_service = HelperService(config=config)
    return helper_service.running
