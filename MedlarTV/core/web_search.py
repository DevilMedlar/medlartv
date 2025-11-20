"""
MedlarTV Enhanced Search Integration
- DuckDuckGo for current web info (news, prices, events)
- Wikipedia for factual/encyclopedic information
Both 100% FREE, no API keys required
"""

print("[DEBUG enhanced_search] Loaded enhanced_search.py")

from duckduckgo_search import DDGS
import wikipediaapi
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

print("[DEBUG enhanced_search] Calling load_dotenv()")
load_dotenv()

# Configuration
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
ENABLE_WIKIPEDIA = os.getenv("ENABLE_WIKIPEDIA", "true").lower() == "true"
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "3"))
WIKIPEDIA_LANG = os.getenv("WIKIPEDIA_LANG", "en")

print(f"[DEBUG enhanced_search] ENABLE_WEB_SEARCH={ENABLE_WEB_SEARCH}")
print(f"[DEBUG enhanced_search] ENABLE_WIKIPEDIA={ENABLE_WIKIPEDIA}")
print(f"[DEBUG enhanced_search] WEB_SEARCH_MAX_RESULTS={WEB_SEARCH_MAX_RESULTS}")
print(f"[DEBUG enhanced_search] WIKIPEDIA_LANG={WIKIPEDIA_LANG}")

# Initialize Wikipedia API
print("[DEBUG enhanced_search] Initializing wikipediaapi.Wikipedia(...)")
wiki = wikipediaapi.Wikipedia(
    language=WIKIPEDIA_LANG,
    user_agent='MedlarTV/1.0 (Twitch Bot; Python/wikipediaapi)'
)
print("[DEBUG enhanced_search] Wikipedia API initialized")


def search_web(query: str, max_results: int = None) -> List[Dict]:
    """
    Search the web using DuckDuckGo (completely free, no API key).
    Best for: current events, news, prices, recent information
    
    Args:
        query: Search query string
        max_results: Maximum number of results (default: from env or 3)
    
    Returns:
        List of search results with title, body, and href
    """
    print(f"[DEBUG enhanced_search] search_web() called with query={query!r}, max_results={max_results!r}")

    if not ENABLE_WEB_SEARCH:
        print("[DEBUG enhanced_search] search_web() → web search disabled, returning []")
        print("[Web Search] Disabled in configuration")
        return []
    
    if max_results is None:
        max_results = WEB_SEARCH_MAX_RESULTS
        print(f"[DEBUG enhanced_search] search_web() max_results was None, using default={max_results}")

    try:
        print("[DEBUG enhanced_search] search_web() creating DDGS() context")
        with DDGS() as ddgs:
            print("[DEBUG enhanced_search] search_web() calling ddgs.text(...)")
            results = list(ddgs.text(query, max_results=max_results))
            print(f"[DEBUG enhanced_search] search_web() ddgs.text() returned {len(results)} results")
            print(f"[Web Search] Found {len(results)} results for: {query}")
            return results
    except Exception as e:
        print(f"[DEBUG enhanced_search] search_web() EXCEPTION: {e}")
        print(f"[Web Search] Error: {e}")
        return []


