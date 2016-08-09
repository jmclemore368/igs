def meters_to_lat(meter):
    """
        Converts meters to latitude

        At 0 deg lat, 1 m approx 9.04371732957e-6 deg
        (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
    """
    return meter * 9.04371732957e-6 #1/110574.0

def meters_to_lon(meter):
    """
        Converts meters to longitude

        At 0 deg long, 1 m approx 9.04371732957e-6
        (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
    """
    return meter * 8.983111749911e-6 #1/111320.0

def lat_to_meters(lat):
    """
        Converts latitude to meters

        At 0 deg lat, 1 deg lat approx 110.574 km 
        (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
    """
    return lat * 110574.0

def lon_to_meters(lon):
    """
        Converts latitude to meters

        At 0 deg long, 1 deg long approx 111.320 km 
        (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
    """
    return lon * 111320.0

