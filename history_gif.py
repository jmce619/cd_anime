# streamlit_app.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import openai
import time
from shapely.geometry import Polygon, MultiPolygon

def set_custom_style():
    """
    Apply custom CSS styles for a minimalist design.
    """
    st.markdown(
        """
        <style>

        /* Set app background color to white */
        .stApp {
            background-color: #FFFFFF;
        }

        

        </style>
        """,
        unsafe_allow_html=True
    )
# Set the page configuration
st.set_page_config(page_title="Districts Slideshow", layout="wide")
# Title of the app

# Initialize OpenAI client
openai.api_key = st.secrets.openai.api_key

def load_and_combine_shapefiles(parent_dir='./'):
    combined_gdf = gpd.read_file("./unioned_districts.shp")
    return combined_gdf


@st.cache_data
def create_mapping_dataframe():
    district_dates = pd.DataFrame({
        'district_n': [f"{i:03}" for i in range(1, 26)],
        'order': [
            '1st', '2nd', '3rd', '4th', '5th',
            '6th', '7th', '8th', '9th', '10th',
            '11th', '12th', '13th', '14th', '15th',
            '16th', '17th', '18th', '19th', '20th',
            '21st', '22nd', '23rd', '24th', '25th'
        ],
        'date_range': [
            'March 4, 1789 to March 3, 1791',
            'March 4, 1791 to March 2, 1793',
            'March 4, 1793 to March 3, 1795',
            'June 8, 1795 to March 3, 1797',
            'March 4, 1797 to March 3, 1799',
            'December 2, 1799 to March 3, 1801',
            'March 4, 1801 to March 3, 1803',
            'October 17, 1803 to March 3, 1805',
            'December 2, 1805 to March 3, 1807',
            'October 26, 1807 to March 3, 1809',
            'March 4, 1809 to March 3, 1811',
            'November 4, 1811 to March 3, 1813',
            'May 24, 1813 to March 3, 1815',
            'December 4, 1815 to March 3, 1817',
            'March 4, 1817 to March 3, 1819',
            'December 6, 1819 to March 3, 1821',
            'December 3, 1821 to March 3, 1823',
            'December 1, 1823 to March 3, 1825',
            'March 4, 1825 to March 3, 1827',
            'December 3, 1827 to March 3, 1829',
            'March 4, 1829 to March 3, 1831',
            'December 5, 1831 to March 2, 1833',
            'December 2, 1833 to March 3, 1835',
            'December 7, 1835 to March 3, 1837',
            'March 4, 1837 to March 3, 1839'
        ]
    })
    return district_dates

@st.cache_data
def merge_data(_combined_gdf, district_dates):
    merged_gdf = _combined_gdf.merge(district_dates, on='district_n', how='left')
  
    # Split the 'date_range' into 'start_date' and 'end_date'
    merged_gdf[['start_date', 'end_date']] = merged_gdf['date_range'].str.split(' to ', expand=True)
    
    # Converthe date strings to datetime objects

    return merged_gdf

# -------------- Historical Facts Caching Function --------------

@st.cache_data
def get_historical_fact(district_n, start_date, end_date, refresh_count):
    """
    Fetches an interesting historical fact for the given district's date range.
    Caches the result to minimize API calls unless a refresh is triggered.
    """
    date_str = f"{start_date} to {end_date}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Provide an interesting historical fact about the United States that happened between {date_str}."}
            ],
            temperature=0.7,
            max_tokens=75
        )
        fact = response.choices[0].message.content.strip()
    except Exception as e:
        fact = "Historical fact not available."
        st.error(f"Error fetching data from OpenAI for District {district_n}: {e}")
    
    return fact

# -------------- Plotting Function --------------

