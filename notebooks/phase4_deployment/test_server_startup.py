import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def wait_for_server(timeout=60):
    print(f"Waiting for server at {BASE_URL}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("Server is UP!")
                print(f"Health Response: {response.json()}")
                return True
            else:
                print(f"Server is up but returned status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    print("Timed out waiting for server.")
    return False

def test_completion():
    print("\nTesting Completion...")
    payload = {
        "prompt": "import python",
        "max_tokens": 10,
        "temperature": 0
    }
    try:
        response = requests.post(f"{BASE_URL}/v1/completions", json=payload)
        if response.status_code == 200:
            print("Completion Successful!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Completion failed with status: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Completion error: {e}")
        return False

if __name__ == "__main__":
    if wait_for_server():
        if test_completion():
            print("\nVerification PASSED")
            sys.exit(0)
        else:
            print("\nVerification FAILED (Completion)")
            sys.exit(1)
    else:
        print("\nVerification FAILED (Startup)")
        sys.exit(1)
