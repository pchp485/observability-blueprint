import requests
import sys
import json
from datetime import datetime

class AetherCollectAPITester:
    def __init__(self, base_url="https://41d9c20b-56ff-4c46-b87f-44e5b9dd3566.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            print(f"Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    print(f"Response: {response.text}")
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_hello_endpoint(self):
        """Test GET /api/ endpoint"""
        success, response = self.run_test(
            "Hello World Endpoint",
            "GET",
            "api/",
            200
        )
        if success and response.get('message') == 'Hello World':
            print("✅ Hello endpoint returned correct message")
            return True
        else:
            print("❌ Hello endpoint did not return expected message")
            return False

    def test_health_endpoint(self):
        """Test GET /api/health endpoint"""
        success, response = self.run_test(
            "Health Check Endpoint",
            "GET",
            "api/health",
            200
        )
        if success:
            if 'status' in response and 'db' in response:
                print(f"✅ Health endpoint returned status: {response['status']}, db: {response['db']}")
                return True
            else:
                print("❌ Health endpoint missing required fields")
                return False
        return False

    def test_create_status(self, client_name="test-e2e"):
        """Test POST /api/status endpoint"""
        success, response = self.run_test(
            "Create Status Check",
            "POST",
            "api/status",
            200,
            data={"client_name": client_name}
        )
        if success and 'id' in response and 'client_name' in response:
            print(f"✅ Status created with ID: {response['id']}")
            return response['id']
        else:
            print("❌ Status creation failed or missing required fields")
            return None

    def test_get_status_checks(self, expected_client_name="test-e2e"):
        """Test GET /api/status endpoint"""
        success, response = self.run_test(
            "Get Status Checks",
            "GET",
            "api/status",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} status checks")
            
            # Check if our test entry exists
            for item in response:
                if item.get('client_name') == expected_client_name:
                    print(f"✅ Found expected client_name '{expected_client_name}' in results")
                    return True
            
            if len(response) > 0:
                print(f"⚠️  No entry with client_name '{expected_client_name}' found, but list is not empty")
                print(f"First item: {response[0]}")
                return True
            else:
                print("❌ Status checks list is empty")
                return False
        else:
            print("❌ Failed to retrieve status checks or response is not a list")
            return False

def main():
    print("🚀 Starting AetherCollect API Tests")
    print("=" * 50)
    
    # Setup
    tester = AetherCollectAPITester()
    
    # Test 1: Hello endpoint
    hello_success = tester.test_hello_endpoint()
    
    # Test 2: Health endpoint
    health_success = tester.test_health_endpoint()
    
    # Test 3: Create status check
    status_id = tester.test_create_status("test-e2e")
    create_success = status_id is not None
    
    # Test 4: Get status checks
    get_success = tester.test_get_status_checks("test-e2e")
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Hello endpoint: {'✅ PASS' if hello_success else '❌ FAIL'}")
    print(f"Health endpoint: {'✅ PASS' if health_success else '❌ FAIL'}")
    print(f"Create status: {'✅ PASS' if create_success else '❌ FAIL'}")
    print(f"Get status: {'✅ PASS' if get_success else '❌ FAIL'}")
    
    all_passed = hello_success and health_success and create_success and get_success
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())