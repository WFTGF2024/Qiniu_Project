import os
from qdrant_client import QdrantClient
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
client = QdrantClient(url="http://127.0.0.1:6333", prefer_grpc=False, check_compatibility=False)
print(client.get_collections())
