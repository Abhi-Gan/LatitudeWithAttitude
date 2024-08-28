## WordMap

The use of traditional search engines for education (especially self-education) is flawed by design; Traditional search engines (e.g. Google, Bing) and recommendation systems (e.g. YouTube recommendations, social media feeds) are optimized to retrieve content based on similarity. This hinders the spread of knowledge that emphasizes connections to different events across space and time, or explores diverse perspectives.
 
The consequences are dire. Today's increasingly polarized landscape exacerbated by the use of these traditional systems (especially in social media) is a call to action to provide a better means to obtain knowledge.
 
Therefore, we present WordMap, an interactive educational web application that utilizes LLM's curated to present answers to user queries with critical analysis and a global context. This is a powerful tool, especially for uncovering the connections between historical events that may have less obvious relationships.
 
By providing a visual interface (web map) that display relevant historical locations and images to convey knowledge visually, we also address the shortcomings of LLM's as an educational tool.

## How it works

The user's query is put into a prompt that is engineered such that the LLM's (GPT-3.5 Turbo) response provides information relevant to the query in a global context and explores different points of views. We then perform Entity Extraction of events from this response via another prompt to an LLM (GPT-3.5 Turbo). Geocoding is performed to convert the natural language locations of these events into points that are displayed on the interactive map. The user can then search for new queries or double click on a point on the map to learn more about that event.
