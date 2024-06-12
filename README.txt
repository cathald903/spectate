1. Find internal nodes

The code is located inside internal_nodes.py and should be ran via
python3 internal_nodes.py


2.
To bring up the flask app run the below
    docker compose up --build -d db &&  docker compose up --build flask

To run the unit tests
     docker compose up --build -d db &&  docker compose up --build tests


Queries and assumptions
    Create, update and delete queries:
