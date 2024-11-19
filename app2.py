 import requests
from collections import defaultdict
import streamlit as st
import folium
from streamlit_folium import folium_static
import json
from fpdf import FPDF

# Define the Overpass API endpoint
overpass_url = "http://overpass-api.de/api/interpreter"

# Constants for the UI
PRIMARY_COLOR = "#164031"   # dark green
SECONDARY_COLOR = "#d99115" # golden yellow
ACCENT_COLOR = "#f16948"    # orange
BACKGROUND_COLOR = "#f0ecdf" # background color from the image
DEFAULT_VILLAGE = "Ossana"  # Default village for testing

# API configuration for AI analysis
API_URL = 'https://www.chatbase.co/api/v1/chat'
API_HEADERS = {
    'Authorization': 'Bearer d1a408c0-5e75-40ca-99e5-424e830d26ed',
    'Content-Type': 'application/json'
}
CHATBOT_ID = 'X5mqGdkfYYzpPO2R7Q5Jv'

# Villages list
villages = [
    "Ossana", "Vermiglio", "Sóller", "Port of Sóller", "Bileća",
    "Padna", "Šmarje", "Agatovo", "Alexandrovо", "Brestovo",
    "Gorsko Slivovo", "Kakrina", "Karpachevo", "Krushuna",
    "Kramolin", "Tepava", "Alavieska", "Kalajoki", "Nivala"
]

def get_amenities_by_village(village_name):
    """
    Fetches amenities around the given village name using Overpass API.
    """
    overpass_query = f"""
    [out:json];
    area["name"="{village_name}"]["boundary"="administrative"]->.searchArea;
    (
      node["amenity"](area.searchArea);
      way["amenity"](area.searchArea);
      relation["amenity"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    
    # Check if response is successful
    if response.status_code == 200:
        data = response.json()
    else:
        st.warning(f"API request failed with status code {response.status_code}")
        return None

    # Group amenities by type
    amenities = defaultdict(list)
    for element in data.get('elements', []):
        if 'tags' in element and 'amenity' in element['tags']:
            amenity_type = element['tags']['amenity']
            amenities[amenity_type].append(element)

    return amenities

def add_markers_to_map(m, amenities):
    """
    Adds markers to the map for given amenities.
    """
    for amenity_type, elements in amenities.items():
        for element in elements:
            if 'lat' in element and 'lon' in element:
                point_location = [element['lat'], element['lon']]
                tooltip = f"{amenity_type}: {element.get('tags', {}).get('name', 'N/A')}"
                folium.CircleMarker(
                    location=point_location,
                    radius=5,
                    popup=tooltip,
                    color=ACCENT_COLOR,
                    fill=True,
                    fill_color=ACCENT_COLOR
                ).add_to(m)

def generate_pdf(text, filename):
    """
    Generates a PDF from the provided text and saves it with the specified filename.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font("Arial", size=12)
    
    line_height = pdf.font_size * 2.5

    for line in text.split('\n'):
        words = line.split(' ')
        current_line = ""
        for word in words:
            if pdf.get_string_width(current_line + word) < (pdf.w - pdf.l_margin - pdf.r_margin):
                current_line += f"{word} "
            else:
                pdf.cell(0, line_height, txt=current_line.strip(), ln=1)
                current_line = f"{word} "
        pdf.cell(0, line_height, txt=current_line.strip(), ln=1)
    
    pdf.output(filename)
    return filename


def main():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {BACKGROUND_COLOR};
        }}
        .stButton>button {{
            background-color: {SECONDARY_COLOR};
            color: white;
        }}
        h1 {{
            color: {SECONDARY_COLOR};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.image("logo.png", width=200)

    st.markdown(
        f"<h1 style='color: {SECONDARY_COLOR};'>TA Analyzer</h1>",
        unsafe_allow_html=True
    )

    village_choice = st.selectbox("Choose a Test Area:", villages, index=villages.index(DEFAULT_VILLAGE))

    # Initialize session state for amenities and map
    if 'amenities' not in st.session_state:
        st.session_state.amenities = None
    if 'map' not in st.session_state:
        st.session_state.map = None

    # Button to show amenities
    if st.button('Show Amenities'):
        try:
            amenities = get_amenities_by_village(village_choice)
            if amenities and amenities.keys():
                st.session_state.amenities = amenities  # Store amenities in session state

                # Create a new map and replace the old one in session state
                first_amenity = next(iter(amenities.values()))[0]
                m = folium.Map(location=[first_amenity['lat'], first_amenity['lon']], zoom_start=14)
                add_markers_to_map(m, amenities)
                st.session_state.map = m  # Update session state with the new map
            else:
                st.warning(f"No amenities found for {village_choice}.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    # Display the map (only once, at the end of the section)
    if st.session_state.map:
        folium_static(st.session_state.map)

    st.subheader("AI Assistant")

    # Button for AI analysis
    if st.button('Analyze'):
        if st.session_state.amenities:
            try:
                # Preparing data for the AI analysis
                amenities = st.session_state.amenities
                amenities_summary = "\n".join([f"{amenity_type}: {len(elements)}" for amenity_type, elements in amenities.items()])
                message_content = f"What is the degree of digitalization, smartness, rural development, or similar in {village_choice} with these facilities:\n{amenities_summary}\nWhat can we do to improve it? Do you have any suggestions?"
                
                data = {
                    "messages": [
                        {"content": message_content, "role": "user"}
                    ],
                    "chatbotId": CHATBOT_ID,
                    "stream": False,
                    "temperature": 0
                }
                
                response = requests.post(API_URL, headers=API_HEADERS, data=json.dumps(data))
                
                if response.status_code == 200:
                    json_data = response.json()
                    response_text = json_data.get('text', 'No text in response')
                    st.write("Response:", response_text)
                    
                    pdf_filename = f"AI_Analysis_{village_choice}.pdf"
                    generate_pdf(response_text, pdf_filename)
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button("Download Analysis as PDF", pdf_file, file_name=pdf_filename)
                else:
                    error_message = response.json().get('message', 'Unknown error')
                    st.error(f'Error: {error_message}')
            
            except Exception as e:
                st.error(f"An error occurred during AI analysis: {str(e)}")
        else:
            st.warning("Please show the amenities first by clicking 'Show Amenities'.")

if __name__ == "__main__":
    main()


