import os
import json
import logging
import torch

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

from search_utils import (
    infer_field_of_study,
    infer_education_level,
    extract_gpa_requirement,
    infer_demographics
)

logger = logging.getLogger(__name__)

# --- LlamaIndex Configuration ---
RAG_DATA_DIR_NAME = "data" # The name of the directory containing JSON files
RAG_DATA_DIR = None # Will be set in initialize_rag_system_on_startup
RAG_PERSIST_DIR = None
RAG_EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RAG_LLM_API_BASE = "https://api.together.xyz/v1"

DEFAULT_PLACEHOLDER_API_KEY = ""
RAG_LLM_API_KEY = os.environ.get("TOGETHER_API_KEY", DEFAULT_PLACEHOLDER_API_KEY)
RAG_LLM_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# --- Global LlamaIndex Variables ---
rag_index = None
rag_query_engine = None
RAG_INITIALIZED_SUCCESSFULLY = False

def initialize_rag_system_on_startup(base_dir):
    global rag_index, rag_query_engine, RAG_INITIALIZED_SUCCESSFULLY
    global RAG_DATA_DIR, RAG_PERSIST_DIR

    RAG_DATA_DIR = os.path.join(base_dir, RAG_DATA_DIR_NAME) 
    RAG_PERSIST_DIR = os.path.join(base_dir, "storage_ai_advisor")

    logger.info(f"Attempting to initialize RAG system with data from: {RAG_DATA_DIR}")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device for RAG embedding: {device}")

        Settings.embed_model = HuggingFaceEmbedding(
            model_name=RAG_EMBED_MODEL_NAME,
            device=device
        )
        logger.info(f"RAG Embedding model ({RAG_EMBED_MODEL_NAME}) initialized.")

        using_default_fallback_key = (RAG_LLM_API_KEY == DEFAULT_PLACEHOLDER_API_KEY)
        env_var_was_set = "TOGETHER_API_KEY" in os.environ

        if not RAG_LLM_API_KEY:
             logger.error("CRITICAL: LLM API Key is completely missing. AI Advisor will not function. Please set TOGETHER_API_KEY.")
             RAG_INITIALIZED_SUCCESSFULLY = False
             return
        elif using_default_fallback_key and not env_var_was_set:
            logger.warning("TOGETHER_API_KEY env var NOT SET. Using default placeholder API key. AI Advisor may be non-functional.")
        elif using_default_fallback_key and env_var_was_set:
            logger.warning("TOGETHER_API_KEY env var IS SET, but to the default placeholder. Use your own valid API key for reliability.")

        Settings.llm = OpenAILike(
            api_base=RAG_LLM_API_BASE,
            api_key=RAG_LLM_API_KEY,
            model=RAG_LLM_MODEL_NAME,
            is_chat_model=True,
        )
        logger.info(f"RAG LLM ({RAG_LLM_MODEL_NAME}) initialized.")

        if not os.path.exists(RAG_PERSIST_DIR):
            logger.info(f"RAG persistent storage not found at {RAG_PERSIST_DIR}. Creating new index.")
            if not os.path.exists(RAG_DATA_DIR) or not os.listdir(RAG_DATA_DIR):
                logger.error(f"RAG_DATA_DIR '{RAG_DATA_DIR}' is empty or does not exist. It should contain your JSON data files.")
                RAG_INITIALIZED_SUCCESSFULLY = False
                return
            
            documents = SimpleDirectoryReader(RAG_DATA_DIR).load_data()
            if not documents:
                logger.error(f"No documents loaded from '{RAG_DATA_DIR}'. Check if JSON files are present and readable.")
                RAG_INITIALIZED_SUCCESSFULLY = False
                return
            
            logger.info(f"Loaded {len(documents)} document(s) for RAG index from {RAG_DATA_DIR}.")
            
            rag_index = VectorStoreIndex.from_documents(documents, show_progress=True)
            rag_index.storage_context.persist(persist_dir=RAG_PERSIST_DIR)
            logger.info(f"RAG Index created and persisted to {RAG_PERSIST_DIR}.")
        else:
            logger.info(f"Loading RAG index from {RAG_PERSIST_DIR}...")
            storage_context = StorageContext.from_defaults(persist_dir=RAG_PERSIST_DIR)
            rag_index = load_index_from_storage(storage_context)
            logger.info("RAG Index loaded.")

        if rag_index:
            rag_query_engine = rag_index.as_query_engine()
            logger.info("RAG Query Engine created.")
            RAG_INITIALIZED_SUCCESSFULLY = True
            logger.info("RAG system initialization complete. RAG_INITIALIZED_SUCCESSFULLY is True.")
        else:
            logger.error("RAG index is None, cannot create query engine.")
            RAG_INITIALIZED_SUCCESSFULLY = False
            logger.error("RAG system initialization failed (index is None).")

    except Exception as e:
        logger.exception(f"Error initializing RAG system: {e}")
        RAG_INITIALIZED_SUCCESSFULLY = False
        logger.error(f"RAG system initialization failed (Exception). Error: {e}")


