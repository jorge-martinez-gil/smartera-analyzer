import streamlit as st
import osmnx as ox
import folium
import requests
import json
import pandas as pd
from streamlit_folium import st_folium
from fpdf import FPDF

# Extracted color palette from the logo.png
PRIMARY_COLOR = "#164031"   # dark green
SECONDARY_COLOR = "#d99115" # golden yellow
ACCENT_COLOR = "#f16948"    # orange
BACKGROUND_COLOR = "#f0ecdf" # background color from the image

# Constants
RADIUS = 1000
DEFAULT_COORDINATES = (48.36964, 14.5128)
API_URL = 'https://www.chatbase.co/api/v1/chat'
API_HEADERS = {
    'Authorization': st.secrets["AUTH"],
    'Content-Type': 'application/json'
}
CHATBOT_ID = st.secrets["ID"]

# Villages and their coordinates
villages_coordinates = {
    "P1 - Valle di Sole - Caldes": (46.3732, 10.9279),
    "P1 - Valle di Sole - Cavizzana": (46.3555, 10.9396),
    "P1 - Valle di Sole - Terzolas": (46.3489, 10.9353),
    "P1 - Valle di Sole - Male": (46.3546, 10.9055),
    "P1 - Valle di Sole - Croviana": (46.3503, 10.9108),
    "P1 - Valle di Sole - Dimaro Folgarida": (46.3293, 10.8813),
    "P1 - Valle di Sole - Commezzadura": (46.3215, 10.8584),
    "P1 - Valle di Sole - Mezzana": (46.3136, 10.8483),
    "P1 - Valle di Sole - Pellizzano": (46.3098, 10.8155),
    "P1 - Valle di Sole - Rabbi": (46.3805, 10.8692),
    "P1 - Valle di Sole - Peio": (46.3628, 10.6792),
    "P1 - Valle di Sole - Ossana": (46.3087, 10.7488),
    "P1 - Valle di Sole - Vermiglio": (46.2979, 10.6833),
    "P2 - Sóller / Tramuntana - Sóller": (39.7696, 2.7140),
    "P2 - Sóller / Tramuntana - Port of Sóller": (39.7960, 2.6972),
    "P2 - Sóller / Tramuntana - Fornalutx/Biniaraix": (39.7821, 2.7405),
    "P3 - Northern Ostrobothnia - Alavieska": (64.1653, 24.3069),
    "P3 - Northern Ostrobothnia - Kalajoki": (64.2597, 23.9486),
    "P3 - Northern Ostrobothnia - Nivala": (63.9292, 24.9778),
    "P4 - East Herzegovina - Nevesinje": (43.2581, 18.1136),
    "P4 - East Herzegovina - Gacko": (43.1670, 18.5350),
    "P4 - East Herzegovina - Bileća": (42.8759, 18.4286),
    "P5 - Smarje-Padna - Padna": (45.4915, 13.6842),
    "P5 - Smarje-Padna - Šmarje": (45.5005, 13.7171),
    "P6 - Devetaki Plateau - Agatovo": (43.1667, 25.0167),
    "P6 - Devetaki Plateau - Alexandrovо": (43.2290, 25.0540),
    "P6 - Devetaki Plateau - Brestovo": (43.1792, 24.9472),
    "P6 - Devetaki Plateau - Gorsko Slivovo": (43.2447, 25.1017),
    "P6 - Devetaki Plateau - Kakrina": (43.1644, 24.9897),
    "P6 - Devetaki Plateau - Karpachevo": (43.2642, 25.0806),
    "P6 - Devetaki Plateau - Krushuna": (43.2461, 25.0397),
    "P6 - Devetaki Plateau - Kramolin": (43.1336, 25.1472),
    "P6 - Devetaki Plateau - Tepava": (43.2106, 25.0286)
}

def get_amenities(latitude, longitude, amenity_type='all', radius=RADIUS):
    """
    Fetches amenities around the given latitude and longitude.
    """
    tags = {'amenity': True} if amenity_type == 'all' else {'amenity': amenity_type}
    amenities = ox.geometries_from_point((latitude, longitude), tags=tags, dist=radius)
    return amenities

def count_entities(entities):
    """
    Counts different types of entities.
    """
    if 'entity_type' in entities.columns:
        entity_counts = entities['entity_type'].value_counts()
    else:
        entity_counts = entities.index.value_counts()
    return entity_counts.to_dict()

