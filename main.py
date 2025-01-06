from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import sqlite3


DATABASE_NAME = "analytics.db"
create_table = """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eventtimestamputc TEXT NOT NULL,
            userid TEXT NOT NULL,
            eventname TEXT NOT NULL
        )
      """

#  Define a lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI.
    This runs on application startup and shutdown.
    """
    # Startup: Initialize the database
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute(create_table)
        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        raise RuntimeError(f"Failed to initialize database: {e}")

    yield

    # Shutdown: Perform cleanup if necessary
    print("Shutting down: No cleanup needed in this case.")


# Create FastAPI app with the lifespan handler
app = FastAPI(lifespan=lifespan)

class Event(BaseModel):
   userid: str
   eventname: str


@app.post("/process_event/")
async def  process_event (event: Event):
   """
   Process an event and store it in the database.
   """
   event_timestamp_utc = datetime.now(timezone.utc).isoformat()

   try:
      with sqlite3.connect(DATABASE_NAME) as conn:
         cursor = conn.cursor()
         cursor.execute("INSERT INTO events (eventtimestamputc, userid, eventname) VALUES (?, ?, ?)", (event_timestamp_utc, event.userid, event.eventname))
         conn.commit()

   except sqlite3.OperationalError as e:
      raise HTTPException(status_code=500, detail=f"Database error: {e}")

   return {
            "status": "success",
            "message": "Event added successfully",
            "data": {
                "eventtimestamputc": event_timestamp_utc,
                "userid": event.userid,
                "eventname": event.eventname,
            },
        }


@app.get("/events/")
async def get_all_events():
    """
    Retrieve all events stored in the database.
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            events = cursor.fetchall()
        return {"events": events}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
  
   