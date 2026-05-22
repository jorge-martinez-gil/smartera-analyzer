import io
import json
from typing import Any

import folium
import osmnx as ox
import pandas as pd
import requests
import streamlit as st
from fpdf import FPDF
from streamlit_folium import folium_static

# Extracted color palette from the logo.png
PRIMARY_COLOR = "#164031"   # dark green
SECONDARY_COLOR = "#d99115" # golden yellow
ACCENT_COLOR = "#f16948"    # orange
BACKGROUND_COLOR = "#f0ecdf" # background color from the image

# Constants
RADIUS = 1000
DEFAULT_COORDINATES = (48.36964, 14.5128)
API_URL = "https://www.chatbase.co/api/v1/chat"

DIMENSION_COLORS = {
    "Default": ACCENT_COLOR,
    "SmartEconomy": "#2ca02c",      # green
    "SmartGovernance": "#1f77b4",   # blue
    "SmartMobility": "#6f42c1",     # purple
    "SmartEnvironment": "#20b2aa",  # teal
    "SmartPeople": "#ff9800",       # orange
    "SmartLiving": "#d62728",       # red
}

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
    "P6 - Devetaki Plateau - Tepava": (43.2106, 25.0286),
}


def get_amenities(latitude: float, longitude: float, amenity_type: str = "all", radius: int = RADIUS) -> pd.DataFrame:
    """Fetch amenities around the given latitude and longitude."""
    tags = {"amenity": True} if amenity_type == "all" else {"amenity": amenity_type}
    with st.spinner("Fetching data…"):
        amenities = ox.features_from_point((latitude, longitude), tags=tags, dist=radius)
    return amenities


def count_entities(entities: pd.DataFrame) -> dict[str, int]:
    """Count entities in a robust way even when expected columns are missing."""
    if entities.empty:
        return {}

    if "entity_type" in entities.columns:
        values = entities["entity_type"].dropna().astype(str)
        if not values.empty:
            return values.value_counts().to_dict()

    if "amenity" in entities.columns:
        values = entities["amenity"].dropna().astype(str)
        if not values.empty:
            return values.value_counts().to_dict()

    if isinstance(entities.index, pd.MultiIndex) and "element_type" in entities.index.names:
        idx = entities.index.get_level_values("element_type").astype(str)
        if len(idx) > 0:
            return pd.Series(idx).value_counts().to_dict()

    if len(entities.index) > 0:
        return {"unknown": int(len(entities.index))}

    return {}


def count_amenities(latitude: float, longitude: float, radius: int = RADIUS) -> dict[str, int]:
    """Count amenities around the given latitude and longitude."""
    amenities = get_amenities(latitude, longitude, radius=radius)
    if "amenity" not in amenities.columns:
        return {}
    amenity_counts = amenities["amenity"].dropna().astype(str).value_counts()
    return amenity_counts.to_dict()


def get_smart_entities(latitude: float, longitude: float, ent: str, radius: int = RADIUS) -> pd.DataFrame:
    """Fetch entities of a specific type around the given latitude and longitude."""
    if "=" in ent:
        key, value = ent.split("=", maxsplit=1)
    else:
        key, value = "name", ent
    tags = {key: True} if value == "all" else {key: value}
    with st.spinner("Fetching data…"):
        entities = ox.features_from_point((latitude, longitude), tags=tags, dist=radius)
    entities["entity_type"] = ent
    return entities


def add_markers_to_map(
    m: folium.Map,
    entities: pd.DataFrame,
    entity_type: str,
    color: str,
    layer_name: str,
) -> None:
    """Add markers to the map for entities using the provided color and layer."""
    feature_group = folium.FeatureGroup(name=layer_name, show=True)

    for _, row in entities.iterrows():
        geometry = row.get("geometry")
        if geometry is None:
            continue

        if geometry.geom_type == "Point":
            point_location = [geometry.y, geometry.x]
        elif geometry.geom_type in {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}:
            centroid = geometry.centroid
            point_location = [centroid.y, centroid.x]
        else:
            continue

        tooltip = f"{entity_type}: {row.get('name', 'N/A')}"
        folium.CircleMarker(
            location=point_location,
            radius=8,
            popup=tooltip,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
        ).add_to(feature_group)

    feature_group.add_to(m)


