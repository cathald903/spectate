"""
Test file
"""
import datetime
import json
import pytest
from app import create_app
from app.tables import clear_tables, declare_tables
from app.helpers import select_query


def get_json(values: list, kind: str):
    """
    make a sport json dict
    """
    if 'Sport' == kind:
        cols = ['Name', 'Active', 'kind', 'object']
        values.append('Sport')
    elif 'Event' == kind:
        cols = ['Name', 'Active', 'Type', 'Sport',
                'Status', 'Scheduled start', 'kind', 'object']
        values.append('Event')
    elif 'Selection' == kind:
        cols = ['Name', 'Event', 'Price',
                'Active', 'Outcome', 'kind', 'object']
        values.append('Selection')
    return dict(zip(cols, values))


@pytest.fixture
def client():
    """
    Test client creation
    """
    app = create_app()
    clear_tables()
    declare_tables()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_home_page(client):
    """
    Tables in the homepage?
    """
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Sports:' in rv.data
    assert b'Events:' in rv.data
    assert b'Selections:' in rv.data


def generic_modify_object_test(client, tab, name, json_data):
    """
    send off the dict to the endpoint and select * from the given table
    """
    rv = client.post('/modify_object', json=json_data)
    assert rv.status_code == 200
    res = select_query(f"Select * from {tab} where name = '{name}'")
    return res


def test_modify_object_sport(client):
    """
    Testing the outcomes of creating,updating and deleting a Sport
    """
    # Can we create a Sport?
    test_sport = 'test_football'
    res = generic_modify_object_test(client, 'Sport', test_sport,
                                     get_json([test_sport, False, 'create'], 'Sport'))[0]
    assert test_sport in res

    # Can we update the Sport?
    res = generic_modify_object_test(client, 'Sport', test_sport,
                                     get_json([test_sport, True, 'update'], 'Sport'))[0]
    assert test_sport in res[0]

    # Can we delete the Sport?
    res = generic_modify_object_test(client, 'Sport', test_sport,
                                     get_json([test_sport, True, 'delete'], 'Sport'))
    assert res == []


def test_modify_object_event(client):
    """
    Testing the outcomes of creating,updating and deleting an Event
    """
    test_event = 'test_football_match'
    test_sport = 'test_football'
    # Can't create an event if sport doesn't exist?
    json_data = get_json(
        [test_event, False, 'preplay', test_sport, 'Pending', '2024-06-11T12:34:56Z', 'create'], 'Event')

    with pytest.raises(RuntimeError):
        err = generic_modify_object_test(
            client, 'Event', test_event, json_data)[0]

    # create a sport for Event to test with
    generic_modify_object_test(
        client, 'Sport', test_sport, get_json([test_sport, True, 'create'], 'Sport'))[0]
    # Can create Event? Does Inactive Event set Sport to inactive also?
    res = generic_modify_object_test(
        client, 'Event', test_event, json_data)[0]
    sport = select_query(
        f"Select Active from Sport where Name = '{test_sport}'")[0]
    assert test_event in res
    assert not sport[0]  # not active

    # Can update Event? Does changing status to Started populate Actual_start?
    json_data = get_json(
        [test_event, True, 'preplay', test_sport, 'Started', '2024-06-11T12:34:56Z', 'update'], 'Event')
    res = generic_modify_object_test(
        client, 'Event', test_event, json_data)[0]
    assert test_event in res
    assert isinstance(res[-1], datetime.datetime)

    # Can we delete the Event?
    json_data = get_json(
        [test_event, True, 'preplay', test_sport, 'Started', '2024-06-11T12:34:56Z', 'delete'], 'Event')
    res = generic_modify_object_test(
        client, 'Event', test_event, json_data)

    assert res == []


def test_modify_object_Selection(client):
    """
    Testing the outcomes of creating,updating and deleting a Selection
    """
    test_selection = 'test_selection'
    test_event = 'test_football_match'
    test_sport = 'test_football'
    # Can't create a Selection if Event doesn't exist?
    json_data = get_json(
        [test_selection, test_event, 1.02345, False, 'Unsettled', 'create'], 'Selection')

    with pytest.raises(RuntimeError):
        err = generic_modify_object_test(
            client, 'Selection', test_selection, json_data)[0]

    # create a sport and Event to test with
    generic_modify_object_test(
        client, 'Sport', test_sport, get_json([test_sport, True, 'create'], 'Sport'))[0]
    event_json_data = get_json(
        [test_event, True, 'preplay', test_sport, 'Pending', '2024-06-11T12:34:56Z', 'create'], 'Event')
    generic_modify_object_test(
        client, 'Event', test_event, event_json_data)[0]

    # Can create Selection? Does Inactive Selection set Event to inactive also? Does that cause Sport to also go inactive?
    res = generic_modify_object_test(
        client, 'Selection', test_selection, json_data)[0]
    eve = select_query(
        f"Select Active from Event where Name = '{test_event}'")[0]
    spor = select_query(
        f"Select Active from Sport where Name = '{test_sport}'")[0]
    assert test_event in res
    assert 4 == len(str(res[2]))  # 2 decimal places
    assert not eve[0]  # Event not active
    assert not spor[0]  # Sport not active

    # Can update Selection?
    json_data = get_json(
        [test_selection, test_event, 1.02345, True, 'Unsettled', 'update'], 'Selection')
    res = generic_modify_object_test(
        client, 'Selection', test_selection, json_data)[0]
    assert test_event in res

    # Can we delete the Selection?
    json_data = get_json(
        [test_selection, test_event, 1.02345, True, 'Unsettled', 'delete'], 'Selection')
    res = generic_modify_object_test(
        client, 'Selection', test_selection, json_data)
    assert res == []


