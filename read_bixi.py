# -*- coding: utf-8 -*-
"""
Created on Wed May 31 23:59:25 2017

@author: Colin-N. Brosseau
"""
import time
import numpy as np
import bz2
import glob
import os
from xml.dom import minidom
from convertyaml_map import convertXml2YamlAux
import datetime

import matplotlib.pylab as plt

"""
Remarks:
    Sometimes, some stations appear or disappear.
    See for example between 2017-06-05_07:24:00.xml.bz2 and 
    2017-06-05_07:25:00.xml.bz2
    
    The server is refreshed at each 120 second in mean. Refresh time is 120 +/- 5 s.

    At some times, the number of docks at some stations change. For exemple,
    on 2017-06-05 station 'De la Commune / King' passed from 48 docks to
    88 docks.
    
    Most of the stations seems to have a bug in their total number of docks.
    For exemple, station 'De la Commune / King' sometimes fluctuate between
    88 and 89 docks. Sometimes it goes down to 1-2 for few minutes and go back
    to 88-89.
"""

class BadXMLFile(Exception):
    """
    Represents a bad .xml file.
    """
    pass

def bixi2np(filename):
    """
    Extract most interresting content of a bixi status file: time, bikes 
    avalables, stations names and maximal number of bikes.
    

    Parameters
    ----------
    filename : str
    
        File to import. Must be in format .xml.bz2. 
        Files are taken from https://montreal.bixi.com/data/bikeStations.xml


    Returns
    -------
    measurement_time : int
        Time of measurement in Epoch (Unix) time.    

    
    bikes_available: ndarray, shape (n_stations,)
        Bikes availables.

    
    max_bikes: ndarray, shape (n_stations,)
        Maximal number of bikes.


    list_stations: list of str,  shape (n_stations,)
        Stations names. Called 'terminalName' in the original file.    
    """
    try:
        d = bixi2dict(filename)  # dict containing all stations
    except BadXMLFile:
        raise BadXMLFile(filename)
        
    list_stations = sorted(d)
    bikes_available = np.zeros(len(list_stations), dtype=np.uint8)
    last_comm_with_server = np.zeros(len(list_stations), dtype=np.uint32)
    max_bikes = np.zeros(len(list_stations), dtype=np.uint8)
    #print(output.size())
    i = 0
    for station in list_stations:
        bikes_available[i] = d[station]['nbBikes']
        last_comm_with_server[i] = int(d[station]['lastCommWithServer']/1000)
        max_bikes[i] = bikes_available[i] + d[station]['nbEmptyDocks']
        i += 1
    # time of measurement
    measurement_time = np.max(last_comm_with_server)
    return measurement_time, bikes_available, max_bikes, list_stations

def bixi2dict(filename):
    """
    Extract content of a bixi status file to a dictionnary.
    

    Parameters
    ----------
    filename : str
    
        File to import. Must be in format .xml.bz2. 
        Files are taken from https://montreal.bixi.com/data/bikeStations.xml


    Returns
    -------
    stations : dict of dicts
        Each element represents a station. Keys are 'terminalName'.  
        A station is itself a dict with fields:
            'id' : int
                id of the station
                
                
            'installed' : bool
                    
                    
            'lastCommWithServer' : int
                time of last communication with the server  . 
                Epoch (Unix) time * 1000           
            
        
            'lastUpdateTime' : 
                time of last update of the station  . 
                Epoch (Unix) time * 1000           
            
            
            'lat' : float
                lattitude of the station        
            
            
            'locked' : bool            
            
            
            'long' : float
                longitude of the station            
                
            
            'name' : str
                name of the station (street corners)
            
            
            'nbBikes' : int
                number of available bikes
            
            
            'nbEmptyDocks' : int
                number of empty docks
                
                
            'public' : bool
            
            
            'temporary' :bool
            
            
            'terminalName' : int
                terminal name
    """
    def convertXml2dict(filename):
        """
        Convert a .xml file to a dictionary.
        
            
        Parameters
        ----------
        filename : str
        
            File to import. Must be in format .xml.
    
    
        Returns
        -------
        output : dict
            Dictionnary reprensentation of the .xml file        
        """
        try:
            doc = minidom.parse(filename)
        except:
            raise BadXMLFile(filename)
        else:
            root = doc.childNodes[0]
            # Convert the DOM tree into "YAML-able" data structures.
            output = convertXml2YamlAux(root)
            return output

    try:
        d = convertXml2dict(bz2.BZ2File(filename, 'r'))  # load data
    except BadXMLFile:
        raise BadXMLFile(filename)
    else:        
        stations = {}  # dict of dict each one representing a station
        for index_station in range(len(d['children'])):
        
            dict_out = {}
            for i_element in range(len(d['children'][index_station]['children'])):
                try:
                    field = d['children'][index_station]['children'][i_element]['name']
                    content = d['children'][index_station]['children'][i_element]['text']
                    dict_out[field] = content
                except:
                    pass
            list_int = ['id', 'lastCommWithServer', 'lastUpdateTime', 'nbBikes', 'nbEmptyDocks', 'terminalName']
            for key in list_int:
                dict_out[key] = int(dict_out[key])
            list_bool = ['installed', 'locked', 'public', 'temporary']
            for key in list_bool:
                dict_out[key] = bool(dict_out[key])
            list_float = ['lat', 'long']
            for key in list_float:
                dict_out[key] = float(dict_out[key])
                
            stations[str(dict_out['terminalName'])] = dict_out
        return stations
    

