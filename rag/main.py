from pinecone import Pinecone
from config.settings import Config

config = Config()

pc = Pinecone(api_key = config.PINECONE_API_KEY)
index = pc.Index(config.PINECONE_INDEX_NAME)


