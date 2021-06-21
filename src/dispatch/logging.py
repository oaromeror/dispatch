import logging
from dispatch.config import LOG_LEVEL


def configure_logging():
    if LOG_LEVEL == "DEBUG":
        # log level:logged message:full module path:function invoked:line number of logging call
        LOGFORMAT = "%(levelname)s:%(message)s:%(pathname)s:%(funcName)s:%(lineno)d"
        logging.basicConfig(level=LOG_LEVEL, format=LOGFORMAT)
    else:
        logging.basicConfig(level=LOG_LEVEL)

    print(logging.root.manager.loggerDict)

    uvicorn_logger = logging.getLogger('uvicorn.access')
    uvicorn_logger.setLevel(logging.CRITICAL)

    muiltipart_logger = logging.getLogger('multipart.multipart')
    muiltipart_logger.setLevel(logging.CRITICAL)



