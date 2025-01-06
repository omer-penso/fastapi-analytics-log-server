import pytest
from fastapi.testclient import TestClient
from main import app  
from datetime import datetime, timezone, timedelta
import sqlite3


@pytest.fixture
def test_db(monkeypatch):
    """Fixture to set up and tear down a test database."""
    # Setup: Create an SQLite database for testing
    monkeypatch.setattr("main.DATABASE_NAME", "test_db")
    conn = sqlite3.connect("test_db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS events")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eventtimestamputc TEXT NOT NULL,
            userid TEXT NOT NULL,
            eventname TEXT NOT NULL
        )
    """)
    conn.commit()

    # Provide the database connection to the test
    yield conn

    # Teardown: Close the connection
    conn.close()


@pytest.fixture
def client(test_db):
    """Fixture to provide a FastAPI TestClient."""
    return TestClient(app)


def test_process_event(client, test_db):
    """Test the /process_event/ endpoint."""

    payload = {"userid": "user123", "eventname": "level_completed"}

    response = client.post("/process_event/", json=payload)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["userid"] == "user123"
    assert response_data["data"]["eventname"] == "level_completed"

    # Verify the data was inserted into the database
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    assert len(events) == 1
    assert events[0][2] == "user123"  # userid
    assert events[0][3] == "level_completed"  # eventname


def test_invalid_payload(client):
    """Test /process_event/ with invalid payloads."""
    # Missing both fields
    response = client.post("/process_event/", json={})
    assert response.status_code == 422  

    # Missing one field
    response = client.post("/process_event/", json={"userid": "user123"})
    assert response.status_code == 422  

    # Invalid data type
    response = client.post("/process_event/", json={"userid": 123, "eventname": 456})
    assert response.status_code == 422  


def test_get_all_events(client, test_db):
    """Test the /events/ endpoint to retrieve all events."""
    # Insert test data into the database
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES ('2025-01-06T12:00:00Z', 'user123', 'level_completed')
    """)
    cursor.execute("""
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES ('2025-01-06T12:30:00Z', 'user456', 'purchase_completed')
    """)
    test_db.commit()

    response = client.get("/events/")
    assert response.status_code == 200
    events = response.json()["events"]

    # Verify the response
    assert len(events) == 2
    assert events[0][1] == "2025-01-06T12:00:00Z"  # eventtimestamputc
    assert events[0][2] == "user123"  # userid
    assert events[0][3] == "level_completed"  # eventname
    assert events[1][1] == "2025-01-06T12:30:00Z"  # eventtimestamputc
    assert events[1][2] == "user456"  # userid
    assert events[1][3] == "purchase_completed"

def test_get_reports(client, test_db):
    """
    Test the /get_reports/ endpoint to retrieve events for a user within the last X seconds.
    """
    # Insert sample data into the database
    cursor = test_db.cursor()
    current_time = datetime.now()

    # Add an event for `user123` within the range
    event_in_range = (current_time - timedelta(seconds=100)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES (?, ?, ?)
    """, (event_in_range, "user123", "test_event_in_range"))

    # Add an event for `user123` outside the range
    event_out_of_range = (current_time - timedelta(seconds=500)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES (?, ?, ?)
    """, (event_out_of_range, "user123", "test_event_out_of_range"))

    test_db.commit()

    # Make POST request to the /get_reports/ endpoint
    payload = {"lastseconds": 200, "userid": "user123"}
    response = client.post("/get_reports/", json=payload)

    # Verify the response
    assert response.status_code == 200
    response_data = response.json()  # Extract the JSON response
    events = response_data["events"]  # Access the "events" key
    assert len(events) == 1  # Only 1 event is within the range
    assert events[0][2] == "user123"  # userid
    assert events[0][3] == "test_event_in_range"  # eventname