def search_wikipedia(query: str, sentences: int = 3) -> Optional[Dict]:
    """
    Search Wikipedia for factual/encyclopedic information.
    Best for: definitions, historical facts, general knowledge
    
    Args:
        query: Search term
        sentences: Number of sentences to include in summary (default: 3)
    
    Returns:
        Dict with title, summary, and url, or None if not found
    """
    print(f"[DEBUG enhanced_search] search_wikipedia() called with query={query!r}, sentences={sentences}")

    if not ENABLE_WIKIPEDIA:
        print("[DEBUG enhanced_search] search_wikipedia() → wikipedia disabled, returning None")
        print("[Wikipedia] Disabled in configuration")
        return None
    
    try:
        # Clean up query for Wikipedia
        print(f"[DEBUG enhanced_search] search_wikipedia() original query={query!r}")
        clean_query = query.replace("what is ", "").replace("who is ", "").replace("?", "").strip()
        clean_query = clean_query.title() if not clean_query.isupper() else clean_query
        print(f"[DEBUG enhanced_search] search_wikipedia() clean_query={clean_query!r}")
        
        # Try to get the page
        print(f"[DEBUG enhanced_search] search_wikipedia() calling wiki.page({clean_query!r})")
        page = wiki.page(clean_query)
        
        if not page.exists():
            print(f"[DEBUG enhanced_search] search_wikipedia() page.exists() is False for {clean_query!r}")
            print(f"[Wikipedia] Page '{clean_query}' not found")
            return None
        
        print(f"[DEBUG enhanced_search] search_wikipedia() page.exists() is True, title={page.title!r}")
        # Get summary (first N sentences)
        summary = page.summary
        print(f"[DEBUG enhanced_search] search_wikipedia() full summary length={len(summary)}")
        sentences_list = summary.split('. ')[:sentences]
        print(f"[DEBUG enhanced_search] search_wikipedia() sentences_list_len={len(sentences_list)}")
        short_summary = '. '.join(sentences_list) + ('.' if not sentences_list[-1].endswith('.') else '')
        print(f"[DEBUG enhanced_search] search_wikipedia() short_summary length={len(short_summary)}")
        
        result = {
            "title": page.title,
            "summary": short_summary,
            "url": page.fullurl,
            "exists": True
        }
        
        print(f"[DEBUG enhanced_search] search_wikipedia() returning result for title={page.title!r}")
        print(f"[Wikipedia] Found: {page.title}")
        return result
        
    except Exception as e:
        print(f"[DEBUG enhanced_search] search_wikipedia() EXCEPTION: {e}")
        print(f"[Wikipedia] Error: {e}")
        return None


def should_search_web(message: str) -> bool:
    """
    Determine if message needs WEB search (current/time-sensitive info).
    
    Returns True for:
    - Price queries (bitcoin price, cost of, how much)
    - Current events (today, latest, recent)
    - News (news about, update on)
    - Time references (2024, 2025, this year)
    """
    print(f"[DEBUG enhanced_search] should_search_web() called with message={message!r}")

    if not ENABLE_WEB_SEARCH:
        print("[DEBUG enhanced_search] should_search_web() → web search disabled, returning False")
        return False
    
    message_lower = message.lower()
    print(f"[DEBUG enhanced_search] should_search_web() message_lower={message_lower!r}")
    
    # Current/time-sensitive triggers
    web_triggers = [
        "price of", "cost of", "how much",
        "latest", "recent", "current", "today", "now",
        "news about", "update on",
        "2024", "2025", "this year", "this month",
        "stock price", "crypto", "bitcoin", "ethereum",
    ]
    
    match = any(trigger in message_lower for trigger in web_triggers)
    print(f"[DEBUG enhanced_search] should_search_web() matched_triggers={match}")
    return match


def should_search_wikipedia(message: str) -> bool:
    """
    Determine if message needs WIKIPEDIA search (factual/encyclopedic info).
    
    Returns True for:
    - Definition queries (what is, who is, define)
    - Historical queries (history of, who was)
    - General knowledge (tell me about, explain)
    """
    print(f"[DEBUG enhanced_search] should_search_wikipedia() called with message={message!r}")

    if not ENABLE_WIKIPEDIA:
        print("[DEBUG enhanced_search] should_search_wikipedia() → wikipedia disabled, returning False")
        return False
    
    message_lower = message.lower()
    print(f"[DEBUG enhanced_search] should_search_wikipedia() message_lower={message_lower!r}")
    
    # Encyclopedic/factual triggers
    wiki_triggers = [
        "what is", "who is", "who was", "what was",
        "define", "definition of",
        "tell me about", "explain",
        "history of", "facts about",
        "information about",
    ]
    
    # Avoid if it's clearly current/time-sensitive
    if should_search_web(message):
        print("[DEBUG enhanced_search] should_search_wikipedia() → should_search_web() is True, returning False")
        return False
    
    match = any(trigger in message_lower for trigger in wiki_triggers)
    print(f"[DEBUG enhanced_search] should_search_wikipedia() matched_triggers={match}")
    return match


