from fastapi import APIRouter, UploadFile, File
from typing import List
from modules.load_vectorstore import load_vectorstore
from fastapi.responses import JSONResponse
from logger import logger


router=APIRouter()

@router.post("/upload_pdfs/")
async def upload_pdfs(files:List[UploadFile] = File(...)):
    try:
        logger.info("Recieved uploaded files")
        result = load_vectorstore(files)
        logger.info(f"Upload result: {result}")
        # 400 only when nothing could be indexed; partial success is still a 200.
        status = 200 if result["processed"] else 400
        return JSONResponse(status_code=status, content=result)
    except Exception as e:
        logger.exception("Error during PDF upload")
        return JSONResponse(status_code=500,content={"error":str(e)})