def count_amenities(latitude, longitude, radius=RADIUS):
    """
    Counts amenities around the given latitude and longitude.
    """
    amenities = get_amenities(latitude, longitude, radius=radius)
    amenity_counts = amenities['amenity'].value_counts()
    return amenity_counts.to_dict()

def get_smart_entities(latitude, longitude, ent, radius=RADIUS):
    """
    Fetches entities of a specific type around the given latitude and longitude.
    """
    key, value = ent.split('=')
    tags = {key: value}
    entities = ox.geometries_from_point((latitude, longitude), tags=tags, dist=radius)
    entities['entity_type'] = ent
    return entities

def add_markers_to_map(m, entities, entity_type):
    """
    Adds markers to the map for given entities.
    """
    for _, row in entities.iterrows():
        if row.geometry:
            if row.geometry.geom_type == 'Point':
                point_location = [row.geometry.y, row.geometry.x]
            elif row.geometry.geom_type == 'Polygon':
                point_location = [row.geometry.centroid.y, row.geometry.centroid.x]
            else:
                continue

            tooltip = f"{entity_type}: {row.get('name', 'N/A')}"
            folium.CircleMarker(
                location=point_location,
                radius=10,
                popup=tooltip,
                color=ACCENT_COLOR,
                fill=True,
                fill_color=ACCENT_COLOR
            ).add_to(m)

