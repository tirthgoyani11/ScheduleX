# core/embeddings/faculty_embeddings.py
"""
Faculty preference embedding store.
Uses ChromaDB locally for cosine-similarity matching during substitution ranking.
Falls back gracefully to a 0.5 similarity when ChromaDB is unavailable.
"""
import structlog

log = structlog.get_logger()

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class FacultyEmbeddingStore:
    """Manages faculty preference embeddings in ChromaDB."""

    def __init__(self):
        self._collection = None
        if CHROMA_AVAILABLE:
            try:
                from config import settings
                client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
                self._collection = client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
                log.info("chromadb_connected", collection=settings.CHROMA_COLLECTION_NAME)
            except Exception as e:
                log.warning("chromadb_init_failed", error=str(e))
                self._collection = None

    async def upsert_faculty(self, faculty_id: str, expertise: list[str], preferred_time: str | None, max_weekly_load: int = 18, department: str = "General"):
        """Store or update a faculty member's embedding from profile data."""
        if not self._collection:
            return
        try:
            profile_text = self._profile_to_text({
                "expertise": expertise,
                "preferred_time": preferred_time,
                "max_weekly_load": max_weekly_load,
                "department": department,
            })
            self._collection.upsert(
                ids=[faculty_id],
                documents=[profile_text],
                metadatas=[{"faculty_id": faculty_id, "expertise": ",".join(expertise or []), "preferred_time": preferred_time or "any"}],
            )
        except Exception as e:
            log.warning("chromadb_upsert_failed", faculty_id=faculty_id, error=str(e))

    # Alias for spec compatibility
    async def upsert_faculty_embedding(self, faculty_id: str, faculty_profile: dict):
        """Spec-compatible upsert from a profile dict."""
        await self.upsert_faculty(
            faculty_id=faculty_id,
            expertise=faculty_profile.get("expertise", []),
            preferred_time=faculty_profile.get("preferred_time"),
            max_weekly_load=faculty_profile.get("max_weekly_load", 18),
            department=faculty_profile.get("department", "General"),
        )

    @staticmethod
    def _profile_to_text(profile: dict) -> str:
        """Convert faculty profile dict to a natural language text for embedding."""
        expertise = ", ".join(profile.get("expertise", []))
        preferred_time = profile.get("preferred_time", "any")
        return (
            f"Faculty member specializing in {expertise}. "
            f"Prefers {preferred_time} teaching slots. "
            f"Maximum weekly load: {profile.get('max_weekly_load', 18)} hours. "
            f"Department: {profile.get('department', 'General')}."
        )

    async def get_faculty_embedding(self, faculty_id: str) -> list | None:
        """Retrieve the embedding vector for a faculty member."""
        if not self._collection:
            return None
        try:
            result = self._collection.get(ids=[faculty_id], include=["embeddings"])
            if result and result.get("embeddings") and result["embeddings"][0]:
                return result["embeddings"][0]
        except Exception as e:
            log.warning("chromadb_get_failed", faculty_id=faculty_id, error=str(e))
        return None

    async def query_similar(self, faculty_id: str, n_results: int = 5) -> list[str]:
        """Find the most similar faculty by embedding."""
        if not self._collection:
            return []
        try:
            embedding = await self.get_faculty_embedding(faculty_id)
            if not embedding:
                return []
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results + 1,  # +1 to exclude self
            )
            ids = results.get("ids", [[]])[0]
            return [fid for fid in ids if fid != faculty_id][:n_results]
        except Exception as e:
            log.warning("chromadb_query_failed", error=str(e))
            return []
