"""
Multimodal Agent using LangGraph
Orchestrates document processing, retrieval, and LLM reasoning
"""

import logging
from typing import TypedDict, Annotated, Sequence, List
from pathlib import Path
import operator

try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except Exception:
    pass

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from utils.document_processor import DocumentProcessor
from utils.vector_store import VectorStore
from utils.llm_wrapper import LocalLLM
from config import config

logger = logging.getLogger(__name__)


# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    documents: list
    query: str
    context: list
    response: str
    error: str


class MultimodalAgent:
    """Agent for handling multimodal queries with LangGraph"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.vector_store = VectorStore(lazy_init=True)
        self.llm = LocalLLM()
        self.graph = self._build_graph()
        logger.info("MultimodalAgent initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve", self._retrieve_context)
        workflow.add_node("generate", self._generate_response)
        
        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()

    def _extract_image_paths(self, context: List[dict]) -> List[Path]:
        """Extract unique image paths from retrieved context."""
        image_paths: List[Path] = []
        seen = set()

        for ctx in context:
            metadata = ctx.get("metadata", {})
            if metadata.get("type") != "image":
                continue

            source = metadata.get("source")
            if not source or source in seen:
                continue

            path = Path(source)
            if path.exists():
                image_paths.append(path)
                seen.add(source)

            if len(image_paths) >= config.MAX_IMAGE_CONTEXT:
                break

        return image_paths
    
    def _retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector store"""
        try:
            query = state.get("query", "")
            if not query:
                logger.warning("No query provided for retrieval")
                state["context"] = []
                return state
            
            # Retrieve relevant documents
            context = self.vector_store.similarity_search(query, k=4)
            state["context"] = context
            
            logger.info(f"Retrieved {len(context)} context documents")
            return state
            
        except Exception as e:
            logger.error(f"Error in retrieval: {str(e)}")
            state["error"] = str(e)
            state["context"] = []
            return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using LLM with context"""
        try:
            query = state.get("query", "")
            context = state.get("context", [])
            
            if not context:
                response = self.llm.generate(query)
            else:
                image_paths = self._extract_image_paths(context)
                if image_paths:
                    response = self.llm.generate_with_context_and_images(query, context, image_paths)
                else:
                    response = self.llm.generate_with_context(query, context)
            
            state["response"] = response
            state["messages"] = [
                HumanMessage(content=query),
                AIMessage(content=response)
            ]
            
            logger.info(f"Generated response ({len(response)} chars)")
            return state
            
        except Exception as e:
            logger.error(f"Error in generation: {str(e)}")
            state["error"] = str(e)
            state["response"] = f"Error: {str(e)}"
            return state
    
    def process_documents(self, file_paths: list) -> dict:
        """
        Process and index documents
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Processing results
        """
        try:
            processed_docs = []
            errors = []
            
            for file_path in file_paths:
                try:
                    doc = self.doc_processor.process_document(Path(file_path))
                    doc_text = doc.get("text", "")
                    if not doc_text or not doc_text.strip():
                        error_msg = f"No extractable text in {Path(file_path).name}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        continue
                    processed_docs.append(doc)
                    logger.info(f"Processed: {Path(file_path).name}")
                except Exception as e:
                    error_msg = f"Failed to process {Path(file_path).name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Add to vector store
            if processed_docs:
                try:
                    self.vector_store.add_documents(processed_docs)
                except Exception as e:
                    error_msg = f"Failed to index documents: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    processed_docs = []
            
            return {
                "success": len(processed_docs),
                "failed": len(errors),
                "errors": errors,
                "processed_files": [doc['source'] for doc in processed_docs]
            }
            
        except Exception as e:
            logger.error(f"Error in process_documents: {str(e)}")
            raise
    
    def query(self, query_text: str) -> dict:
        """
        Query the agent with text or speech
        
        Args:
            query_text: User query
            
        Returns:
            Response dictionary
        """
        try:
            initial_state = {
                "messages": [],
                "documents": [],
                "query": query_text,
                "context": [],
                "response": "",
                "error": ""
            }
            
            # Run the graph
            result = self.graph.invoke(initial_state)
            
            return {
                "query": query_text,
                "response": result.get("response", ""),
                "context": result.get("context", []),
                "error": result.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Error in query: {str(e)}")
            return {
                "query": query_text,
                "response": "",
                "context": [],
                "error": str(e)
            }
