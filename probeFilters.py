"""Functions for filtering a group of probes to enforce geographic diversity or ASN diversity."""

from ripe.atlas.cousteau import Probe, ProbeRequest
from collections import Counter, defaultdict
import math

def select_diverse_subset(probe_list, k, probes_per_asn = math.inf):
    """Selects k probes, given a list of probes, to maximize geographic diversity. 
    
    Parameters
    ----------
    probe_list: list (of dictionaries)
        A list of probe dictionaries, with info such as their coordinates and ASN. This can be obtained from 
        ripe.atlas.cousteau's ProbeRequest, or from get_probes_by_id() defined below. 
    k: int
        The number of probes to select from the list.
    probes_per_asn: int 
        An optional constraint to enforce ASN diversity. For example, perhaps you do not want more than 2 probes to
        be selected from the same ASN. 

    Returns
    -------
    selected: list (of dictionaries)
        A subset of probe_list, of length k, that maximizes geographic diversity. 
    """

    print("Selecting", k, "probes for diversity...this may take a while.")
    probes = [probe for probe in probe_list if probe['geometry'] is not None]
    if len(probes) < len(probe_list):
        print("Alert: some probes coordinates are not known (or are software probes). These will not be chosen.")

    selected = [probes[0]] #Arbitrarily selects first probe to start. 
    asn_counts = Counter({selected[0]['asn_v4']: 1}) #Counts occurences of ASNs we selected. 
    #asn_v4 and asn_v6 for the same probe are rarely different, so for simplicity only asn_v4 is considered. 
    probes = probes[1:] 
    nearest_neighbors = defaultdict(lambda: math.inf)
    
    while len(selected) < k and len(probes) > 0: #Selects probes one at a time, based on diversity, until k have been chosen.
        #Considers only probes which obey ASN constraint
        probes = [probe for probe in probes if asn_counts[probe['asn_v4']] < probes_per_asn] 
        select, nearest_neighbors = next_diverse_selection(probes, selected, nearest_neighbors) 
        selected.append(select)
        key = select['asn_v4'] if select['asn_v4'] is not None else "unknown"
        asn_counts[select['asn_v4']] += 1
        probes.remove(select) 
        
    return selected  

def next_diverse_selection(probes, selected, nearest_neighbors):
    """Selects the next probe to maximize geographic diversity from the already selected.
    This is done using the maximum of minimum distances. In other words, we choose the probe
    where even its closest neighbor is as distant as possible.
    """
    
    max_min_dist = -1 
    best_probe = None
    for probe in probes:
        probe_id = probe["id"]
        
        nearest_neighbors[probe_id] = min(nearest_neighbors[probe_id], great_circle_distance(probe, selected[-1]))
        
        if(nearest_neighbors[probe_id] > max_min_dist): 
            max_min_dist = nearest_neighbors[probe_id]
            best_probe = probe
    
    return best_probe, nearest_neighbors

def great_circle_distance(probe1, probe2):
    """Returns the spherical distance between two probes, using their latitude and longtidue values."""

    geo1, geo2 = [probe1['geometry']['coordinates'], probe2['geometry']['coordinates']]
    long1, lat1, long2, lat2 = map(math.radians, [geo1[0], geo1[1], geo2[0], geo2[1]]) #Converts degrees to radians
    
    # haversine formula 
    a = math.sin((lat2 - lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((long2 - long1)/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    
    km = 6371 * c #Multiply by radius of the earth
    return km

dual_stack_tags = "system-ipv4-works,system-ipv6-works,system-resolves-a-correctly,system-resolves-aaaa-correctly,"
version_tags = ["system-anchor","system-v4","system-v3"]
def get_probes_by_tag(and_tags = dual_stack_tags, or_tags = version_tags):
    """Returns a list of probes that have all of the 'and_tags', and at least one of the 'or_tags'. 
    By default, this is used to retrieve only probes that are IPv4 and IPv6 capable,
    and are one of the recent hardware versions (v3, v4 or anchor). 
    """
    print("Selecting probes from Ripe-Atlas...this may take a while.")
    probes = []
    for tag in or_tags:
        filters = {"tags" : and_tags + tag, "status" : "1"} 
        collection = ProbeRequest(**filters)
        for probe in collection:
            probes.append(probe)
    return probes

def get_probes_by_id(id_list):
    """Returns a list of probe data such as coordinates, given probe ids.
    This is necessary for using select_diverse_subset() with probe ids. 
    """
    print("Fetching probe data from Ripe-Atlas...this may take a while.")
    probe_list = []
    for probe_id in id_list:
        probe = Probe(id=probe_id)
        probe_list.append({"id" : probe_id, "asn_v4" : probe.asn_v4, "geometry" : probe.geometry})
    return probe_list

def print_probe_list(probe_list):
    """Prints the id, asn and coordinates for each probe in probe_list."""
    for probe in probe_list:
        print("id:", probe['id'], "\tasn:", probe['asn_v4'], "\tlongitude/latitude:", probe["geometry"]["coordinates"])