from flask import Flask, request, jsonify

# openai stuff
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

import json
import itertools

import copy

# GIS
from arcgis.geocoding import geocode, batch_geocode, get_geocoders
from arcgis.gis import GIS

# initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# we want to use this model
OPENAI_MODEL = "gpt-3.5-turbo-0125"

# initialize gis
gis = GIS()

app = Flask(__name__)


def get_llm_response(prompt):
    chat_response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", 
             "content": prompt} 
        ],
        n=1,
        temperature=0.6
    )

    llm_response_json = None
    try:
        llm_response_json = json.loads(chat_response.choices[0].message.content)
    except Exception as e:
        print(f"error parsing LLM response to prompt '{prompt}'!\nResponse:{llm_response_json}\nError:{e}")

    return llm_response_json

# gets more detailed info abt this event
def refine_query(query):
    refined_query_prompt = \
f"""In 1-3 paragraphs, describe events/movements related to the prompt '{query}'. Address causation, continuity and change over time, and impacts from various perspectives.

Then, provide information about relevant historical events.
Be specific about events and locations. Have a transnational approach and try to make connections to other geographical places/groups.

For each event, provide information in the following format:
{{
    "tag line": <brief description of event>,
    "locations" [list of relevant cities/states/regions/addresses to this event],
    "start date": <approximate start date of this event in YYYY-MM-DD format>
    "end date": <approximate end date of this event in YYYY-MM-DD format>
    "query": <search query that can be used to find relevant images *safe for work*> 
}}

Format your answer like so:
{{
    "answer": <answer>,
    "query": <search query that can be used to find relevant images to your answer *safe for work*> 
    "events": [relevant events]
}}
"""
    
    return get_llm_response(refined_query_prompt)


def expand_query(query):
    expand_query_prompt = \
f"""Write 1-3 paragraphs about the query '{query}' in the context of global events/movements in other geographical locations that have a direct relationship to it. 
In your response, do the following:
    - Use a transnational perspective to produce a global contextualization of '{query}' and its impacts
    - Explain the connections to argue a central theme. 
    - try to discuss related events important to a variety of fields - history, technology, arts, psychology, economics, etc.

Then, provide information about relevant historical events. Establish the connections between these events and the initial query in your paragraphs.
Be specific about events and locations. Have a transnational approach and try to make connections to other geographical places/groups.

For each event, provide information in the following format:
{{
    "tag line": <brief description of event>,
    "locations" [list of specific singular cities/states/regions relevant to this event.],
    "start date": <approximate start date of this event in YYYY-MM-DD format>
    "end date": <approximate end date of this event in YYYY-MM-DD format>
    "query": <search query that can be used to find relevant images *safe for work*> 
}}
Ensure each entry in your list of locations can be geocoded.

Format your answer like so:
{{
    "answer": <answer>,
    "query": <search query that can be used to find relevant images to your answer *safe for work*> 
    "events": [relevant events]
}}
"""
    
    return get_llm_response(expand_query_prompt)

def expand_compact_dict(combined_locs_data):
    out_list = []
    for curDict in combined_locs_data:
        if not isinstance(curDict, str):
            print(curDict)
            for nl_loc in curDict["locations"]:
                copiedDict = copy.deepcopy(curDict)
                del copiedDict["locations"]
                copiedDict["location"] = nl_loc
                x_y_loc = geocode(nl_loc, max_locations=1, out_fields="location")[0]['location']
                copiedDict['x_loc'] = x_y_loc['x']
                copiedDict['y_loc'] = x_y_loc['y']

                out_list.append(copiedDict)
    return out_list


@app.route('/historyQuery', methods=['POST'])
def historyQuery():
    data = request.get_json()
    query_str = data['query']

    refine_response = refine_query(query_str)
    print(refine_response)
    refine_response["events"] = expand_compact_dict(refine_response["events"])

    expand_response = expand_query(query_str)
    print(expand_response)
    expand_response["events"] = expand_compact_dict(expand_response["events"])

    # combine the two strings to display on the right?
    result = {
        "refine_response": refine_response,
        "expand_response": expand_response
    }

    return jsonify(result)

    # return jsonify({"message": "data received"})

if __name__ == '__main__':
    app.run(debug=True)