def read_day(year, month, day, directory='.', verbose=0):
    """
    Read all available data for one day.

    Data files are supposed to be in format AAAA-MM-DD_xxxxxx.xml.bz2. Where
    AAAA is year, MM is month, DD is day. xxxxxx could be anything. Files must be 
    in .xml.bz2 format.
    

    Parameters
    ----------
    year : int
    
        Year (YYYY) to import.


    month : int
    
        month to import.


    day : int
    
        Day to import.


    directory : str
    
        Source directory for the files.

    
    verbose : int, [0, 1, 2]
        
        Level of verbosity


    Returns
    -------
    time_vector: int, shape (n_measurements,)


    bikes_available: dict

        Each element is the number of bikes available (shape (n_measurements,)) in the corresponding station (key is 'terminalName').


    max_bikes: dict

        Each element is the maximum number of bikes available (shape (n_measurements,)) in the corresponding station (key is 'terminalName').


    stations_metadata: dict

        Each element is a dictionary of metadata for the corresponing station (key is 'terminalName').
        Metadata available:
            'id': int
            'installed': bool
            'lat': float
                lattitude
            'locked': bool
            'long': float
                longitude
            'name': str
                name of the station (human readable)
            'public': bool
            'temporary': bool

    Possible bug: if a station disappear and reapear during the day, corresponding bikes_abailable and max_bikes will be wrong
    """
    list_filename = sorted(glob.glob(os.path.join(directory, "%04d-%02d-%02d_*.xml.bz2" % (year, month, day))))
    
    # The set of stations  sometimes change through the day. So we cannot know
    # in advance present stations.
    # It is not possible to know in advance number of points in time.
    # Some measurents are the same as the one before. Sometime files are corrupted.

    # output vectors
    time_vector = np.array([])  # vector of time
    bikes_available = {}  # Current bikes in station
    max_bikes = {}  # Maximum bikes in station. Number of docks.
    stations_metadata = {}  # Metadata for stations
    
    i = 1
    for filename in list_filename:
        current_status = {}  # used for creating stations_metadata
        if verbose > 0:
            print(str(i) + "/" + str(len(list_filename))  +  "   " + filename)
        try:
            time_, bikes_available_, max_bikes_, list_stations_ = bixi2np(filename)
        except BadXMLFile:
            if verbose > 0:
                print("Bad .xml file: " + filename)
            else:
                pass
        else:
            if time_ not in time_vector:
                time_vector = np.append(time_vector, time_)
                for station, bikes, max_bik in zip(list_stations_, bikes_available_, max_bikes_):
                    try: 
                        bikes_available[station] = np.append(bikes_available[station], bikes)
                        max_bikes[station] = np.append(max_bikes[station], max_bik)
                    except KeyError:
                        bikes_available[station] = np.empty(len(time_vector), dtype=np.uint8)  * np.nan
                        bikes_available[station][-1] = bikes
                        max_bikes[station] = np.empty(len(time_vector), dtype=np.uint8)  * np.nan
                        max_bikes[station][-1] = max_bik
                        
                        #  Add station metadata
                        try:
                            stations_metadata[station] = current_status[station]
                        except KeyError:
                            current_status = bixi2dict(filename)  # current status. Will be reused for other stations.
                            stations_metadata[station] = current_status[station]
                            if verbose > 1:
                                print('load current status')
                        del stations_metadata[station]['nbBikes']
                        del stations_metadata[station]['lastCommWithServer']
                        del stations_metadata[station]['lastUpdateTime']
                        del stations_metadata[station]['terminalName']
                        del stations_metadata[station]['nbEmptyDocks']
                        if verbose > 1:
                            print('add station ' + str(station))
        i += 1

    # Check that all vectors have the same length
    for station in bikes_available:
        if len(bikes_available[station]) < len(time_vector):  # this appends when stations disappear in the middle of the day
            if verbose > 1:
                print(str(station) + ' was wrong in length. Now corrected.')
            remaining_items = np.empty(len(time_vector) - len(bikes_available[station]), dtype=np.uint8)  * np.nan
            bikes_available[station] = np.append(bikes_available[station], remaining_items)
            max_bikes[station] = np.append(max_bikes[station], remaining_items)

    # Check for missing informations in stations_metadata
    if len(stations_metadata.keys()) != len(bikes_available.keys()):
        print("missings informations in stations_metadata")
            
    return time_vector, bikes_available, max_bikes, stations_metadata


