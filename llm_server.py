from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
# openai stuff
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

import json
import itertools

import copy

# scraping images
import requests
from bs4 import BeautifulSoup

# GIS
from arcgis.geocoding import geocode, batch_geocode, get_geocoders
from arcgis.gis import GIS

# mock waiting
import time

ESRI_API_KEY = os.getenv('ESRI_API_KEY_UNSAFE')
# initialize GIS
gis = GIS(api_key=ESRI_API_KEY)
geocoder = get_geocoders(gis)[0]

# initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

# SWITCH TO TURN ON / OFF MOCK DATA
USE_MOCK_DATA = True or (OPENAI_API_KEY is None)
# SWITCH TO TURN ON IMAGE SCRAPING
SCRAPE_IMAGES = True

# we want to use this model
OPENAI_MODEL = "gpt-3.5-turbo-0125"

app = Flask(__name__)
CORS(app)

# max num imgs we care abt
MAX_IMGS = 10

def get_llm_response(prompt, as_json=False):
    chat_response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", 
             "content": prompt} 
        ],
        n=1,
        temperature=0.6
    )

    llm_response_str = chat_response.choices[0].message.content
    
    if not as_json:
        return llm_response_str
    else: # convert to json
        llm_response_json = None
        try:
            llm_response_json = json.loads(llm_response_str)
        except Exception as e:
            print(f"error parsing LLM response to prompt '{prompt}'!\nResponse:{llm_response_str}\nError:{e}")

        return llm_response_json
    
def discuss_topic(query):
    expand_refine_prompt = \
f"""Tell me about '{query}'
In your response, do the following:
    - contextualize it in a broader global history to make lesser discussed connections to other events
    - draw parallels to other events across space and time
    - Have a transnational approach and try to make connections to other geographical places/groups.
    - Explain the connections to argue a central theme that contends or slightly differs from the dominant narrative.

For example:
- in a response to a query about operation babylift you can discuss the details of the event but also its connection to a continuity in US disregard to the lives of those on the Philippines and Pacific Islands that were essential for this mission. Then you could make connections to the Philippine American War and Nuclear Testing on Bikini Atoll.
- in a response to a query about the Khmer Rouge you can discuss it in the context of the Vietnam War, and make a connection to the future US policy and civilian backlash in Afghanistan.
"""
    return get_llm_response(expand_refine_prompt, as_json=False)

def get_related_events(paragraph_response):
    relev_events_prompt = f"""Provide the described information for relevant historical events to the following paragraph:
```
{paragraph_response}
```

For each event, provide information in the following json format:
{{
    "tag line": <brief description of event>,
    "locations" [list of relevant cities/states/regions/addresses to this event],
    "start date": <approximate start date of this event in YYYY-MM-DD format>
    "end date": <approximate end date of this event in YYYY-MM-DD format>
    "query": <search query that can be used to find relevant images *safe for work*> 
}}
Be specific about events and locations.

Return a json list of event descriptions as described above.
"""

#     If there are people or locations important to the paragraph, also include the described information for important events to them.    
#     "corresponding current locations" [list of modern day locations of the locations in the locations array]

    relev_events_list = get_llm_response(relev_events_prompt, as_json=True)

    return relev_events_list