def create_test_data(client):
    test_sport = 'sport_'
    for i in range(5):
        generic_modify_object_test(
            client, 'Sport', test_sport+str(i), get_json([test_sport+str(i), True, 'create'], 'Sport'))
    test_event = "event_"
    dates = ["0"+str(i) if len(str(i)) == 1 else str(i) for i in range(1, 16)]
    for i in range(15):
        event_json_data = get_json(
            [test_event+str(i), [True, False][i % 2], 'preplay', test_sport+str(i % 5), 'Pending', f"2024-06-{dates[i]}T12:34:56Z", 'create'], 'Event')
        generic_modify_object_test(
            client, 'Event', test_event+str(i), event_json_data)
    test_selection = "selection_"
    prices = ["1.0"+str(i) if len(str(i)) == 1 else "1."+str(i)
              for i in range(1, 31)]
    for i in range(30):
        selection_json_data = get_json(
            [test_selection+str(i), test_event+str(i % 15), float(prices[i]), [True, False][i % 2], "Unsettled", 'create'], 'Selection')
        generic_modify_object_test(
            client, 'Selection', test_selection+str(i), selection_json_data)


def test_filter_object_by_active(client):
    """
    will test if filters are operating as expected
    """
    create_test_data(client)
    filt = {
        "table": "Sport",
        "select_columns": "*",
        "filters": [
            {
                "filler_col": "Active",
                "operation": "equal",
                "val": True
            }
        ]
    }
    rv = client.post('/filter_object', json=filt)
    # res = (rv.data).decode('utf-8')
    res = json.loads(rv.data)
    assert 3 == len(res)


def test_filter_object_by_Name(client):
    create_test_data(client)
    filt = {
        "table": "Selection",
        "select_columns": "*",
        "filters": [
            {
                "filler_col": "Name",
                "operation": "equal",
                "val": "selection_0"
            }
        ]
    }
    rv = client.post('/filter_object', json=filt)
    res = json.loads(rv.data)
    assert "selection_0" in res[0]


def test_filter_object_by_tz(client):
    create_test_data(client)
    filt = {
        "table": "Event",
        "select_columns": "*",
        "filters": [
            {
                "filler_col": "Scheduled_start",
                "operation": "gequal",
                "val": {
                    "date": "2024-06-08T11:34:56Z",
                    "timezone": "America/New_York"
                }
            },
            {
                "filler_col": "Scheduled_start",
                "operation": "lequal",
                "val": {
                    "date": "2024-08-08T11:34:56Z",
                    "timezone": "America/New_York"
                }
            }
        ]
    }
    rv = client.post('/filter_object', json=filt)
    res = json.loads(rv.data)
    assert len(res) == 8


def test_complex_filter_count(client):
    create_test_data(client)
    filt = {
        "table": [
            "Sport",
            "Event"
        ],
        "select_columns": [
            "Name",
            ""
        ],
        "filters": [
            [],
            [{
                "filler_col": "Active",
                "operation": "equal",
                "val": True
            }]
        ],
        "aggregate": [
            [{
                "agg_col": "Active",
                "agg_operation": "count",
                "operation": "gequal",
                "val": 1
            }],
            [{
            }]
        ]
    }
    rv = client.post('/filter_object', json=filt)
    res = json.loads(rv.data)[0]
    assert "sport_0" in res
    assert 2 == res[1]


def test_complex_filter_min(client):
    create_test_data(client)
    filt = {
        "table": [
            "Sport",
            "Selection"
        ],
        "select_columns": [
            "Name",
            "Name"
        ],
        "filters": [
            [],
            [{
                "filler_col": "Active",
                "operation": "equal",
                "val": True
            },
            ]
        ],
        "aggregate": [
            [],
            [{
                "agg_col": "Price",
                "agg_operation": "min",
                "operation": "lequal",
                "val": 1.01
            }]
        ]
    }
    rv = client.post('/filter_object', json=filt)
    res = json.loads(rv.data)
    assert len(res) == 1
    assert "sport_0" in res[0]
    assert "selection_0" in res[0]
    clear_tables()
