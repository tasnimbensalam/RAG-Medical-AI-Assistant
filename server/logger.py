import logging 


def setup_logger(name: "learn_RAG"):

    logger=logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch=logging.StreamHandler()
    ch.setLevel(logging.DEBUG)


    formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(ch)
    
    return logger

logger=setup_logger("learn_RAG")


logger.info("Logger initialized successfully.")