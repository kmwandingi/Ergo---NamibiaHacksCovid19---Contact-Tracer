# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 13:04:18 2020

@author: mwandingik
"""

import streamlit as st

#!/usr/bin/env python3

import collections
import fnmatch
import folium
from folium.plugins import HeatMap
from folium.plugins import HeatMapWithTime
import ijson
import json
import os
from progressbar import ProgressBar, Bar, ETA, Percentage
import webbrowser
import zipfile
from PIL import Image
import pandas as pd
import numpy as np
import pydeck as pdk

from datetime import datetime, timedelta

#os.chdir('C:/Users/mwandingik/Box/Github/hp/') #local drive to save map html
cwd = os.getcwd()
image = Image.open('bw.png')
st.image(image, width = 130, format ='PNG')

st.markdown("<h1 style='text-align: center; color: green;'>Ergo - NamibiaHacksCovid19</h1>", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: black;'>Where has't thee been?</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: black;'>Download location data that google has on you at the following link...</h3>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center'><p><a href='https://takeout.google.com/' >https://takeout.google.com </p></a></div>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: black;'>You need to select and download ONLY your 'Location History' in 'JSON' format as zip file, choose your desired date range below and load the zip file.</p>", unsafe_allow_html=True)

# data = st.radio("",('ALL', 'Add Date Range'))
st.markdown("<p style='text-align: center; color: black;'>Choose Date Range</p>", unsafe_allow_html=True)

start_date,end_date = None, None


today = datetime.today() - timedelta(days=90)
tomorrow = today + timedelta(days=56)
start_date = st.date_input('Start date', today)
end_date = st.date_input('End date', tomorrow)
min_date, max_date = (str(start_date), str(end_date))

# st.success("Plot all data")
# min_date, max_date = (None, None)
    
if start_date is not None:    
    if start_date < end_date:
        st.success('Start date: `%s`\n\nEnd date: `%s`' % (start_date, end_date))
    else:
        st.error('Error: End date must fall after start date.')


fname = st.file_uploader("", type = ["zip"])

# importing required modules 
from zipfile import ZipFile 
  
# specifying the zip file name (if file is local)
#fname = "takeout-20200320T061637Z-005.zip" 

#Initialise globals
a = None
e = folium.Map()
file_count = 0

#min_date, max_date = (None, None)
date_range = min_date, max_date
stream_data = False
settings = {
            "tiles": "OpenStreetMap",
            "zoom_start": 10,
            "radius": 7,
            "blur": 4,
            "min_opacity": 0.2,
            "max_zoom": 10
        }

coordinates = collections.defaultdict(int)
time = collections.defaultdict(int)

TEXT_BASED_BROWSERS = [webbrowser.GenericBrowser, webbrowser.Elinks]

def isTextBasedBrowser(browser):
    """Returns if browser is a text-based browser.

    Arguments:
        browser {webbrowser.BaseBrowser} -- A browser.

    Returns:
        bool -- True if browser is text-based, False if browser is not
            text-based.
    """
    for tb_browser in TEXT_BASED_BROWSERS:
        if type(browser) is tb_browser:
            return True
    return False


def timestampInRange(timestamp, date_range):
    """Returns if the timestamp is in the date range.

    Arguments:
        timestamp {str} -- A timestamp (in ms).
        date_range {tuple} -- A tuple of strings representing the date range.
        (min_date, max_date) (Date format: yyyy-mm-dd)
    """
    if date_range == (None, None):
        return True
    date_str = datetime.fromtimestamp(
        int(timestamp) / 1000).strftime("%Y-%m-%d")

    return dateInRange(date_str, date_range)


def dateInRange(date, date_range):
    """Returns if the date is in the date range.

    Arguments:
        date {str} -- A date (Format: yyyy-mm-dd).
        date_range {tuple} -- A tuple of strings representing the date range.
        (min_date, max_date) (Date format: yyyy-mm-dd)
    """
    if date_range == (None, None):
        return True
    if date_range[0] == None:
        min_date = None
    else:
        min_date = datetime.strptime(date_range[0], "%Y-%m-%d")
    if date_range[1] == None:
        max_date = None
    else:
        max_date = datetime.strptime(date_range[1], "%Y-%m-%d")
    date = datetime.strptime(date, "%Y-%m-%d")
    return (min_date is None or min_date <= date) and \
        (max_date is None or max_date >= date)
        
def updateCoord(coords):
    global max_coordinates, max_magnitude
    max_coordinates = (0, 0)
    max_magnitude = 0
    coordinates[coords] += 1
    time[date_index] += 1
    if coordinates[coords] > max_magnitude:
        max_coordinates = coords
        max_magnitude = coordinates[coords]
    

def loadJSONData(json_file, date_range):
    """Loads the Google location data from the given json file.

    Arguments:
        json_file {file} -- An open file-like object with JSON-encoded
            Google location data.
        date_range {tuple} -- A tuple containing the min-date and max-date.
            e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
    """
    global date_index, coords
    data = json.load(json_file)
    w = [Bar(), Percentage(), " ", ETA()]
    with ProgressBar(max_value=len(data["locations"]), widgets=w) as pb:
        for i, loc in enumerate(data["locations"]):
            if "latitudeE7" not in loc or "longitudeE7" not in loc:
                continue
            coords = (round(loc["latitudeE7"] / 1e7, 6),
                       round(loc["longitudeE7"] / 1e7, 6))
            
            date_index = datetime.fromtimestamp(int(loc["timestampMs"]) / 1000).strftime("%Y-%m-%d, %H:%M:%S")

            if timestampInRange(loc["timestampMs"], date_range):
                updateCoord(coords)
            pb.update(i)
    generateMap(settings)
    
def streamJSONData(json_file, date_range):
    """Stream the Google location data from the given json file.
    
    Arguments:
        json_file {file} -- An open file-like object with JSON-encoded
            Google location data.
        date_range {tuple} -- A tuple containing the min-date and max-date.
            e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
    """
    # Estimate location amount
    max_value_est = sum(1 for line in json_file) / 13
    json_file.seek(0)
    locations = ijson.items(json_file, "locations.item")
    w = [Bar(), Percentage(), " ", ETA()]
    with ProgressBar(max_value=max_value_est, widgets=w) as pb:
        for i, loc in enumerate(locations):
            if "latitudeE7" not in loc or "longitudeE7" not in loc:
                continue
            coords = (round(loc["latitudeE7"] / 1e7, 6),
                        round(loc["longitudeE7"] / 1e7, 6))
            date_index = datetime.fromtimestamp( int(loc["timestampMs"]) / 1000).strftime("%Y-%m-%d")
            
            if timestampInRange(loc["timestampMs"], date_range):
                updateCoord(coords)
                
            if i > max_value_est:
                max_value_est = i
                pb.max_value = i
            pb.update(i)
    generateMap(settings)

def loadGPXData(file_name, date_range):
        """Loads location data from the given GPX file.

        Arguments:
            file_name {string or file} -- The name of the GPX file
                (or an open file-like object) with the GPX data.
            date_range {tuple} -- A tuple containing the min-date and max-date.
                e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
        """
        xmldoc = minidom.parse(file_name)
        gxtrack = xmldoc.getElementsByTagName("trkpt")
        w = [Bar(), Percentage(), " ", ETA()]

        with ProgressBar(max_value=len(gxtrack), widgets=w) as pb:
            for i, trkpt in enumerate(gxtrack):
                lat = trkpt.getAttribute("lat")
                lon = trkpt.getAttribute("lon")
                coords = (round(float(lat), 6), round(float(lon), 6))
                date = trkpt.getElementsByTagName("time")[0].firstChild.data
                if dateInRange(date[:10], date_range):
                    updateCoord(coords)
                pb.update(i)
        generateMap(settings)
       
def generateMap(settings):
    """Generates the heatmap.
    
    Arguments:
        settings {dict} -- The settings for the heatmap.
    
    Returns:
        Map -- The Heatmap.
    """
    global m, a, coordinates, time, mdata, map_data, date_data
    
    tiles = settings["tiles"]
    zoom_start = settings["zoom_start"]
    radius = settings["radius"]
    blur = settings["blur"]
    min_opacity = settings["min_opacity"]
    max_zoom = settings["max_zoom"]
    
    #data for folium heatmap
    map_data = [[coords[0], coords[1], magnitude]
                for coords, magnitude in coordinates.items()]
        
    
    date_data = [[date_index[0]]
                for date_index in time.items()]
    
    #data for py deck heatmap
    # a = pd.DataFrame(map_data)
    # a['Time'] = pd.DataFrame(date_data)
    # a.columns=['lat', 'lon','weight', 'time']
    
    # Generate map
    m = folium.Map(location=max_coordinates,
                   zoom_start=zoom_start,
                   tiles=tiles,
                   max_val=1000,
                   blur=blur,
                   height = "100%", 
                   width = "100%")

    #Generate heat map
    HeatMap(map_data, gradient = gradient,
                      max_val=1000,
                      min_opacity=min_opacity,
                      radius=radius,
                      blur=blur,
                      max_zoom=max_zoom,
                      name = 'Heatmap').add_to(m)
    
    h = HeatMap(map_data, gradient = gradient,
                      max_val=1000,
                      min_opacity=min_opacity,
                      radius=radius,
                      blur=blur,
                      max_zoom=max_zoom,
                      overlay=True,
                      name = jname + ' Heatmap')
    
    
    if len(date_data)==len(map_data):
        mdata = [([map_data[i]] +[ map_data[i]]) for i in range(len(date_data))]
    elif len(date_data)>len(map_data):
        date_data = date_data[:len(map_data)]
        mdata = [([map_data[i]] +[ map_data[i]]) for i in range(len(date_data))]
    else:
        map_data = map_data[:len(date_data)]
        mdata = [([map_data[i]] + [ map_data[i]]) for i in range(len(date_data))]
    
    #Genarate heatmap with time
    HeatMapWithTime(mdata, gradient = gradient,
                        index=date_data,
                        auto_play=True, 
                        radius=15,
                        max_opacity=3,
                        name = "With time").add_to(m)
    
    t = HeatMapWithTime(mdata, gradient = gradient,
                             index=date_data,
                             auto_play=True, 
                             radius=15,
                             max_opacity=3,
                             name = jname + " With time")
    
    folium.LayerControl().add_to(m)
    m.save(output_file)
    allmaps(h,t)
    
    coordinates = collections.defaultdict(int)
    time = collections.defaultdict(int)
    
    return m, a

def allmaps(h,t):
    '''
    add all location history maps to one map
    
    '''
    if len(data_path)>1:
        global e
        h.add_to(e)
        t.add_to(e)
    
def addlayerCtrl():
    '''
    add layer controls and save the combined map
    
    '''
    if len(data_path)>1:
        global e
        folium.LayerControl().add_to(e)
        output_file = cwd + "\\all.html"
        e.save(output_file)

from bs4 import BeautifulSoup

#Read zip files, find json location histories and loop through them.
if fname is not None:
    zip_file = zipfile.ZipFile(fname,"r")
    namelist = zip_file.namelist() 
        
    (html_path,) = fnmatch.filter(namelist, "Takeout/*.html")
    with zip_file.open(html_path) as read_file:
        soup = BeautifulSoup(read_file, "html.parser")
    (elem,) = soup.select(
        "#service-tile-LOCATION_HISTORY > button > div.service_summary > div > h1[data-english-name=LOCATION_HISTORY]")
    name = elem["data-folder-name"]
    data_path = fnmatch.filter(
        namelist,
        "Takeout/Location History/Location History*.json".format(name=name))
    for path in data_path:
        jname = path.rsplit('/',1)[1].rsplit('.',1)[0]
        output_file = cwd + "\\" + jname + ".html"
        print("Reading location data file from zip archive: {!r}".format(
            path))
        file_count += 1
        if path.endswith(".json"):
            if file_count == 1:
                gradient= None
            elif file_count == 2:
                gradient={.4: 'yellow', .65: 'orange', 1: 'red'}
            elif file_count == 3:
                gradient={.4: 'grey', .65: 'pink', 1: 'purple'}
            else:
                gradient={.4: 'lightblue', .65: 'lightgreen', 1: 'green'}
                
            with zip_file.open(path) as read_file:
                loadJSONData(read_file, date_range)
                if stream_data:
                    streamJSONData(read_file, date_range)
        else:
            raise ValueError("unsupported extension for {!r}: only .json supported"
                .format(zip_file))
    addlayerCtrl()
        
    # if fname.endswith(".gpx"):
    #     loadGPXData(fname, date_range)
          
if fname is not None:  
    if len(data_path)>1:
        output_file = cwd + "\\all.html"
    else:
        output_file = output_file
        
    if not isTextBasedBrowser(webbrowser.get()):
            try:
                print("[info] Opening {} in browser".format(output_file))
                webbrowser.open("file://" + os.path.realpath(output_file))
            except webbrowser.Error:
                print("[info] No runnable browser found. Open {} manually.".format(
                    output_file))
                print("[info] Path to heatmap file: \"{}\"".format(os.path.abspath(output_file)))
#Pydeck plot heatmap
# if a is not None:
#     midpoint = (np.average(a["lat"]), np.average(a["lon"]))
#     st.write(pdk.Deck(
#         map_style="mapbox://styles/mapbox/dark-v9",
#         initial_view_state={
#             "latitude": midpoint[0],
#             "longitude": midpoint[1],
#             "zoom": 15,
#             "pitch": 50,
#         },
#         layers=[
#             pdk.Layer(
#                 "HeatmapLayer",
#                 data=a,
#                 get_position=["lon", "lat"],
#                 get_weight='weight',
#             ),
#         ],
#     ))

                
st.markdown("<footer style= 'text-align: center'><a href='mailto:info@ergoanalyticscc.com'> info@ergoanalyticscc.com </a></footer>", unsafe_allow_html=True)

center_style = """
        <style>
        * {text-align: center;}
        </style>
        """
st.markdown(center_style, unsafe_allow_html=True)

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