def search_intelligently(query: str) -> str:
    """
    Intelligently choose between web search, Wikipedia, or both.
    
    Strategy:
    1. Check if question is about current/time-sensitive info → Web search
    2. Check if question is about facts/definitions → Wikipedia
    3. For general questions ending in "?" → Try web search
    4. Combine both if relevant
    
    Args:
        query: User's message/question
    
    Returns:
        Formatted search context string (empty if no results)
    """
    print(f"[DEBUG enhanced_search] search_intelligently() called with query={query!r}")

    context_parts = []
    
    # Check if we should search Wikipedia
    wiki_flag = should_search_wikipedia(query)
    print(f"[DEBUG enhanced_search] search_intelligently() should_search_wikipedia={wiki_flag}")
    if wiki_flag:
        print(f"[DEBUG enhanced_search] search_intelligently() → Trying Wikipedia for: {query}")
        print(f"[Smart Search] Trying Wikipedia for: {query}")
        wiki_result = search_wikipedia(query)
        if wiki_result:
            print("[DEBUG enhanced_search] search_intelligently() wiki_result found, adding to context_parts")
            context_parts.append("WIKIPEDIA INFORMATION:\n")
            context_parts.append(f"Title: {wiki_result['title']}\n")
            context_parts.append(f"Summary: {wiki_result['summary']}\n")
            context_parts.append(f"Source: {wiki_result['url']}\n")
        else:
            print("[DEBUG enhanced_search] search_intelligently() wiki_result is None")
    
    # Check if we should search the web
    web_flag = should_search_web(query)
    print(f"[DEBUG enhanced_search] search_intelligently() should_search_web={web_flag}")
    if web_flag:
        print(f"[DEBUG enhanced_search] search_intelligently() → Trying Web Search for: {query}")
        print(f"[Smart Search] Trying Web Search for: {query}")
        web_results = search_web(query, max_results=3)
        if web_results:
            print(f"[DEBUG enhanced_search] search_intelligently() web_results count={len(web_results)}")
            if context_parts:
                context_parts.append("\n")
            context_parts.append("CURRENT WEB INFORMATION:\n")
            for i, result in enumerate(web_results, 1):
                title = result.get('title', 'N/A')
                body = result.get('body', result.get('description', 'N/A'))
                print(f"[DEBUG enhanced_search] search_intelligently() adding web result {i}: title={title!r}")
                context_parts.append(f"[Result {i}] {title}\n{body}\n\n")
        else:
            print("[DEBUG enhanced_search] search_intelligently() web_results is empty or None")
    
    # If we found nothing but it's a question, try a general web search
    if not context_parts and "?" in query:
        print(f"[DEBUG enhanced_search] search_intelligently() → no context yet and query is question, fallback web search")
        print(f"[Smart Search] Fallback web search for: {query}")
        web_results = search_web(query, max_results=2)
        if web_results:
            print(f"[DEBUG enhanced_search] search_intelligently() fallback web_results count={len(web_results)}")
            context_parts.append("WEB SEARCH RESULTS:\n")
            for i, result in enumerate(web_results, 1):
                title = result.get('title', 'N/A')
                body = result.get('body', 'N/A')
                print(f"[DEBUG enhanced_search] search_intelligently() adding fallback result {i}: title={title!r}")
                context_parts.append(f"{title}: {body}\n")
        else:
            print("[DEBUG enhanced_search] search_intelligently() fallback web_results is empty or None")
    
    if context_parts:
        full_context = "".join(context_parts)
        print(f"[DEBUG enhanced_search] search_intelligently() built context length before footer={len(full_context)}")
        full_context += "\n---\nIMPORTANT: Use the above information to provide an accurate answer. Keep it concise and conversational for Twitch chat (1-2 sentences max)."
        print(f"[DEBUG enhanced_search] search_intelligently() final context length={len(full_context)}")
        return full_context
    
    print("[DEBUG enhanced_search] search_intelligently() no context generated, returning empty string")
    return ""


def search_news(query: str, max_results: int = None) -> List[Dict]:
    """
    Search recent news articles using DuckDuckGo News.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (default: from env or 3)
    
    Returns:
        List of news results
    """
    print(f"[DEBUG enhanced_search] search_news() called with query={query!r}, max_results={max_results!r}")

    if not ENABLE_WEB_SEARCH:
        print("[DEBUG enhanced_search] search_news() → web search disabled, returning []")
        return []
    
    if max_results is None:
        max_results = WEB_SEARCH_MAX_RESULTS
        print(f"[DEBUG enhanced_search] search_news() max_results was None, using default={max_results}")
    
    try:
        print("[DEBUG enhanced_search] search_news() creating DDGS() context")
        with DDGS() as ddgs:
            print("[DEBUG enhanced_search] search_news() calling ddgs.news(...)")
            results = list(ddgs.news(query, max_results=max_results))
            print(f"[DEBUG enhanced_search] search_news() ddgs.news() returned {len(results)} results")
            print(f"[News Search] Found {len(results)} articles for: {query}")
            return results
    except Exception as e:
        print(f"[DEBUG enhanced_search] search_news() EXCEPTION: {e}")
        print(f"[News Search] Error: {e}")
        return []


