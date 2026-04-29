from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from src.config.settings import llm

class LogAnalysisOutput(BaseModel):
    """
    Output model for the log analysis agent
    """
    decision: Literal["cskg_required", "cskg_not_required"] = Field(description="Checks if in-depth analysis with cybersecurity knowledge is required")
    log_summary: str = Field(description="A concise summary of the findings from the log data that answers the original question.")
    
    # PERBAIKAN 1: Tegaskan di Pydantic agar pertanyaan digeneralisasi
    generated_question: str = Field(description="A GENERALIZED question for a cybersecurity knowledge base. MUST NOT contain local entities like user names, IP addresses, or hostnames. Focus only on general attack patterns, techniques, or mitigations.")

log_analysis_prompt = ChatPromptTemplate.from_messages([
    (
        "system", 
        """You are a security analyst expert. You have received structured and unstructured data from system logs.
        Your tasks are:
        1.  Summarize the findings from the provided log context to directly answer the user's original question.
        2.  Based on the user's original question, determine whether it requires further analysis with cybersecurity knowledge base. 
        3.  return 'cskg_required' if the user's original question requires further analysis with cybersecurity knowledgebase. Return 'cskg_not_required' if it does not. 
        
        # PERBAIKAN 2: Instruksi ketat (Guardrails) untuk anonymization pertanyaan
        4.  If generating a question for the cybersecurity knowledge base, it MUST BE ANONYMIZED AND GENERALIZED. 
            - DO NOT include specific local entities such as user names (e.g., 'Daryl', 'danette'), hostnames (e.g., 'Mail-0'), or IP addresses (e.g., '127.0.0.1').
            - Translate the specific log findings into general cybersecurity concepts.
            - Example Bad Question: 'What attack pattern is user Daryl doing on Mail-0?'
            - Example Good Question: 'What are the common attack patterns associated with repeated authentication failures, and what are the recommended mitigations?'
        """
    ),
    (
        "human", 
        """
        Original Question: {original_question}

        Context from Vector Search:
        {log_vector_context}

        Context from Cypher Query:
        {log_cypher_context}

        Based on the provided context, perform your tasks.
        """
    ),
])
log_analysis_chain = log_analysis_prompt | llm.with_structured_output(LogAnalysisOutput)