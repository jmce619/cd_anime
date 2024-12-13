import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import openai
import time
from shapely.geometry import Polygon, MultiPolygon
from pathlib import Path  # Added missing import

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
def load_shapefile(district_n, parent_dir='./early_shapefiles'):
    """
    Load a single shapefile for the specified district number.

    Parameters:
    - district_n (str): The three-digit district number (e.g., "001").
    - parent_dir (str or Path): The parent directory containing shapefiles.

    Returns:
    - gdf (GeoDataFrame): The GeoDataFrame of the loaded shapefile, or None if loading fails.
    - message (str): Success or error message related to loading the shapefile.
    """
    parent_dir = Path(parent_dir)
    district_folder = parent_dir / f"districts{district_n}" / "districtShapes"
    shapefile_path = district_folder / f"districts{district_n}.shp"

    if shapefile_path.exists():
        try:
            gdf = gpd.read_file(shapefile_path)
            gdf['district_n'] = district_n  # Ensure consistent column naming
           
            return gdf
        except Exception as e:
            
            return None
    else:

        return None


@st.cache_data
def create_mapping_dataframe():
    """
    Create a mapping DataFrame that links each district to its congressional session and date range.
    """
    district_dates = pd.DataFrame({
        'district_n': [f"{i:03}" for i in range(1, 26)],
        'order': [
            '1st', '2nd', '3rd', '4th', '5th',
            '6th', '7th', '8th', '9th', '10th',
            '11th', '12th', '13th', '14th', '15th',
            '16th', '17th', '18th', '19th', '20th',
            '21st', '22nd', '23rd', '24th', '25th'
        ],
        'order': [
            '1st', '2nd', '3rd', '4th', '5th',
            '6th', '7th', '8th', '9th', '10th',
            '11th', '12th', '13th', '14th', '15th',
            '16th', '17th', '18th', '19th', '20th',
            '21st', '22nd', '23rd', '24th', '25th'
        ],
        'order_num': list(range(1, 26)),
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
def process_date_ranges(district_dates):
    """
    Process the 'date_range' column into separate 'start_date' and 'end_date' datetime columns.

    Parameters:
    - district_dates (DataFrame): The mapping DataFrame with 'date_range' column.

    Returns:
    - district_dates (DataFrame): Updated DataFrame with 'start_date' and 'end_date' columns.
    """
    district_dates[['start_date', 'end_date']] = district_dates['date_range'].str.split(' to ', expand=True)
    district_dates['start_date'] = pd.to_datetime(district_dates['start_date'])
    district_dates['end_date'] = pd.to_datetime(district_dates['end_date'])
    return district_dates

# -------------- Historical Facts Caching Function --------------

@st.cache_data
def get_historical_fact(district_n, start_date, end_date):

    date_str = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that responds with an interesting fact. The statement should not be framed as an answer to a question, but rather as a historical fact. Start differently each time"},
                {"role": "user", "content": f"State an interesting or exciting historical fact about the United States that occurred between {date_str}."}
            ],
            temperature=0.7
        )  
        
        fact = response.choices[0].message.content.strip()
    except Exception as e:
        fact = "Historical fact not available."
        st.error(f"Error fetching data from OpenAI for District {district_n}: {e}")

    return fact

# -------------- Plotting Function --------------

def plot_district(order, geometries, fact, dates):
    """
    Generates a Matplotlib figure for the given congressional session with all its geometries.

    Parameters:
    - order (str): The order of the congressional session (e.g., "1st").
    - geometries (list): A list of geometries (Polygons or MultiPolygons) for the session.
    - fact (str): The historical fact to display.

    Returns:
    - fig: The Matplotlib figure object.
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    # Convert geometries to GeoSeries for plotting
    if isinstance(geometries, list):
        geometries = gpd.GeoSeries(geometries)
    elif isinstance(geometries, (Polygon, MultiPolygon)):
        geometries = gpd.GeoSeries([geometries])
    elif isinstance(geometries, gpd.GeoSeries):
        pass  # Already a GeoSeries
    else:
        st.warning("Invalid geometry type provided.")
        return fig  # Return empty figure

    # Plot all geometries for the congressional session
    geometries.plot(ax=ax, color='skyblue', edgecolor='black')

    # Set the title and remove axes
    ax.set_title(f"{order} Congressional Session ({dates})", fontsize=16)
    ax.axis('off')

    # Add the historical fact as text at the bottom
    plt.figtext(0.5, 0.02, fact, wrap=True, horizontalalignment='center', fontsize=12)

    return fig

# -------------- Slideshow Display Function --------------

def display_slideshow_auto(district_dates, interval=0):
    """
  
    """
    placeholder = st.empty()

    # Sort districts numerically based on 'order_num'
    ordered_districts = district_dates.sort_values('order_num')['district_n'].tolist()

    for district_n in ordered_districts:
        with placeholder.container():
            # Initialize a container to hold all dynamic content
            container = st.container()

            with st.spinner(f"Loading District {district_n}..."):
                # Load the shapefile for the current district
                district_gdf = load_shapefile(district_n)

            # Display the load message

            if district_gdf is not None:
                # Fetch the mapping data for the current district
                mapping_row = district_dates[district_dates['district_n'] == district_n].iloc[0]
                order = mapping_row['order']
                start_date = mapping_row['start_date']
                end_date = mapping_row['end_date']

                # Fetch the historical fact
                fact = get_historical_fact(district_n, start_date, end_date)

                # Generate the plot
                fig = plot_district(order, district_gdf['geometry'].tolist(), fact,f"{mapping_row['start_date']}-{mapping_row['end_date']}")

                # Display the plot
                container.pyplot(fig)

                plt.close(fig)  # Close the figure to free memory

            # Wait for the specified interval before moving to the next slide
            time.sleep(interval)



# -------------- Main Function --------------

def main():
    # Apply custom styling
    set_custom_style()

    # Initialize refresh_count in session state
    if 'refresh_count' not in st.session_state:
        st.session_state.refresh_count = 0

    # Create mapping dataframe
    district_dates = create_mapping_dataframe()
    district_dates = process_date_ranges(district_dates)

    # UI Elements
    st.markdown(
        """
        <div style="font-size:16px; color:#4CAF50; font-weight: bold;">
            Slow Down Animation 
        </div>
        """,
        unsafe_allow_html=True
    )

    # Slider to set slideshow interval

    interval = st.slider("", min_value=0, max_value=10, value=0)

    # Display the automatic slideshow with current refresh_count
    display_slideshow_auto(district_dates, interval, refresh_count=st.session_state.refresh_count)

    # Button to rerun animation and refresh historical facts
    if st.button("🔄 Rerun Animation"):
        st.session_state.refresh_count += 1
        st.experimental_rerun()  # Rerun the app to restart the slideshow
    # Optionally, provide a download option for historical facts
    # (Implementation depends on how facts are stored; omitted for brevity)

if __name__ == "__main__":
    main()