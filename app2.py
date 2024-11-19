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