def handle_ai_chat(user_message, conversation_history_from_client, db_instance):
    global rag_query_engine 

    if not RAG_INITIALIZED_SUCCESSFULLY or not rag_query_engine:
        logger.error("AI Chat Handler: RAG query engine not available.")
        ai_response = "I'm sorry, my AI advisory capabilities are currently unavailable."
        updated_history = list(conversation_history_from_client)
        updated_history.append({"role": "user", "content": user_message}) 
        updated_history.append({"role": "assistant", "content": ai_response})
        return ai_response, [], updated_history[-12:] 

    current_conversation_history = list(conversation_history_from_client)
    current_conversation_history.append({"role": "user", "content": user_message})
    
    # System prompt focused on direct recommendations (similar to the one in the provided app.py)
    system_prompt = (
        "You are ScholarshipGPT, an efficient AI scholarship advisor. Your goal is to quickly understand students' needs and provide direct, actionable scholarship recommendations from your KNOWLEDGE BASE.\n\n"
        "RESPONSE GUIDELINES:\n"
        "1. Be CONCISE and DIRECT - avoid lengthy explanations unless specifically asked.\n"
        "2. When you have enough info about a student (e.g., field, level, GPA) AND they ask for scholarships, immediately search your KNOWLEDGE BASE and recommend scholarships.\n"
        "3. If a student mentions their field of study, education level, and explicitly asks for scholarships or funding, provide recommendations from your KNOWLEDGE BASE right away.\n"
        "4. Only ask clarifying questions if you truly need critical missing information to perform a search. If they ask for scholarships, prioritize that.\n"
        "5. Focus on being helpful rather than overly conversational if the user is trying to get recommendations.\n\n"
        
        "RECOMMENDATION TRIGGER:\n"
        "If the user mentions:\n"
        "- Their field of study (engineering, business, etc.)\n"
        "- Education level (high school, college, graduate)\n"
        "- AND any explicit request for scholarships/money/funding/recommendations\n"
        "→ IMMEDIATELY provide scholarship recommendations from your KNOWLEDGE BASE using the special format below.\n\n"
        
        "SCHOLARSHIP RECOMMENDATION FORMAT:\n"
        "When you find relevant scholarships in your KNOWLEDGE BASE, you MUST respond with:\n"
        "'RECOMMENDATION_MODE_ACTIVATED: [Exact Scholarship Title 1 from Knowledge Base]; [Exact Scholarship Title 2 from Knowledge Base]; [Exact Scholarship Title 3 from Knowledge Base]'\n"
        "Use the EXACT titles from your KNOWLEDGE BASE. Do NOT add any extra text before or after this special response.\n"
        "If your KNOWLEDGE BASE has NO matching scholarships, respond naturally and explain that you couldn't find matches for their current query in your data, and perhaps suggest they broaden their search or provide more details.\n\n"
        
        "CONVERSATION EXAMPLES:\n"
        "User: 'I study computer science, am a junior, and need scholarships.'\n"
        "You: (Search KNOWLEDGE BASE for 'computer science', 'junior' scholarships) 'RECOMMENDATION_MODE_ACTIVATED: CS Junior Grant; Tech Innovators Scholarship'\n\n"
        
        "User: 'What scholarships are available for high school business students?'\n"
        "You: (Search KNOWLEDGE BASE for 'high school', 'business' scholarships) 'RECOMMENDATION_MODE_ACTIVATED: Young Entrepreneurs Award; Future Business Leaders Grant'\n\n"
        
        "User: 'I have a 3.0 GPA.'\n"
        "You: 'Thanks for sharing your GPA. What field are you studying and what's your education level? This will help me find relevant scholarships for you.' (Asking for more info because no explicit scholarship request yet or insufficient info for a targeted search)\n\n"

        "User: 'Any scholarships for me?' (User has previously mentioned they are a HS junior, CS major, 3.0 GPA)\n"
        "You: (Search KNOWLEDGE BASE based on all known info) 'RECOMMENDATION_MODE_ACTIVATED: STEM HS Scholarship; Coding Challenge Prize'\n\n"
        
        "Only engage in extended conversation if the user specifically asks questions about scholarship applications, requirements, or tips AFTER seeing recommendations, or if they are not directly asking for scholarships yet."
    )

    prompt_for_rag = f"{system_prompt}\n\nConversation History (most recent first for context):\n"
    for turn in current_conversation_history[-12:]: 
        prompt_for_rag += f"{turn['role'].capitalize()}: {turn['content']}\n"
    
    # Logic to potentially force RECOMMENDATION_MODE_ACTIVATED based on keywords
    user_lower = user_message.lower()
    direct_request_keywords = ['recommend', 'show me', 'find', 'give me', 'want', 'need', 'looking for', 'scholarships', 'scholarship', 'scholerships', 'scholership']
    # Check if user history contains field/level info already.
    # This is a simplified check; a more robust way would be to use an NER model or regex to extract entities from history.
    history_text_lower = " ".join([turn['content'].lower() for turn in current_conversation_history[:-1]]) # Exclude current message
    
    has_field_info_history = any(field in history_text_lower for field in ['engineering', 'computer', 'business', 'science', 'art', 'medical', 'cs', 'ai'])
    has_level_info_history = any(level in history_text_lower for level in ['high school', 'undergraduate', 'graduate', 'college', 'junior', 'senior', 'freshman', 'sophomore', 'hs'])

    has_field_info_current = any(field in user_lower for field in ['engineering', 'computer', 'business', 'science', 'art', 'medical', 'cs', 'ai'])
    has_level_info_current = any(level in user_lower for level in ['high school', 'undergraduate', 'graduate', 'college', 'junior', 'senior', 'freshman', 'sophomore', 'hs'])

    # Trigger recommendation if current message asks for scholarships AND (current message has field/level OR history has field/level)
    should_force_recommendation = False
    if any(keyword in user_lower for keyword in direct_request_keywords):
        if (has_field_info_current or has_field_info_history) and \
           (has_level_info_current or has_level_info_history):
            should_force_recommendation = True
        elif "any" in user_lower and (has_field_info_history or has_level_info_history): # e.g. "any cs ones?"
             should_force_recommendation = True


    if should_force_recommendation:
        prompt_for_rag += f"\nIMPORTANT: The user is requesting direct scholarship recommendations based on their profile (possibly detailed in history). Provide specific scholarships from your KNOWLEDGE BASE using the RECOMMENDATION_MODE_ACTIVATED format. Use all available information from the conversation history to find the best matches.\n"
    
    prompt_for_rag += f"\nUser's latest message: {user_message}\nScholarshipGPT response:"

    logger.info(f"Querying RAG with prompt for: {user_message[:100]}...")
    logger.debug(f"Full query for LLM (first 500 chars): {prompt_for_rag[:500]}")
    
    ai_response_text = ""
    scholarships_to_send = []

    try:
        ai_raw_response = rag_query_engine.query(prompt_for_rag)
        ai_response_text = str(ai_raw_response).strip()
        logger.info(f"LLM Raw Response: {ai_response_text[:300]}...")

    except Exception as e:
        logger.error(f"Error during RAG query or LLM call: {e}", exc_info=True)
        error_message = "I encountered an issue trying to process your request. Please try rephrasing or try again."
        if "API key" in str(e).lower() or "authentication" in str(e).lower():
             error_message = "I'm having trouble connecting to my knowledge base due to an API configuration issue. Please contact support."
        current_conversation_history.append({"role": "assistant", "content": error_message})
        return error_message, [], current_conversation_history[-12:]

    if ai_response_text.startswith("RECOMMENDATION_MODE_ACTIVATED:"):
        titles_str = ai_response_text.replace("RECOMMENDATION_MODE_ACTIVATED:", "").strip()
        scholarship_titles = [title.strip() for title in titles_str.split(';') if title.strip()] 
        
        logger.info(f"LLM recommended titles: {scholarship_titles}")
        
        if not scholarship_titles:
            logger.warning("RECOMMENDATION_MODE_ACTIVATED but no specific titles were provided by LLM.")
            ai_response_text = "I tried to find scholarships based on our conversation, but I couldn't list specific titles right now. Could you provide a bit more detail, or perhaps try a broader search on the 'Search' page?"
        else:
            conn = None
            found_scholarships_data = []
            try:
                conn = db_instance.get_connection()
                cursor = conn.cursor()
                added_scholarship_ids = set() 

                for title in scholarship_titles:
                    cursor.execute('SELECT * FROM scholarships WHERE LOWER(title) = ? LIMIT 1', (title.lower(),))
                    scholarship_row = cursor.fetchone()
                    
                    if not scholarship_row:
                        logger.debug(f"Exact match for '{title}' failed, trying LIKE '%{title}%'.")
                        cursor.execute('SELECT * FROM scholarships WHERE LOWER(title) LIKE ? LIMIT 1', (f'%{title.lower()}%',))
                        scholarship_row = cursor.fetchone()

                    if not scholarship_row and len(title.split()) > 1: 
                         first_word = title.split()[0].lower()
                         last_word = title.split()[-1].lower()
                         shorter_title_search = f"%{first_word}%{last_word}%" 
                         logger.debug(f"LIKE match for '{title}' failed, trying more flexible LIKE '{shorter_title_search}'.")
                         cursor.execute('SELECT * FROM scholarships WHERE LOWER(title) LIKE ? LIMIT 1', (shorter_title_search,))
                         scholarship_row = cursor.fetchone()
                    
                    if scholarship_row:
                        s_dict = dict(scholarship_row)
                        if s_dict['id'] not in added_scholarship_ids: 
                            try: s_dict['requirements_structured'] = json.loads(s_dict.get('requirements_structured_json', '{}') or '{}')
                            except (json.JSONDecodeError, TypeError): s_dict['requirements_structured'] = {}
                            try: s_dict['keywords'] = json.loads(s_dict.get('keywords_json', '[]') or '[]')
                            except (json.JSONDecodeError, TypeError): s_dict['keywords'] = []
                            
                            s_dict['field_of_study'] = infer_field_of_study(s_dict)
                            s_dict['education_level'] = infer_education_level(s_dict)
                            s_dict['gpa_requirement'] = extract_gpa_requirement(s_dict)
                            s_dict['demographic_requirements'] = infer_demographics(s_dict)
                            found_scholarships_data.append(s_dict)
                            added_scholarship_ids.add(s_dict['id'])
                        else:
                            logger.info(f"Skipping duplicate scholarship ID {s_dict['id']} for title '{title}'")
                    else:
                        logger.warning(f"Could not find scholarship in DB matching title from LLM: '{title}' (tried exact, LIKE, and flexible LIKE).")
            except Exception as db_exc:
                logger.error(f"Database error during scholarship retrieval: {db_exc}", exc_info=True)
                ai_response_text = "I encountered a database issue while trying to fetch scholarship details. Please try again later."
            finally:
                if conn:
                    conn.close()
            
            if found_scholarships_data:
                scholarships_to_send = found_scholarships_data
                ai_response_text = f"Found {len(found_scholarships_data)} scholarships that match your profile:" # Matches the one in provided app.py
            else: 
                logger.warning(f"LLM recommended titles {scholarship_titles} but NONE were found in DB despite search attempts.")
                ai_response_text = "I found some potential matches, but couldn't retrieve the full details right now. Please try searching by field of study or try again." # Matches the one in provided app.py
    
    elif not ai_response_text.startswith("RECOMMENDATION_MODE_ACTIVATED:"):
        logger.info("LLM responded conversationally (did not use RECOMMENDATION_MODE_ACTIVATED).")

    if not ai_response_text: 
        logger.warning("AI response text was empty after all processing, providing a generic fallback.")
        ai_response_text = "I'm not sure how to respond to that. Could you try rephrasing or asking something else?"

    current_conversation_history.append({"role": "assistant", "content": ai_response_text})
    
    return ai_response_text, scholarships_to_send, current_conversation_history[-12:]