def expand_compact_dict(combined_locs_data):
    individ_locs_dicts = []

    # first separate locations into individual entries
    for curDict in combined_locs_data:
        if not isinstance(curDict, str):
            # print(curDict)
            relev_imgs_list = curDict["relev_events_images"]
            locations_list = curDict["locations"] # ["corresponding current locations"]
            for i in range(len(locations_list)):
                nl_loc = locations_list[i]
                copiedDict = copy.deepcopy(curDict)
                # add individual location
                del copiedDict["locations"] # ["corresponding current locations"]
                copiedDict["location"] = nl_loc
                # add image from list of relev images based on index in locations list
                del copiedDict["relev_events_images"]
                img_idx = i % len(relev_imgs_list)
                copiedDict["relev_image"] = relev_imgs_list[img_idx]
                # x_y_loc = geocode(nl_loc, max_locations=1, out_fields="location")[0]['location']
                # copiedDict['x_loc'] = x_y_loc['x']
                # copiedDict['y_loc'] = x_y_loc['y']

                individ_locs_dicts.append(copiedDict)

    locations_list = [curDict["location"] for curDict in individ_locs_dicts]

    def sorted_batch_geocode(locations_list):
        batch_geocode_responses = batch_geocode(locations_list, out_fields='location')
        return sorted(batch_geocode_responses, key=lambda x: x['attributes']['ResultID'])

    # geocode in one request
    all_geocode_responses = sorted_batch_geocode(locations_list)

    # update x y 
    for i in range(len(individ_locs_dicts)):
        cur_dict = individ_locs_dicts[i]
        # get relevant geocoded location
        cur_geo = all_geocode_responses[i]
        cur_loc = cur_geo['location']
        # add this to current dict
        cur_dict['x'] = cur_loc['x']
        cur_dict['y'] = cur_loc['y']

        # with geocode info
        print(f'Geocoded Event: {cur_dict["tag line"]}, {cur_dict["location"]}->{cur_loc}')

    return individ_locs_dicts


def get_relev_img_urls(query):
    if SCRAPE_IMAGES:
        url = f"https://www.google.com/search?q={query}&tbm=isch"
        session = requests.Session()
        session.cookies.clear()
        response = requests.get(url=url)
        soup = BeautifulSoup(response.content, 'html.parser')

        images = soup.find_all('img')

        img_urls = []
        # filter for only valid links
        for img in images:
            # print(img)
            cur_src_url = img['src']
            if cur_src_url.startswith("https://"):
                img_urls.append(cur_src_url)

        # return top images
        return img_urls[:MAX_IMGS]
    else:
        return ["https://www.historyhit.com/app/uploads/2020/07/US-forces-battle-of-midway-1.jpg"]

def get_overall_info(query):
    paragraph_response = discuss_topic(query)
    related_events_list = get_related_events(paragraph_response)
    # add relev images for each event
    for event in related_events_list:
        event["relev_events_images"] = get_relev_img_urls(event["query"])

    print(related_events_list)
    # separate entries for each location
    individ_events_list = expand_compact_dict(related_events_list)

    # current relevant image
    relev_images = get_relev_img_urls(query)[:MAX_IMGS]

    return {
        "paragraph_response": paragraph_response,
        "query": query,
        "relev_images": relev_images,
        "relev_events_list": individ_events_list,
    }

@app.route('/test', methods=['POST'])
def testNothing():
    return jsonify({"message": "done"})

@app.route('/historyQuery', methods=['POST'])
def historyQuery():
    data = request.get_json()
    query_str = data['query']
    # check if I have the openAI api
    if USE_MOCK_DATA:
        time.sleep(1)
        fname = './example_responses/example_response1_abomb.json'

        if 'vietnam1' in query_str:
            fname = './demo_responses/vietnam_war1.json'
        elif 'vietnam2' in query_str or 'the vietnam war' in query_str:
            fname = './demo_responses/vietnam_war2.json'
        elif 'africa1' in query_str:
            fname = './demo_responses/africa_decolonization1.json'
        elif 'africa2' in query_str or 'Decolonization movements in Africa, Asia, and the Middle East' in query_str:
            fname = './demo_responses/africa_decolonization2.json'
        elif 'goat' in query_str or 'who is the GOAT of basketball?' in query_str:
            fname = './demo_responses/goat1.json'
        
        elif '1' in query_str:
            fname = './example_responses/example_response1_abomb.json'
        elif '2' in query_str:
            fname = './example_responses/example_response2_stock.json'
        elif '3' in query_str:
            fname = './example_responses/example_response3_chartist.json'

        with open(fname) as file:
            mock_data = json.load(file)
            return mock_data
    else:
        # new API call
        return get_overall_info(query_str)


if __name__ == '__main__':
    app.run(debug=True)
