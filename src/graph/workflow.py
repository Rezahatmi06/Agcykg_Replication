# src/graph/workflow.py
import logging
import time 
from langgraph.graph import StateGraph, END
from src.graph.state import AgentState

# Import all chains dan agen func
from src.agents.guardrails_agent import guardrails_router_chain
from src.agents.review_agent import review_chain
from src.agents.synthesizer_agent import synthesis_chain
from src.agents.vector_agent import query_vector_search
from src.agents.cypher_agent import query_cypher
from src.agents.reflection_agent import vector_reflection_chain, reflection_chain
from src.agents.mcp_rdf_agent import run_mcp_agent
# from src.agents.routing_agent import router_chain
from src.agents.log_analysis_agent import log_analysis_chain

logger = logging.getLogger(__name__)

# --- Node Definition: Guardrails ---
def guardrails_node(state: AgentState):
    """
     node that checks relevance and routes the question to appropriate tool.
    Returns relevance status and routing decision in a single operation.
    """
    logger.info("--- Executing Node: [[Guardrails & Router]] ---")
    question = state['question']
    result = guardrails_router_chain.invoke({"question": question})
    
    if result.decision == "irrelevant":
        logger.warning(f"[[Guardrails]]: Irrelevant question detected -> '{question}'")
        return {
            "is_relevant": False, 
            "answer": "Sorry, I can only answer questions related to log analysis and cybersecurity knowledge topic"
        }
    else:
        logger.info("[[Guardrails]]: Question is relevant.")
        is_log_question = result.datasource == "log_analysis"
        logger.info(f"[[Router]]: Routing decision: {result.datasource} -> is_log_question: {is_log_question}")
        return {
            "is_relevant": True,
            "is_log_question": is_log_question
        }

# --- Node Definition: Vector Agent ---
def vector_search_node(state: AgentState):
    """Calls the vector search tool and populates the state."""
    logger.info("--- Executing Node: [[vector_agent]] ---")
    question = state['question']
    try:
        vector_context = query_vector_search(question)
        logger.info("[[Vector Agent]] : Vector search completed successfully.")
        logger.info(f"[[Vector Agent]] : Vector search context found:\n{vector_context}")
        return {"log_vector_context": vector_context}
    except Exception as e:
        logger.error(f"[[Vector Agent]] : Vector search failed: {e}")
        return {"log_vector_context": f"Error during vector search: {e}"}

# --- Node Definition: Review Vector Answer ---
def review_vector_node(state: AgentState):
    """Reviews the context from the vector search."""
    logger.info("--- Executing Node: [[review_vector_answer]] ---")
    time.sleep(60)
    question = state['original_question']
    context = state['log_vector_context']
    
    if context and "Error during vector search" not in context:
        logger.info(f"[[Review Vector]]: Found new context, saving as 'latest_vector_context'.")
        state['latest_vector_context'] = context
    
    if not context or "Error during vector search" in context:
        logger.warning("[[Review Vector]]: Context is empty or contains an error. Marking as insufficient.")
        return {"vector_answer_sufficient": False, "log_vector_context": None}

    review = review_chain.invoke({"question": question, "context": context})
    logger.info(f"[[Review Vector]]: Decision: {review.decision}. Reasoning: {review.reasoning}")
    
    return {"vector_answer_sufficient": review.decision == "sufficient"}

# --- Node Definition: Vector Reflection ---
def vector_reflection_node(state: AgentState):
    """Reflects on the failed vector search and rephrases the question."""
    logger.info("--- Executing Node: [[vector_reflection]] ---")
    original_question = state['original_question']
    insufficient_context = state['log_vector_context']
    
    rephrased_result = vector_reflection_chain.invoke({
        "original_question": original_question,
        "log_vector_context": insufficient_context
    })
    
    new_question = rephrased_result.rephrased_question
    iteration_count = state['vector_iteration_count'] + 1
    logger.info(f"[[Vector Reflection]]: Rephrasing question to: '{new_question}'. New attempt: {iteration_count}.")
    
    return {"question": new_question, "vector_iteration_count": iteration_count}

# --- Node Definition: Cypher Agent ---
def cypher_query_node(state: AgentState):
    """Calls the cypher search tool and populates the state."""
    logger.info(f"--- Executing Node: [[cypher_agent]] (Attempt: {state.get('iteration_count', 1)}) ---")
    question = state['question']
    try:
        cypher_result = query_cypher(question)
        context = cypher_result.get("context", [])
        generated_query = cypher_result.get("query", "")

        if not context:
            logger.warning(f"[[Cypher Agent]]: No results found for query: {generated_query}")
        else:
            logger.info(f"[[Cypher Agent]]: Found context. Query: {generated_query}")

        return {
            "cypher_query": generated_query,
            "log_cypher_context": context
        }
    except Exception as e:
        logger.error(f"[[Cypher Agent]] failed: {e}", exc_info=True)
        return {
            "error": f"Query Cypher failed: {e}",
            "log_cypher_context": [],
            "cypher_query": "Failed to generate Cypher query due to an error."
        }

