import requests
import random
import time
from joblib import Parallel, delayed

# Azure server URL for the process_event endpoint
AZURE_URL = "https://fastapi-app.orangewater-9296a39e.eastus.azurecontainerapps.io/process_event/"

# Function to send a single HTTP POST request
def send_event_request():
    payload = {
        "userid": f"user_{random.randint(1, 100)}",
        "eventname": random.choice(["click", "purchase", "signup", "logout"])
    }
    response = requests.post(AZURE_URL, json=payload)
    return response.status_code

# Run parallel requests
def load_test():
    start_time = time.time()
    results = Parallel(n_jobs=10)(delayed(send_event_request)() for _ in range(1000))
    success_count = sum(1 for res in results if res == 200)
    print(f"Total successful requests: {success_count}/1000")
    print(f"Total execution time: {time.time() - start_time} seconds")

if __name__ == "__main__":
    load_test()
