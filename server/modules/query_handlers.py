from logger import logger


def query_chain(chain, user_input: str):

    try:
        logger.debug(f"Processing user input: {user_input}")

        result = chain.invoke({"input": user_input})

        # DEBUG : voir ce que le retriever retourne
        logger.debug(f"Chain result keys: {result.keys()}")
        logger.debug(f"Number of documents: {len(result.get('context', []))}")

        for i, doc in enumerate(result.get("context", [])):
            logger.debug(f"Document {i}:")
            logger.debug(f"Metadata: {doc.metadata}")
            logger.debug(f"Content: {doc.page_content[:500]}")

        response = {
            "response": result["answer"],
            "sources": [
                doc.metadata.get("source", "")
                for doc in result.get("context", [])
            ]
        }

        logger.debug(f"chain response: {response}")

        return response

    except Exception as e:
        logger.error(f"Error during query processing: {str(e)}")
        raise