def generate_pdf(text):
    """
    Generates a PDF from the provided text with proper word wrapping.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font("Arial", size=12)
    
    line_height = pdf.font_size * 2.5

    for line in text.split('\n'):
        # Break lines that are too long
        words = line.split(' ')
        current_line = ""
        for word in words:
            if pdf.get_string_width(current_line + word) < (pdf.w - pdf.l_margin - pdf.r_margin):
                current_line += f"{word} "
            else:
                pdf.cell(0, line_height, txt=current_line.strip(), ln=1)
                current_line = f"{word} "
        pdf.cell(0, line_height, txt=current_line.strip(), ln=1)
    
    return pdf


def update_message_content(lat, lon):
    """
    Updates the message content in the session state.
    """
    if st.session_state.selected_entities:
        combined_entities = pd.concat(st.session_state.selected_entities)
        entity_counts = count_entities(combined_entities)
        
        if 'all' in entity_counts:
            amenities_count = count_amenities(lat, lon, 1000)
            update_message_content2(str(amenities_count))
            return
        
        entity_counts_filtered = {k: v for k, v in entity_counts.items() if k != 'all'}
        detailed_info = "\n".join([f"{etype}: {count}" for etype, count in entity_counts_filtered.items()])
        
        st.session_state.message_content = f"What is the degree of digitalization, smartness, rural development or similar of a village located in a rural territory with these facilities:\n{detailed_info}\nWhat can we do to improve it? Do you have any suggestion?"

def update_message_content2(info):
    """
    Updates the message content with provided information.
    """
    if st.session_state.selected_entities:
        st.session_state.message_content = f"What is the degree of digitalization, smartness, rural development or similar of a village located in a rural territory with these facilities:\n{info}\nWhat can we do to improve it? Do you have any suggestion?"

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
        .stSelectbox, .stNumberInput {{
            color: {SECONDARY_COLOR};
        }}
        .stTabs {{
            border-color: {ACCENT_COLOR};
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
    
    example_choice = st.selectbox("Choose a Test Area:", list(villages_coordinates.keys()), key='example_choice')
    selected_coordinate = villages_coordinates[example_choice]
    lat = st.number_input("Enter the latitude of the area:", value=selected_coordinate[0])
    lon = st.number_input("Enter the longitude of the area:", value=selected_coordinate[1])
    
    m = folium.Map(location=[lat, lon], zoom_start=14)

    tab_names = ["Default", "SmartEconomy", "SmartGovernance", "SmartMobility", "SmartEnvironment", "SmartPeople", "SmartLiving"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        amenity_options = ['all', 'restaurant', 'hospital', 'school', 'bank', 'cafe', 'pharmacy', 'cinema', 'parking', 'fuel']
        amenity_type = st.selectbox("Select Amenity Type:", amenity_options, key='amenity_type')
        
        if st.button('Show Amenities', key='amenity'):
            try:
                amenities = get_amenities(lat, lon, amenity_type, RADIUS)
                amenities['entity_type'] = amenity_type
                add_markers_to_map(m, amenities, amenity_type)
                st.session_state.selected_entities.append(amenities)
                update_message_content(lat, lon)
            except Exception as e:
                if "EmptyOverpassResponse" in str(e):
                    st.warning(f"No {amenity_type} amenities found within the specified distance.")
                else:
                    st.error(f"An error occurred: {str(e)}")

    smart_entities_options = {
        "SmartEconomy": [
            'POI', 'amenity=marketplace', 'amenity=vending_machine', 'building=commercial', 
            'man_made=offshore_platform', 'man_made=petroleum_well', 'man_made=pipeline', 'man_made=works', 'office=company',
            'office=coworking', 'shop=all', 'tourism=alpine_hut', 'tourism=attraction', 'tourism=camp_pitch', 'tourism=camp_site',
            'tourism=caravan_site', 'building=chalet', 'building=guest_house', 'building=hostel', 'building=hotel', 'tourism=information',
            'tourism=motel', 'building=museum', 'tourism=wilderness_hut'
        ],
        "SmartGovernance": ['amenity=townhall', 'amenity=courthouse', 'amenity=police', 'amenity=fire_station', 'building=government'],
        "SmartMobility": [
            'barrier=bump_gate', 'barrier=bus_trap', 'barrier=cycle_barrier', 'barrier=motorcycle_barrier',
            'barrier=sump_buster', 'building=train_station', 'building=transportation', 'building=parking',
            'highway=motorway', 'public_transport=all', 'railway=all', 'route=all'
        ],
        "SmartEnvironment": [
            "amenity=recycling", "boundary=forest", "boundary=forest_compartment", "boundary=hazard",
            "boundary=national_park", "boundary=protected_area", "leisure=garden", "leisure=nature_reserve",
            "leisure=park", "man_made=gasometer", "man_made=mineshaft", "man_made=wastewater_plant",
            "man_made=water_works", "natural=grass", "water=river"
        ],
        "SmartPeople": [
            "amenity=college", "amenity=kindergarten", "amenity=school", "amenity=university",
            "office=educational_institution", "office=employment_agency", "amenity=refugee_site"
        ],
        "SmartLiving": [
            "amenity=internet_cafe", "amenity=public_bath", "amenity=vending_machine",
            "amenity=water_point", "amenity=hospital", "amenity=museum",
            "amenity=place_of_worship", "amenity=fire_station", "amenity=toilets",
        ]
    }

    for i, tab_name in enumerate(tab_names[1:], start=1):
        with tabs[i]:
            selected_entity = st.selectbox(f"Select Entity Type for {tab_name}:", smart_entities_options[tab_name], key=f'{tab_name}_entity')
            if st.button(f'Show Selected Entities for {tab_name}', key=f'tab{i}'):
                try:
                    entities = get_smart_entities(lat, lon, selected_entity, RADIUS)
                    add_markers_to_map(m, entities, selected_entity)
                    st.session_state.selected_entities.append(entities)
                    update_message_content(lat, lon)
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    st_folium(m)

    st.subheader("AI Assistant")
    
    if st.button('Analysis', key='ai_analysis'):
        data = {
            "messages": [
                {"content": st.session_state.message_content, "role": "user"}
            ],
            "chatbotId": CHATBOT_ID,
            "stream": False,
            "temperature": 0
        }
        
        response = requests.post(API_URL, headers=API_HEADERS, data=json.dumps(data))
        st.write (st.session_state.message_content)
        
        if response.status_code == 200:
            json_data = response.json()
            response_text = json_data.get('text', 'No text in response')
            st.write("Response:", response_text)
            
            pdf = generate_pdf(response_text)
            pdf_output = f"AI_Analysis_{lat}_{lon}.pdf"
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as pdf_file:
                st.download_button("Download Analysis as PDF", pdf_file, file_name=f"AI_Analysis_{lat}_{lon}.pdf")
        else:
            error_message = response.json().get('message', 'Unknown error')
            st.write('Error:', error_message)

if __name__ == "__main__":
    # Initialize session state
    if 'selected_entities' not in st.session_state:
        st.session_state.selected_entities = []

    if 'message_content' not in st.session_state:
        st.session_state.message_content = ""

    main()