def plot_district(order, geometries, fact):
    """
    Generates a Matplotlib figure for the given congressional session with all its geometries.
    
    Parameters:
    - order (str): The order of the congressional session (e.g., "1st").
    - geometries (GeoSeries or list): The geometries of the session.
    - fact (str): The historical fact to display.
    
    Returns:
    - fig: The Matplotlib figure object.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Ensure geometries are in a GeoSeries for plotting
    if isinstance(geometries, list):
        geometries = gpd.GeoSeries(geometries)
    elif isinstance(geometries, (Polygon, MultiPolygon)):
        geometries = gpd.GeoSeries([geometries])
    elif isinstance(geometries, gpd.GeoSeries):
        pass  # Already a GeoSeries
    else:
        return fig  # Return empty figure
    
    # Plot all geometries for the congressional session
    geometries.plot(ax=ax, color='skyblue', edgecolor='black')
    
    # Set the title and remove axes
    ax.set_title(f"{order} Congressional Session", fontsize=16)
    ax.axis('off')
    
    # Add the historical fact as text at the bottom
    plt.figtext(0.5, 0.02, fact, wrap=True, horizontalalignment='center', fontsize=12)
    
    return fig

# -------------- Slideshow Display Functions --------------

def display_slideshow_auto(merged_gdf, interval=0, refresh_count=0):
    """
    Displays a slideshow of congressional sessions with automatic transitions.
    
    Parameters:
    - merged_gdf (GeoDataFrame): The merged GeoDataFrame containing session data.
    - interval (int): Time in seconds each session is displayed.
    - refresh_count (int): Counter to control caching of historical facts.
    """
    placeholder = st.empty()
    
    # Get unique session orders in desired order
    unique_sessions = merged_gdf['district_n'].unique()
    
    for district_n in unique_sessions:
        # Filter all geometries for the current session
        session_gdf = merged_gdf[merged_gdf['district_n'] == district_n]
        geometries = session_gdf['geometry'].tolist()
        
        # Extract the order (e.g., "1st")
        order = session_gdf['order'].iloc[0]
        
        # Fetch the historical fact (using the first row's dates)
        first_row = session_gdf.iloc[0]
        fact = get_historical_fact(
            district_n, 
            first_row['start_date'], 
            first_row['end_date'], 
            refresh_count
        )
        
        # Generate the plot with the order
        fig = plot_district(order, geometries, fact)
        
        # Display the plot
        with placeholder.container():
            st.pyplot(fig)
        
        plt.close(fig)  # Close the figure to free memory
        time.sleep(interval)
    
    # The following code seems redundant and references a 'current_slide' that isn't initialized
    # It's best to remove or comment it out unless you have a mechanism to handle 'current_slide'
    """
    # Display the current slide
    current_district = unique_districts[st.session_state.current_slide]
    district_gdf = merged_gdf[merged_gdf['district_n'] == current_district]
    geometries = district_gdf['geometry'].tolist()
    
    # Fetch the historical fact (using the first row's dates)
    first_row = district_gdf.iloc[0]
    fact = get_historical_fact(current_district, first_row['start_date'], first_row['end_date'])
    
    # Generate the plot
    fig = plot_district(current_district, geometries, fact)
    
    st.pyplot(fig)
    plt.close(fig)  # Close the figure to free memory
    
    # Display slide number
    st.write(f"Slide {st.session_state.current_slide + 1} of {len(unique_districts)}")
    """




    # # Display the current slide
    # current_district = unique_districts[st.session_state.current_slide]
    # district_gdf = merged_gdf[merged_gdf['district_n'] == current_district]
    # geometries = district_gdf['geometry'].tolist()
    
    # # Fetch the historical fact (using the first row's dates)
    # first_row = district_gdf.iloc[0]
    # fact = get_historical_fact(current_district, first_row['start_date'], first_row['end_date'])
    
    # # Generate the plot
    # fig = plot_district(current_district, geometries, fact)
    
    # st.pyplot(fig)
    # plt.close(fig)  # Close the figure to free memory
    
    # # Display slide number
    # st.write(f"Slide {st.session_state.current_slide + 1} of {len(unique_districts)}")

# -------------- Main Function --------------

def main():
    # Initialize refresh_count in session state
    set_custom_style()
    if 'refresh_count' not in st.session_state:
        st.session_state.refresh_count = 0

    # Load and combine shapefiles
    with st.spinner("📦 Loading and combining shapefiles..."):
        combined_gdf = load_and_combine_shapefiles()
    
    if combined_gdf is None:
        st.stop()
    
    # Create mapping dataframe
    district_dates = create_mapping_dataframe()
    
    # Merge data
    merged_gdf = merge_data(combined_gdf, district_dates)
    st.markdown(
    """
    <div style="font-size:16px; color:#4CAF50; font-weight: bold;">
        Slow Down Animation 
    </div>
    """,
    unsafe_allow_html=True
    )
    # Choose slideshow type (currently automatic)
    interval = st.slider("", min_value=1, max_value=10, value=1)
    if st.button("🔄 Rerun Animation"):
        st.session_state.refresh_count += 1
    # Display the automatic slideshow with current refresh_count
    display_slideshow_auto(merged_gdf, interval, refresh_count=st.session_state.refresh_count)
    
    # Add the Refresh button below the slideshow

    
    # Optionally, provide a download option for historical facts
    # This could involve downloading a CSV or similar


    
    # Optionally, provide a download option for historical facts
    # This could involve downloading a CSV or similar

if __name__ == "__main__":
    main()