def format_search_context(results: List[Dict], query: str = "") -> str:
    """
    Format web search results into context string for LLM.
    
    Args:
        results: List of search result dictionaries
        query: Original search query (optional)
    
    Returns:
        Formatted string with search results
    """
    print(f"[DEBUG enhanced_search] format_search_context() called with results_len={len(results)}, query={query!r}")

    if not results:
        print("[DEBUG enhanced_search] format_search_context() results empty, returning fallback message")
        return "No relevant search results found."
    
    context = "CURRENT WEB INFORMATION:\n"
    if query:
        context += f"Search Query: {query}\n"
    context += "\n"
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'N/A')
        body = result.get('body', result.get('description', 'N/A'))
        href = result.get('href', '')
        
        print(f"[DEBUG enhanced_search] format_search_context() result {i}: title={title!r}, href={href!r}")
        context += f"[Result {i}]\n"
        context += f"Title: {title}\n"
        context += f"Content: {body}\n"
        if href:
            context += f"Source: {href}\n"
        context += "\n"
    
    context += "Use this information to provide an accurate, current answer.\n"
    print(f"[DEBUG enhanced_search] format_search_context() final context length={len(context)}")
    
    return context.strip()


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("Testing MedlarTV Enhanced Search (Web + Wikipedia)")
    print("=" * 60)
    
    # Test 1: Wikipedia
    print("\n=== Test 1: Wikipedia Search ===")
    wiki_test = "Artificial Intelligence"
    print(f"Query: {wiki_test}")
    result = search_wikipedia(wiki_test)
    if result:
        print(f"✅ Found: {result['title']}")
        print(f"Summary: {result['summary'][:150]}...")
        print(f"URL: {result['url']}")
    else:
        print("❌ No Wikipedia result")
    
    # Test 2: Web Search
    print("\n=== Test 2: Web Search (Current Info) ===")
    web_test = "Bitcoin price today"
    print(f"Query: {web_test}")
    results = search_web(web_test, max_results=2)
    if results:
        print(f"✅ Found {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.get('title', 'N/A')[:60]}...")
    else:
        print("❌ No web results")
    
    # Test 3: Smart Search (Factual)
    print("\n=== Test 3: Smart Search (Factual) ===")
    smart_test_1 = "what is quantum computing"
    print(f"Query: {smart_test_1}")
    print(f"Should use Wikipedia? {should_search_wikipedia(smart_test_1)}")
    print(f"Should use Web? {should_search_web(smart_test_1)}")
    context = search_intelligently(smart_test_1)
    if context:
        print(f"✅ Generated context ({len(context)} chars)")
        print(context[:200] + "...")
    else:
        print("❌ No context generated")
    
    # Test 4: Smart Search (Current)
    print("\n=== Test 4: Smart Search (Current Info) ===")
    smart_test_2 = "latest news about AI"
    print(f"Query: {smart_test_2}")
    print(f"Should use Wikipedia? {should_search_wikipedia(smart_test_2)}")
    print(f"Should use Web? {should_search_web(smart_test_2)}")
    context2 = search_intelligently(smart_test_2)
    if context2:
        print(f"✅ Generated context ({len(context2)} chars)")
    else:
        print("❌ No context generated")
    
    # Test 5: Trigger Detection
    print("\n=== Test 5: Trigger Detection ===")
    test_queries = [
        "what is python?",           # Should trigger Wikipedia
        "price of ethereum today?",  # Should trigger Web
        "how are you?",              # Should trigger neither
        "who was Albert Einstein?",  # Should trigger Wikipedia
        "latest bitcoin news",       # Should trigger Web
    ]
    
    for q in test_queries:
        wiki_flag = "✅" if should_search_wikipedia(q) else "❌"
        web_flag = "✅" if should_search_web(q) else "❌"
        print(f"  '{q[:30]:30}' → Wiki:{wiki_flag} Web:{web_flag}")
    
    print("\n" + "=" * 60)
    print("✅ Enhanced Search tests complete!")
    print("=" * 60)
