import requests
import re

# line types
rer = 'rers'
bus = 'bus'
tram = 'tramways'
metro = 'metros'
nocti = 'noctiliens'

# enum types
line_types = [rer, bus, tram, metro, nocti]
no_traffic_info = [nocti, bus]
mission_dirs = ["A", "R", "A+R"]

# URL
url = "https://api-ratp.pierre-grimaud.fr/v3"

stations = "stations"
missions = "mission"
lines = "lines"
schedules = "schedules"
traffic = "traffic"

"""
    Used to create URL basically add slash between each arg
"""


def create_url(*args):
    return '/'.join(args)


"""
    Process stop_name to match with RATP API requirements
"""


def stop_name_process(stop_name):
    s = stop_name.lower()
    # transform all non alpha_num char in +
    return re.sub('[^0-9a-zA-Z]+', '+', s)


"""
    Run http request of the given req and parse response into JSON    
"""


def http_request_to_json(req):
    # Get json from url request
    req_res = requests.get(req)
    return req_res.json()


"""
    Test if error occurs in the API's response
"""


def test_resp_error(js_resp):
    if 'code' in js_resp['result']:
        raise RuntimeError('API internal error')


"""
    Get next missions and return a new dict with information
"""


def get_schedule_info(js_resp, output_dict, my_station):
    test_resp_error(js_resp)
    assert (isinstance(my_station, My_station), "my_station must be a My_station instance")

    line_key = my_station.line_type + '+' + my_station.line_name

    # Create line if not exist in the output dict
    if not line_key in output_dict['my_lines']:
        output_dict['my_lines'][line_key] = dict(traffic_title="", traffic_msg="")

    if not my_station.line_name in output_dict['my_lines'][line_key]:
        output_dict['my_lines'][line_key][my_station.stop_name] = dict(next_missions=[])

    for schedule in js_resp['result']['schedules']:
        # Check if rer go to dest_stop_name
        if my_station.line_type == rer and my_station.dest_stop_name is not "":
            # get schedule for next missions
            req = create_url(url,
                             missions,
                             my_station.line_type,
                             my_station.line_name.upper(),
                             schedule['code'])

            mission_res = http_request_to_json(req)

            # looks for the dest_stop_name in the mission stops
            found = False
            for v in mission_res['result']['stations']:
                if found:
                    break
                for k1, v1 in v.items():
                    if stop_name_process(v1) == my_station.dest_stop_name:
                        found = True
                        # If destination found in the mission add it
                        output_dict['my_lines'][line_key][my_station.stop_name]["next_missions"] \
                            .append({'message': schedule['message'], 'destination': schedule['destination']})
                        break

        # add to my_info different process for rers
        else:
            output_dict['my_lines'][line_key][my_station.stop_name]["next_missions"]\
                .append({'message': schedule['message'], 'destination': schedule['destination']})

    # Get traffic info not bus or noctilien
    if my_station.line_type not in no_traffic_info:
        req = create_url(url,
                         traffic,
                         my_station.line_type,
                         my_station.line_name.upper())

        traffic_res = http_request_to_json(req)

        output_dict['my_lines'][line_key]['traffic_title'] = traffic_res['result']['title']
        output_dict['my_lines'][line_key]['traffic_msg'] = traffic_res['result']['message']

    # TODO: Handle other types and multiple lines
    return output_dict


"""
    Run test on arguments and get next missions given the parameters
"""


def search_for_transport(my_stations, output_dict):
    assert (isinstance(my_stations, list) or isinstance(my_stations, My_station),
            "my_station must be a My_station instance or list of My_station")

    my_stations = [my_stations] if isinstance(my_stations, My_station) else my_stations

    for my_station in my_stations:
        assert (isinstance(my_station, My_station), "my_station must be a My_station")

        # get schedule for next missions
        req = create_url(url, schedules,
                         my_station.line_type,
                         my_station.line_name.lower(),
                         my_station.stop_name,
                         my_station.mission_dir)

        js_resp = http_request_to_json(req)

        output_dict = get_schedule_info(js_resp=js_resp,
                                        output_dict=output_dict,
                                        my_station=my_station)
    return output_dict


class My_station(object):
    def __init__(self, line_type, line_name, stop_name, mission_dir, dest_stop_name):
        if line_type not in line_types:
            raise RuntimeError("line_type unknown")

        if mission_dir not in mission_dirs:
            raise RuntimeError("mission_dir unknown")

        self.line_type = line_type
        self.line_name = line_name
        self.stop_name = stop_name_process(stop_name)
        self.mission_dir = mission_dir
        self.dest_stop_name = stop_name_process(dest_stop_name)


def main():
    my_station_tram = My_station(line_name="3a",
                                 line_type=tram,
                                 stop_name="cite universitaire",
                                 mission_dir="R",
                                 dest_stop_name="")

    my_station_bus = My_station(line_name="399",
                                line_type=bus,
                                stop_name="mairie massy",
                                mission_dir="R",
                                dest_stop_name="")

    my_station_rer = My_station(line_name="b",
                                line_type=rer,
                                stop_name="massy palaiseau",
                                mission_dir="A",
                                dest_stop_name="chatelet")

    my_station_rer2 = My_station(line_name="b",
                                 line_type=rer,
                                 stop_name="chatelet",
                                 mission_dir="R",
                                 dest_stop_name="massy palaiseau")

    # TODO: Set a dict to handle multiple paths

    # Output structure
    my_info = {"my_lines": {}}

    res = search_for_transport(my_station_rer2, output_dict=my_info)

    my_info = {"my_lines": {}}
    res = search_for_transport([my_station_rer, my_station_bus, my_station_tram, my_station_rer2], output_dict=my_info)

    print('end')


if __name__ == "__main__":
    main()
