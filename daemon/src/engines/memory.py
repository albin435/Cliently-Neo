import json
import logging
from typing import List, Dict, Optional
import numpy as np

from sqlmodel import select
from ..database import get_session, MemoryNode
from .llm import llm_client

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages the Neo CTO Vector Memory for long-term architectural persistence."""

    def add_memory(self, content: str, node_type: str = "past_decision", meta: Optional[Dict] = None):
        """Add a new memory node by computing its embedding and saving to DB."""
        if not content or not content.strip():
            return
            
        try:
            embedding = llm_client.embed_content(content)
            if not embedding:
                logger.error("Failed to generate embedding for memory node.")
                return
                
            with get_session() as db:
                node = MemoryNode(
                    content=content,
                    node_type=node_type,
                    metadata_json=json.dumps(meta) if meta else None,
                    embedding_json=json.dumps(embedding)
                )
                db.add(node)
                db.commit()
                logger.info(f"New {node_type} node added to CTO Vector Memory.")
        except Exception as e:
            logger.error(f"Failed to add memory to Vector DB: {e}")

    def query_memory(self, query: str, top_k: int = 5, threshold: float = 0.5, node_type: Optional[str] = None) -> List[Dict]:
        """Search memory nodes using cosine similarity, with optional type filtering."""
        try:
            query_emb = llm_client.embed_content(query)
            if not query_emb:
                return []
                
            q_vec = np.array(query_emb)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return []
                
            results = []
            with get_session() as db:
                stmt = select(MemoryNode)
                if node_type:
                    stmt = stmt.where(MemoryNode.node_type == node_type)
                
                nodes = db.exec(stmt).all()
                for node in nodes:
                    try:
                        node_emb = json.loads(node.embedding_json)
                        n_vec = np.array(node_emb)
                        n_norm = np.linalg.norm(n_vec)
                        
                        if n_norm == 0:
                            continue
                            
                        sim = np.dot(q_vec, n_vec) / (q_norm * n_norm)
                        if sim >= threshold:
                            results.append({
                                "id": node.id,
                                "content": node.content,
                                "node_type": node.node_type,
                                "metadata": json.loads(node.metadata_json) if node.metadata_json else {},
                                "similarity": float(sim),
                                "created_at": node.created_at.isoformat()
                            })
                    except Exception as e:
                        logger.error(f"Error computing similarity for node {node.id}: {e}")
                        
            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error querying Vector DB: {e}")
            return []

memory_manager = MemoryManager()
