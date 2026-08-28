from fastapi import Request
from fastapi.response import JSONResponse
from logger import logger


async def catch_exception_middleware(request:Request,call_next):
    try:
        response=await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."}
        )