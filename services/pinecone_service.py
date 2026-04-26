from pinecone import Pinecone, ServerlessSpec
from config.settings import settings
from utils.logger import logger
import concurrent.futures

_pinecone_client = None
_pinecone_index = None


def get_pinecone_client():
    global _pinecone_client
    if _pinecone_client is None:
        if not settings.pinecone.API_KEY:
            raise ValueError("PINECONE_API_KEY is missing")
        logger.info("Initializing Pinecone client with environment...")
        _pinecone_client = Pinecone(api_key=settings.pinecone.API_KEY, environment=settings.pinecone.ENVIRONMENT)
    return _pinecone_client


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        client = get_pinecone_client()
        logger.info(f"Connecting to index: {settings.pinecone.INDEX_NAME}")
        _pinecone_index = client.Index(settings.pinecone.INDEX_NAME)
    return _pinecone_index


def query_pinecone(vector, top_k=5, categories=None, cluster=None):
    """Query Pinecone across namespaces (clusters).
    If ``cluster`` is provided, only that namespace is queried; otherwise all namespaces are queried in parallel.
    ``categories`` is used as a metadata filter on the ``category`` field.
    """
    index = get_pinecone_index()
    try:
        # Build metadata filter
        filter_query = None
        if categories:
            filter_query = {"cluster": {"$in": categories}}
        # Determine namespaces to query
        if cluster:
            namespaces = [cluster]
        else:
            stats = index.describe_index_stats()
            namespaces = list(stats.get('namespaces', {}).keys())
        if not namespaces:
            logger.warning("No namespaces found in the Pinecone index.")
            return []
        logger.info(f"Querying Pinecone across {len(namespaces)} namespaces | top_k={top_k} | filter={categories}")
        all_results = []
        def _query_namespace(ns):
            try:
                response = index.query(
                    vector=vector,
                    top_k=top_k,
                    include_metadata=True,
                    filter=filter_query,
                    namespace=ns
                )
                return format_results(response)
            except Exception as e:
                logger.error(f"Error querying namespace {ns}: {e}")
                return []
        # Parallel query
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ns = {executor.submit(_query_namespace, ns): ns for ns in namespaces}
            for future in concurrent.futures.as_completed(future_to_ns):
                all_results.extend(future.result())
        # Sort and limit globally
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]
    except Exception as e:
        logger.error(f"Pinecone query failed: {str(e)}")
        return []


def format_results(response):
    results = []
    for match in response.get("matches", []):
        results.append({
            "id": match["id"],
            "score": match["score"],
            "text": match["metadata"].get("text", ""),
            "cluster": match["metadata"].get("cluster", ""),
            "source": match["metadata"].get("source", "")
        })
    return results


def get_all_chunks():
    """Retrieve all chunks (metadata) from every namespace.
    Returns a list of dicts with keys: id, text, category, source.
    Used for building the BM25 index.
    """
    index = get_pinecone_index()
    # Get list of namespaces
    stats = index.describe_index_stats()
    namespaces = list(stats.get('namespaces', {}).keys())
    all_chunks = []
    for ns in namespaces:
        # Query with a very high top_k to fetch all vectors in the namespace
        # Pinecone limits to 10k per query; we loop if needed (simplified here).
        try:
            response = index.query(
                vector=[0]*settings.pinecone.DIMENSION,  # dummy zero vector (will be ignored with filter)
                top_k=10000,
                include_metadata=True,
                namespace=ns,
                # Use a filter that matches everything
                filter={}
            )
            for match in response.get("matches", []):
                all_chunks.append({
                    "id": match["id"],
                    "text": match["metadata"].get("text", ""),
                    "cluster": match["metadata"].get("cluster", ""),
                    "source": match["metadata"].get("source", "")
                })
        except Exception as e:
            logger.error(f"Failed to fetch chunks from namespace {ns}: {e}")
    return all_chunks