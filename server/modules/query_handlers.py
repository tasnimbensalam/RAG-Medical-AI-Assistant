from logger import logger

def query_chain(chain,user_input:str):
    try:
        logger.debug(f"Processing user input: {user_input}")
        result=chain({"query":user_input})
        response={"response": result["result"],
                    "sources": [doc.metadata.get("sources","") for doc in result["source_documents"]]
        }
        logger.debug(f"chain response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error during query processing: {str(e)}")
        raise