def generate_pdf(text: str) -> io.BytesIO:
    """Generate an in-memory PDF from the provided text."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font("Arial", size=12)

    line_height = pdf.font_size * 2.5

    for line in text.split("\n"):
        words = line.split(" ")
        current_line = ""
        for word in words:
            if pdf.get_string_width(current_line + word) < (pdf.w - pdf.l_margin - pdf.r_margin):
                current_line += f"{word} "
            else:
                pdf.cell(0, line_height, txt=current_line.strip(), new_x="LMARGIN", new_y="NEXT")
                current_line = f"{word} "
        pdf.cell(0, line_height, txt=current_line.strip(), new_x="LMARGIN", new_y="NEXT")

    raw_output: Any = pdf.output(dest="S")
    if isinstance(raw_output, str):
        raw_output = raw_output.encode("latin-1")

    buffer = io.BytesIO(bytes(raw_output))
    buffer.seek(0)
    return buffer


def update_message_content(lat: float, lon: float) -> None:
    """Update AI prompt content in session state based on selected entities."""
    if st.session_state.selected_entities:
        combined_entities = pd.concat(st.session_state.selected_entities, ignore_index=False)
        entity_counts = count_entities(combined_entities)

        if "all" in entity_counts:
            amenities_count = count_amenities(lat, lon, RADIUS)
            update_message_content2(str(amenities_count))
            return

        entity_counts_filtered = {k: v for k, v in entity_counts.items() if k != "all"}
        detailed_info = "\n".join([f"{etype}: {count}" for etype, count in entity_counts_filtered.items()])

        st.session_state.message_content = (
            "What is the degree of digitalization, smartness, rural development or similar "
            "of a village located in a rural territory with these facilities:\n"
            f"{detailed_info}\n"
            "What can we do to improve it? Do you have any suggestion?"
        )


def update_message_content2(info: str) -> None:
    """Update AI prompt content with provided entity information."""
    if st.session_state.selected_entities:
        st.session_state.message_content = (
            "What is the degree of digitalization, smartness, rural development or similar "
            "of a village located in a rural territory with these facilities:\n"
            f"{info}\n"
            "What can we do to improve it? Do you have any suggestion?"
        )


def initialize_session_state() -> None:
    """Initialize the session state values used by the app."""
    if "selected_entities" not in st.session_state:
        st.session_state.selected_entities = []
    if "message_content" not in st.session_state:
        st.session_state.message_content = ""


def get_api_config() -> tuple[dict[str, str] | None, str | None]:
    """Get API credentials from Streamlit secrets with graceful fallback."""
    try:
        headers = {
            "Authorization": st.secrets["AUTH"],
            "Content-Type": "application/json",
        }
        chatbot_id = st.secrets["ID"]
        return headers, chatbot_id
    except Exception:
        st.info("AI credentials are not configured. Add AUTH and ID in Streamlit secrets to enable analysis.")
        return None, None


def render_entity_chart(entity_counts: dict[str, int]) -> None:
    """Render a bar chart for entity counts using existing color palette constants."""
    if not entity_counts:
        return

    chart_df = pd.DataFrame(
        {"Entity Type": list(entity_counts.keys()), "Count": list(entity_counts.values())}
    )

    try:
        import plotly.graph_objects as go

        colors = [SECONDARY_COLOR if i % 2 == 0 else ACCENT_COLOR for i in range(len(chart_df))]
        fig = go.Figure(
            data=[
                go.Bar(
                    x=chart_df["Entity Type"],
                    y=chart_df["Count"],
                    marker_color=colors,
                )
            ]
        )
        fig.update_layout(
            title="Entity Counts by Type",
            xaxis_title="Entity Type",
            yaxis_title="Count",
            plot_bgcolor=BACKGROUND_COLOR,
            paper_bgcolor=BACKGROUND_COLOR,
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.bar_chart(chart_df.set_index("Entity Type"), color=SECONDARY_COLOR)


def build_map(lat: float, lon: float) -> folium.Map:
    """Create map and redraw all selected entity layers from session state."""
    m = folium.Map(location=[lat, lon], zoom_start=14)

    for entities in st.session_state.selected_entities:
        if entities.empty:
            continue
        entity_type = str(entities.get("entity_type", pd.Series(["unknown"])).iloc[0])
        layer_name = str(entities.get("layer_name", pd.Series(["Default"])).iloc[0])
        marker_color = str(entities.get("marker_color", pd.Series([ACCENT_COLOR])).iloc[0])
        add_markers_to_map(m, entities, entity_type, marker_color, layer_name)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def main() -> None:
    """Run the TA Analyzer Streamlit app."""
    initialize_session_state()

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
        unsafe_allow_html=True,
    )

    st.image("logo.png", width=200)
    st.markdown(f"<h1 style='color: {SECONDARY_COLOR};'>TA Analyzer</h1>", unsafe_allow_html=True)

    smart_entities_options = {
        "SmartEconomy": [
            "POI", "amenity=marketplace", "amenity=vending_machine", "building=commercial",
            "man_made=offshore_platform", "man_made=petroleum_well", "man_made=pipeline", "man_made=works", "office=company",
            "office=coworking", "shop=all", "tourism=alpine_hut", "tourism=attraction", "tourism=camp_pitch", "tourism=camp_site",
            "tourism=caravan_site", "building=chalet", "building=guest_house", "building=hostel", "building=hotel", "tourism=information",
            "tourism=motel", "building=museum", "tourism=wilderness_hut",
        ],
        "SmartGovernance": ["amenity=townhall", "amenity=courthouse", "amenity=police", "amenity=fire_station", "building=government"],
        "SmartMobility": [
            "barrier=bump_gate", "barrier=bus_trap", "barrier=cycle_barrier", "barrier=motorcycle_barrier",
            "barrier=sump_buster", "building=train_station", "building=transportation", "building=parking",
            "highway=motorway", "public_transport=all", "railway=all", "route=all",
        ],
        "SmartEnvironment": [
            "amenity=recycling", "boundary=forest", "boundary=forest_compartment", "boundary=hazard",
            "boundary=national_park", "boundary=protected_area", "leisure=garden", "leisure=nature_reserve",
            "leisure=park", "man_made=gasometer", "man_made=mineshaft", "man_made=wastewater_plant",
            "man_made=water_works", "natural=grass", "water=river",
        ],
        "SmartPeople": [
            "amenity=college", "amenity=kindergarten", "amenity=school", "amenity=university",
            "office=educational_institution", "office=employment_agency", "amenity=refugee_site",
        ],
        "SmartLiving": [
            "amenity=internet_cafe", "amenity=public_bath", "amenity=vending_machine",
            "amenity=water_point", "amenity=hospital", "amenity=museum",
            "amenity=place_of_worship", "amenity=fire_station", "amenity=toilets",
        ],
    }

    with st.sidebar:
        st.header("Controls")
        example_choice = st.selectbox("Choose a Test Area:", list(villages_coordinates.keys()), key="example_choice")
        selected_coordinate = villages_coordinates[example_choice]
        lat = st.number_input("Enter the latitude of the area:", value=selected_coordinate[0])
        lon = st.number_input("Enter the longitude of the area:", value=selected_coordinate[1])

        if st.button("🗑 Clear All Layers", key="clear_layers"):
            st.session_state.selected_entities = []
            st.session_state.message_content = ""
            st.rerun()

        tab_names = ["Default", "SmartEconomy", "SmartGovernance", "SmartMobility", "SmartEnvironment", "SmartPeople", "SmartLiving"]
        tabs = st.tabs(tab_names)

        with tabs[0]:
            amenity_options = ["all", "restaurant", "hospital", "school", "bank", "cafe", "pharmacy", "cinema", "parking", "fuel"]
            amenity_type = st.selectbox("Select Amenity Type:", amenity_options, key="amenity_type")

            if st.button("Show Amenities", key="amenity"):
                try:
                    amenities = get_amenities(lat, lon, amenity_type, RADIUS)
                    amenities["entity_type"] = amenity_type
                    amenities["layer_name"] = "Default"
                    amenities["marker_color"] = DIMENSION_COLORS["Default"]
                    st.session_state.selected_entities.append(amenities)
                    update_message_content(lat, lon)
                except Exception as e:
                    if "EmptyOverpassResponse" in str(e):
                        st.warning(f"No {amenity_type} amenities found within the specified distance.")
                    else:
                        st.error(f"An error occurred: {str(e)}")

        for i, tab_name in enumerate(tab_names[1:], start=1):
            with tabs[i]:
                selected_entity = st.selectbox(
                    f"Select Entity Type for {tab_name}:",
                    smart_entities_options[tab_name],
                    key=f"{tab_name}_entity",
                )
                if st.button(f"Show Selected Entities for {tab_name}", key=f"tab{i}"):
                    try:
                        entities = get_smart_entities(lat, lon, selected_entity, RADIUS)
                        entities["layer_name"] = tab_name
                        entities["marker_color"] = DIMENSION_COLORS[tab_name]
                        st.session_state.selected_entities.append(entities)
                        update_message_content(lat, lon)
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

    combined_entities = (
        pd.concat(st.session_state.selected_entities, ignore_index=False)
        if st.session_state.selected_entities
        else pd.DataFrame()
    )
    entity_counts = count_entities(combined_entities)

    if entity_counts:
        total_count = int(sum(entity_counts.values()))
        distinct_types = int(len(entity_counts))
        radius_km = RADIUS / 1000
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Entities", total_count)
        col2.metric("Distinct Types", distinct_types)
        col3.metric("Radius (km)", f"{radius_km:.1f}")

        st.subheader("Entity Distribution")
        render_entity_chart(entity_counts)

    m = build_map(lat, lon)
    folium_static(m)

    st.subheader("AI Assistant")
    api_headers, chatbot_id = get_api_config()

    if st.button("Analysis", key="ai_analysis"):
        if not st.session_state.message_content:
            st.warning("Load at least one layer before requesting analysis.")
        elif not api_headers or not chatbot_id:
            st.info("AI analysis is unavailable until AUTH and ID are configured in Streamlit secrets.")
        else:
            data = {
                "messages": [{"content": st.session_state.message_content, "role": "user"}],
                "chatbotId": chatbot_id,
                "stream": False,
                "temperature": 0,
            }

            with st.expander("View prompt"):
                st.code(st.session_state.message_content)

            with st.spinner("Analyzing…"):
                response = requests.post(API_URL, headers=api_headers, data=json.dumps(data), timeout=60)

            if response.status_code == 200:
                json_data = response.json()
                response_text = json_data.get("text", "No text in response")
                st.success(response_text)

                pdf_buffer = generate_pdf(response_text)
                st.download_button(
                    "Download Analysis as PDF",
                    data=pdf_buffer,
                    file_name=f"AI_Analysis_{lat}_{lon}.pdf",
                    mime="application/pdf",
                )
            else:
                try:
                    error_message = response.json().get("message", "Unknown error")
                except Exception:
                    error_message = "Unknown error"
                st.error(f"Error: {error_message}")


if __name__ == "__main__":
    main()
