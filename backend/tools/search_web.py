import urllib.request
import urllib.parse
import json

def execute(query: str, max_results: int = 3) -> str:
    \"\"\"
    Search the web using DuckDuckGo Instant Answer API.
    \"\"\"
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'MultiAgentOrchestrator/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return "No web results found."
            
            data = json.loads(response.read().decode())
            results = []
            
            if 'RelatedTopics' in data and isinstance(data['RelatedTopics'], list):
                for topic in data['RelatedTopics'][:max_results]:
                    if 'Text' in topic and 'FirstURL' in topic:
                        title = topic['Text'].split(' - ')[0] if ' - ' in topic['Text'] else topic['Text'][:60]
                        results.append(f"Title: {title}\\nSnippet: {topic['Text']}\\nURL: {topic['FirstURL']}")
            
            if not results and data.get('Abstract'):
                title = data.get('Heading', query)
                results.append(f"Title: {title}\\nSnippet: {data['Abstract']}\\nURL: {data.get('AbstractURL', '')}")
            
            if not results:
                return "No web results found."
            
            return "\\n\\n".join(results)
    except Exception as e:
        return f"Error executing search: {str(e)}"
