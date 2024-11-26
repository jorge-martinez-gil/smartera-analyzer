import streamlit as st
import osmnx as ox
import folium
import requests
import json
import pandas as pd
from streamlit_folium import st_folium
from fpdf import FPDF

# Constants and Styling
RADIUS = 1000
DEFAULT_COORDINATES = (48.36964, 14.5128)
PRIMARY_COLOR = "#164031"
SECONDARY_COLOR = "#d99115"
ACCENT_COLOR = "#f16948"
BACKGROUND_COLOR = "#f0ecdf"

API_URL = 'https://www.chatbase.co/api/v1/chat'
API_HEADERS = {
    'Authorization': st.secrets["AUTH"],
    'Content-Type': 'application/json'
}
CHATBOT_ID = st.secrets["ID"]

villages_coordinates = {
    "P1 - Valle di Sole - Caldes": (46.3732, 10.9279),
    "P1 - Valle di Sole - Cavizzana": (46.3555, 10.9396),
    "P1 - Valle di Sole - Terzolas": (46.3489, 10.9353),
    "P1 - Valle di Sole - Male": (46.3546, 10.9055),
    # Add other villages here...
}

# Helper Functions
def get_amenities(lat, lon, amenity_type='all', radius=RADIUS):
    """
    Fetch amenities using OSMnx within a radius of the given point.
    """
    try:
        tags = {'amenity': amenity_type} if amenity_type != 'all' else {'amenity': True}
        amenities = ox.geometries.geometries_from_point((lat, lon), tags=tags, dist=radius)
        return amenities
    except Exception as e:
        st.error(f"Error fetching amenities: {e}")
        return pd.DataFrame()

def add_markers_to_map(map_obj, entities, entity_type):
    """
    Add markers for amenities/entities to the map.
    """
    for _, row in entities.iterrows():
        if row.geometry.is_empty:
            continue
        point = row.geometry.centroid if row.geometry.geom_type == 'Polygon' else row.geometry
        folium.CircleMarker(
            location=[point.y, point.x],
            radius=10,
            popup=f"{entity_type}: {row.get('name', 'N/A')}",
            color=ACCENT_COLOR,
            fill=True,
            fill_color=ACCENT_COLOR
        ).add_to(map_obj)

def generate_pdf(text):
    """
    Generate a PDF from the provided text.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    return pdf

def main():
    # Styling
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {BACKGROUND_COLOR}; }}
        .stButton>button {{ background-color: {SECONDARY_COLOR}; color: white; }}
        .stSelectbox, .stNumberInput {{ color: {SECONDARY_COLOR}; }}
        h1 {{ color: {SECONDARY_COLOR}; }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.image("logo.png", width=200)
    st.title("TA Analyzer")
    
    # User Inputs
    village = st.selectbox("Choose a Test Area:", list(villages_coordinates.keys()))
    lat, lon = villages_coordinates[village]
    lat = st.number_input("Latitude:", value=lat)
    lon = st.number_input("Longitude:", value=lon)

    # Map Initialization
    map_obj = folium.Map(location=[lat, lon], zoom_start=14)

    # Amenity Selection and Display
    amenity_type = st.selectbox("Select Amenity Type:", ['all', 'restaurant', 'hospital', 'school', 'cafe', 'bank'])
    if st.button("Show Amenities"):
        amenities = get_amenities(lat, lon, amenity_type)
        if not amenities.empty:
            add_markers_to_map(map_obj, amenities, amenity_type)
        else:
            st.warning("No amenities found.")
    
    st_folium(map_obj)

    # AI Analysis
    if st.button("Analyze Area"):
        st.session_state.message_content = (
            f"Analyze the digitalization and smartness of the village with these facilities: {amenity_type}."
        )
        response = requests.post(
            API_URL, 
            headers=API_HEADERS, 
            data=json.dumps({
                "messages": [{"role": "user", "content": st.session_state.message_content}],
                "chatbotId": CHATBOT_ID
            })
        )
        if response.status_code == 200:
            analysis_text = response.json().get('text', "No response.")
            st.text_area("AI Analysis Response:", analysis_text)
            
            pdf = generate_pdf(analysis_text)
            pdf_file = f"AI_Analysis_{lat}_{lon}.pdf"
            pdf.output(pdf_file)
            with open(pdf_file, "rb") as f:
                st.download_button("Download Analysis as PDF", f, file_name=pdf_file)
        else:
            st.error(f"Error: {response.json().get('message', 'Unknown error')}")

if __name__ == "__main__":
    if "message_content" not in st.session_state:
        st.session_state.message_content = ""
    main()