def day2file(year, month, day, directory='.', verbose=0):
    """
    Export the data of one day to a numpy file.
    """
    print("%04d%02d%02d" % (year, month, day))
    # Todo: read a bit before and a bit after (few minutes) to take care of the time offset
    t, x, mx, md = read_day(year, month, day, directory=directory, verbose=verbose)
    try:  # day without data will not crash the program
        # Format the time in a human readable form
        t = format_time(t)  # t is now an array (see function below)
        # resample data over time vector. Time vector is now evenly spaced.
        resample_time(t[:, 2:3], x)  # Resample the available bikes
        minute = resample_time(t[:, 2:3], mx)  # Resample the number of docks
        year_day = np.ones_like(minute) * t[0, 0]  # Recreate the day of the year column
        weekday = np.ones_like(minute) * t[0, 1]  # Recreate the weekday column
        t = np.concatenate((year_day, weekday, minute), axis=1)
        # save data to file
        np.savez_compressed("%04d%02d%02d" % (year, month, day), time=t, bikes=x, max_bikes=mx, metadata=md)

    
def file2day(year, month, day, directory='.'):
    """
    Read data for one day from a numpy file.
    """
    filename = os.path.join(directory, "%04d%02d%02d.npz" % (year, month, day))
    data = np.load(filename)
    return data['time'], data['bikes'][()], data['max_bikes'][()], data['metadata'][()] 


def format_time(t):
    """
    Format time vector to a human readable form.
    """
    # Todo: use the real time (midnight at given date) as reference instead of t[0]
    i = 5  # we use the  tenth reading for weekday and year_day (sometimes there is a 2 minutes offset)
    minute = np.array((t - t[0])/60)[:, np.newaxis]  # minutes of the day
    weekday = np.ones_like(minute) * datetime.datetime.fromtimestamp(int(t[i])).weekday()  # day of the week. monday=0
    year_day = np.ones_like(minute) * datetime.datetime.fromtimestamp(int(t[i])).timetuple().tm_yday  # day of the year
    return np.concatenate((year_day, weekday, minute), axis=1)


def resample_time(X, y):
    """
    Calculate values over a even spaced vector.
    Output time vector is 0 -> 1438 with steps of 2. Unit is minutes.
    If y is a dictionnary, each key represent a vector (y). It then resample every vector
    """
    if isinstance(y, dict):
        for key in y:
            x_fit, y_fit = resample_time(X, y[key])
            y[key] = y_fit
        return x_fit
    else:
        if len(np.shape(X)) == 1:  # X vector must have 2 dimensions. If needed, create a simgleton dimension.
            X = X[:, np.newaxis]
        from sklearn.tree import DecisionTreeRegressor
        regressor = DecisionTreeRegressor(random_state = 0)
        regressor.fit(X, y)
        x_fit = np.arange(0, 1440, 2)[:, np.newaxis] 
        y_fit = regressor.predict(x_fit)
        #plt.scatter(X, y, color = 'red')
        #plt.plot(x_fit, y_fit, '.:', color = 'blue')
        #plt.show()
        return x_fit, y_fit
    

if __name__ == '__main__':
    t, x, max_x, md = read_day(2017, 6, 10)
