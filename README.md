# Find internal nodes

The code for this function is located inside internal_nodes.py and should be ran via \
`python3 internal_nodes.py`

# Flask API
## Starting the processes
To run the unit tests \
`docker compose up --build -d db &&  docker compose up --build tests`

To bring up the flask app run the below \
`docker compose up --build -d db &&  docker compose up --build flask`

Running the unit tests first will leave the test data in the db when the flask app is brought up afterwards. \
To run the tests and bring up a fresh flask app uncomment the `clear_tables()` function call at the end of \
the `test_routes.py` file


## Making and Modifying the Sports,Events and Selections
Create, update and delete queries all share a common data structure depending on method type eg `create`,`update` or `delete`. Place desired method in the "kind" field 

Assumed all data is being attached as a json dict to the requests and that all data can be retrieved via \
 `request_dict = json.loads(request.data)`

All Create, update and delete queries go to \
`http://localhost:8000/modify_object`
### Sport
#### Assumptions
Slug is not passed in because it is just the url friendly version of Name so can be derived upon create. It won't change during update because \
Name is the primary key and can't change
```
{
  "Name": "Football",
  "Active":true,
  "kind": "create",
  "object": "Sport"
}
``` 

### Event
#### Assumptions
Scheduled start is passed in with a space between the names as that is what the doc defined, so the Flask app has to handle that
```
{
  "Name": "Football Match",
  "Active":true,
  "Type":"preplay",
  "Sport": "Football",
  "Status":"Pending",
  "Scheduled start": "2024-06-01T12:34:56Z",
  "kind": "create",
  "object": "Event"
}
``` 

### Selection
Price can be given as any float but the flask app must round it to two decimal places
```
{
  "Name": "Football Match Selection",
  "Event": "Football Match",
  "Price":1.023,
  "Active":true,
  "Outcome":"Unsettled",
  "kind": "create",
  "object": "Selection"
}
```

## Filters
*NOTE: thunder-collection_Selection.json contains ready to go sample api calls*
### Simple vs Complex
A loose definition of what I implemented, simple is any filter that doesn't require a join or an aggregate.
NOTE: Examples below use the data left in the db after running the tests
#### Filter
A filter looks like this 
```
{
  "table": "Sport",
  "select_columns": "*",
  "filters": [
    {
      "filler_col": "Active",
      "operation": "equal",
      "val": true
    }
  ]
}
```
multiple filters for a given table can be attached by adding another dict to the filters list

```
{
  "table": "Sport",
  "select_columns": "*",
  "filters": [
    {
      "filler_col": "Active",
      "operation": "equal",
      "val": true
    },
    {
      "filler_col": "Name",
      "operation": "equal",
      "val": "sport_0"
    }
  ]
}

```
#### More Complex Examples
By turning the columns into lists of lists we can now make them complex. \
The order of the table names in the `table` field is the order their accompanying `select_columns`,`filters` and `aggreagate` fields must be in. \
*With hindsight having the columns be dictionaries containing the fields is probably a better idea*

#### Filter to get all the Sports that have 2 or more active Events
```
{
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
    [
      {
        "filler_col": "Active",
        "operation": "equal",
        "val": true
      }
    ]
  ],
  "aggregate": [
    [
      {
        "agg_col": "Active",
        "agg_operation": "count",
        "operation": "gequal",
        "val": 2
      }
    ],
    [
      {}
    ]
  ]
}
```

#### filter to get the Sports that have an active selection with price less than or equal to a given number
*NOTE: was seeing some rounding issues here, things like equal as the operator not reutrning 1.01 but <= would*
```
{
  "table": [
    "Sport",
    "Selection"
  ],
  "select_columns": [
    "Name",
    "*"
  ],
  "filters": [
    [],
    [
      {
        "filler_col": "Active",
        "operation": "equal",
        "val": true
      }
    ]
  ],
  "aggregate": [
    [],
    [
      {
        "agg_col": "Price",
        "agg_operation": "min",
        "operation": "lequal",
        "val": 1.01
      }
    ]
  ]
}
```