# --- Node Definition: Review Cypher Answer ---
def review_cypher_node(state: AgentState):
    """Reviews the context from the cypher search."""
    logger.info("--- Executing Node: [[review_cypher_answer]] ---")
    time.sleep(30)
    question = state['original_question']
    context = str(state['log_cypher_context'])
    
    if context and context is not None:
        logger.info(f"[[Review Cypher]]: Found new context, saving as 'latest_cypher_context'.")
        state['latest_cypher_context'] = context

    if not context:
        logger.warning("[[Review Cypher]]: Context is empty. Marking as insufficient.")
        return {"cypher_answer_sufficient": False, "log_cypher_context": None}
        
    review = review_chain.invoke({"question": question, "context": context})
    logger.info(f"[[Review Cypher]]: Decision: {review.decision}. Reasoning: {review.reasoning}")

    return {"cypher_answer_sufficient": review.decision == "sufficient"}

# --- Node Definition: Cypher Reflection ---
def cypher_reflection_node(state: AgentState):
    """Reflects on the failed cypher query and rephrases the question."""
    logger.info("--- Executing Node: [[cypher_reflection]] ---") 
    original_question = state['original_question']
    failed_query = state['cypher_query']
    
    rephrased_result = reflection_chain.invoke({
        "original_question": original_question,
        "cypher_query": failed_query
    })
    
    new_question = rephrased_result.rephrased_question
    iteration_count = state['cypher_iteration_count'] + 1
    logger.info(f"[[Cypher Reflection]]: Rephrasing question to: '{new_question}'. New attempt: {iteration_count}.")
    
    return {"question": new_question, "cypher_iteration_count": iteration_count}

# --- Node Definition: Log Analysis Agent ---
def log_analysis_node(state: AgentState):
    """Analyzes log data and determine whether cybersecurity knowledge is required."""
    logger.info("--- Executing Node: [[Log Analysis Agent]] ---")
    time.sleep(80)
    
    result = log_analysis_chain.invoke({
        "original_question": state['original_question'],
        "log_vector_context": str(state.get('log_vector_context', 'No data')),
        "log_cypher_context": str(state.get('log_cypher_context', 'No data')),
    })
    
    # We will temporarily store the log summary in the 'answer' field
    # The synthesizer will later use this and combine it.

    if result.decision == "cskg_required":
        logger.info(f"[[Log Analysis Agent]]: The analysis requires Cybersecurity Knowledge")
        return {"is_cskg_required": True, "answer": result.log_summary, "generated_question_for_rdf": result.generated_question}
    else:
        logger.info("[[Log Analysis Agent]]: The analysis doesn not require Cybersecurity Knowledge.")
        return {"is_cskg_required": False, "answer": result.log_summary}

# --- Node Definition: MCP RDF Agent ---
async def mcp_rdf_agent_node(state: dict) -> dict:
    """An asynchronous node for LangGraph that runs the MCP agent."""
    logger.info("--- Executing Node: [[mcp_rdf_agent]] ---")
    
    question_to_ask = ""
    if state.get('is_log_question') and state.get('generated_question_for_rdf'):
        question_to_ask = state['generated_question_for_rdf']
        logger.info(f"[[MCP RDF Agent]]: Answering generated question: '{question_to_ask}'")
    else:
        question_to_ask = state['original_question']
        logger.info(f"[[MCP RDF Agent]]: Answering direct question: '{question_to_ask}'")
        
    try:
        mcp_context = await run_mcp_agent(question_to_ask)
        logger.info(f"[[MCP RDF Agent]]: Search completed. Context found:\n{mcp_context}")
        return {"mcp_rdf_context": str(mcp_context)}
    except Exception as e:
        logger.error(f"[[MCP RDF Agent]]: Gagal menjalankan node: {e}")
        return {"mcp_rdf_context": f"Error in MCP RDF Agent node: {str(e)}"}
    
# --- Node Definition: Synthesizer ---
def synthesize_node(state: AgentState):
    """Generates the final compiled report for the user."""
    logger.info("--- Executing Node: [[Synthesizer]] ---")
    time.sleep(20)

    # Ambil konteks, jika tidak ada atau kosong, gunakan pesan default
    log_cypher = str(state.get('log_cypher_context')) if state.get('log_cypher_context') else "Not applicable for this query."
    log_vector = str(state.get('log_vector_context')) if state.get('log_vector_context') else "Not applicable for this query."
    generated_q = str(state.get('generated_question_for_rdf', "Not applicable for this query."))

    if not state.get('mcp_rdf_context') and log_cypher == "Not applicable for this query." and log_vector == "Not applicable for this query.":
        final_answer = "Sorry, after several attempts, I could not find any relevant information."
    else:
        final_answer = synthesis_chain.invoke({
            "original_question": state['original_question'],
            "log_cypher_context": log_cypher,
            "log_vector_context": log_vector,
            "generated_question_for_rdf": generated_q,
            "mcp_rdf_context": str(state.get('mcp_rdf_context', "No data was provided from this source.")),
        })
        
    return {"answer": final_answer}

# --- Perakitan Graph ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("guardrails", guardrails_node)
workflow.add_node("vector_agent", vector_search_node)
workflow.add_node("review_vector_answer", review_vector_node)
workflow.add_node("vector_reflection", vector_reflection_node)

workflow.add_node("cypher_agent", cypher_query_node)
workflow.add_node("review_cypher_answer", review_cypher_node)
workflow.add_node("cypher_reflection", cypher_reflection_node)

workflow.add_node("log_analysis_agent", log_analysis_node)
workflow.add_node("mcp_rdf_agent", mcp_rdf_agent_node)
workflow.add_node("synthesizer", synthesize_node)

# 1. Decision after Guardrails
def decide_relevance(state: AgentState):
    if not state.get('is_relevant', False):
        logger.info("[Decision] Question is irrelevant, ending execution.")
        return END
    
    if state.get("is_log_question", False):
        logger.info("[Decision] Question is about logs, proceeding to vector search.")
        return "vector_agent"  # Route log questions to vector agent
    else:
        logger.info("[Decision] Question is about general cybersecurity information and threat intelligence, proceeding to MCP RDF agent.")
        return "mcp_rdf_agent"   # Route cyber knowledge questions to rdf agent

# 2. Decision after Vector Review
def decide_after_vector_review(state: AgentState):
    if state.get('vector_answer_sufficient'):
        logger.info("[Decision] Vector context is sufficient. Proceeding to Cypher agent.")
        return "cypher_agent"
    if state.get("vector_iteration_count", 0) < state.get("max_iterations", 3):
        logger.warning("[Decision] Vector context is insufficient. Proceeding to reflection.")
        return "vector_reflection"
    else:
        if state.get('latest_vector_context'):
            logger.error("[Decision] Max retries for Vector search reached, but a previous context was found. Using the 'latest' context and proceeding to Cypher.")
            state['log_vector_context'] = state['latest_vector_context']
            return "cypher_agent"
        else:
            logger.error("[Decision] Max retries for Vector search reached with no usable context. Proceeding to Cypher with no Vector data.")
            return "cypher_agent"
    

# 3. Decision after Cypher Review
def decide_after_cypher_review(state: AgentState):
    if state.get('cypher_answer_sufficient'):
        logger.info("[Decision] Cypher context is sufficient. Proceeding to Log Analysis agent.")
        return "log_analysis_agent"
    if state.get("cypher_iteration_count", 0) < state.get("max_iterations", 3):
        logger.warning("[Decision] Cypher context is insufficient. Proceeding to reflection.")
        return "cypher_reflection"
    else:
        if state.get('latest_cypher_context'):
            logger.error("[Decision] Max retries for Cypher reached, but a previous context was found. Using the 'latest' context and proceeding to Log Analysis.")
            
            state['log_cypher_context'] = state['latest_cypher_context']
            return "log_analysis_agent"
        else:
            logger.error("[Decision] Max retries for Cypher reached with no usable context. Proceeding to Log Analysis with no Cypher data.")
            return "log_analysis_agent"

# 4. Decision after Log Analysis
def decide_after_log_analysis(state: AgentState):
    if state.get('is_cskg_required'):
        logger.info("[Decision] yes, proceeding to cybersecurity knowledge.")
        return "mcp_rdf_agent"
    else:
        logger.warning("[Decision] no, proceeding to synthesizer.")
        return "synthesizer"
    
# --- Define Edges ---
workflow.set_entry_point("guardrails")

# Add Edges to the graph
workflow.add_conditional_edges(
    "guardrails", 
    decide_relevance, 
    {
        "vector_agent": "vector_agent",
        "mcp_rdf_agent": "mcp_rdf_agent",
        END: END
    }
)

workflow.add_edge(
    "vector_agent",
    "review_vector_answer"
)

workflow.add_conditional_edges(
    "review_vector_answer", 
    decide_after_vector_review, 
    {
        "cypher_agent": "cypher_agent", 
        "vector_reflection": "vector_reflection"
    }
)

workflow.add_edge(
    "vector_reflection",
    "vector_agent"
)

workflow.add_edge(
    "cypher_agent",
    "review_cypher_answer"
)

workflow.add_conditional_edges(
    "review_cypher_answer",
    decide_after_cypher_review,
    {
        "log_analysis_agent": "log_analysis_agent",
        "cypher_reflection": "cypher_reflection"
    }
)

workflow.add_edge(
    "cypher_reflection", 
    "cypher_agent"
)

workflow.add_conditional_edges(
    "log_analysis_agent",
    decide_after_log_analysis,
    {
        "mcp_rdf_agent": "mcp_rdf_agent",
        "synthesizer": "synthesizer"
    }
)

workflow.add_edge(
    "mcp_rdf_agent", 
    "synthesizer"
)

workflow.add_edge(
    "synthesizer", 
    END
)

# Compile graph
app = workflow.compile()