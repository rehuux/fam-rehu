from flask import Flask, request, jsonify
import requests
import threading
import time
import os
import logging
import json
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CREDITS
OWNER = "Syed Rehan"
DEVELOPER = "@istgrehu"
VERSION = "3.3"  # Updated version

# CONFIGURATION FROM YOUR CAPTURED DATA
OFFICIAL_API_HOST = "https://westeros.famapp.in"

# EXTRACTED FROM YOUR REQUEST - UPDATED
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
            
            # Configure session
            adapter = requests.adapters.HTTPAdapter(
                max_retries=3,
                pool_connections=10,
                pool_maxsize=10
            )
            SESSION.mount('https://', adapter)
            SESSION.mount('http://', adapter)
            
            logger.info(f"Session initialized successfully!")
            logger.info(f"Device ID: {DEVICE_ID}")
            logger.info(f"Token: {AUTH_TOKEN[:50]}...")
    
    return SESSION

def test_authentication() -> Tuple[bool, str]:
    """Test if authentication works using the new endpoint"""
    try:
        session = init_session()
        response = session.get(
            f"{OFFICIAL_API_HOST}/activity/v2/requests/all/?status=1",
            timeout=10
        )
        
        logger.info(f"Auth test status: {response.status_code}")
        logger.info(f"Auth test response: {response.text[:200]}")
        
        if response.status_code == 200:
            return True, "Authentication successful"
        elif response.status_code == 401:
            try:
                error_data = response.json()
                return False, f"Authentication failed: {error_data.get('message', 'Invalid token')}"
            except:
                return False, f"Authentication failed: HTTP {response.status_code}"
        else:
            return False, f"API error: HTTP {response.status_code}"
            
    except Exception as e:
        logger.error(f"Connection error in auth test: {e}")
        return False, f"Connection error: {str(e)}"

def fetch_blocked_list() -> Optional[Dict[str, Any]]:
    """Fetch blocked list from the new endpoint with error handling"""
    try:
        session = init_session()
        response = session.get(
            f"{OFFICIAL_API_HOST}/activity/v2/requests/all/?status=1",
            timeout=15
        )
        
        logger.info(f"Blocked list status: {response.status_code}")
        logger.info(f"Blocked list response preview: {response.text[:500]}")
        
        if response.status_code == 401:
            logger.error(f"Authentication error: {response.status_code}")
            return None
        elif response.status_code != 200:
            logger.error(f"Failed to fetch blocked list: {response.status_code}")
            logger.error(f"Response: {response.text[:200]}")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # DEBUG: Log the full response structure
        logger.info(f"Response type: {type(data)}")
        if isinstance(data, dict):
            logger.info(f"Response keys: {list(data.keys())}")
        
        # Handle different response structures
        if isinstance(data, list):
            logger.info(f"Fetched blocked list with {len(data)} users (list format)")
            return {"results": data}
        elif 'results' in data:
            users = data.get('results', [])
            logger.info(f"Fetched blocked list with {len(users)} users")
            if users and isinstance(users, list) and len(users) > 0:
                logger.info(f"First user structure: {list(users[0].keys()) if isinstance(users[0], dict) else 'Not dict'}")
            return data
        elif 'data' in data:
            users = data.get('data', [])
            logger.info(f"Fetched blocked list with {len(users)} users (data key)")
            return {"results": users}
        else:
            # Try to find any list in the response
            for key, value in data.items() if isinstance(data, dict) else []:
                if isinstance(value, list) and len(value) > 0:
                    logger.info(f"Found list in key '{key}' with {len(value)} items")
                    return {"results": value}
            
            logger.warning(f"Could not find user list in response. Full data: {json.dumps(data)[:500]}")
            return {"results": []}
        
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching blocked list")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching blocked list: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching blocked list: {e}")
        return None

def find_user_in_list(fam_id: str, blocked_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find user in blocked list - updated for new API structure"""
    if not blocked_data:
        return None

    fam_id_clean = fam_id.replace('@fam', '').strip().lower()
    
    # Get users list
    users = []
    if isinstance(blocked_data, dict):
        users = blocked_data.get('results', [])
        if not users and 'data' in blocked_data:
            users = blocked_data.get('data', [])
    elif isinstance(blocked_data, list):
        users = blocked_data
    else:
        logger.error(f"Unexpected blocked_data type: {type(blocked_data)}")
        return None
    
    logger.info(f"Searching {len(users)} users for {fam_id}")
    
    # Check cache first
    if fam_id in FAM_ID_MAPPING:
        cached_phone = FAM_ID_MAPPING[fam_id]
        for user in users:
            if user:
                # Extract contact info
                contact_info = user.get('contact') or user.get('user') or user.get('sender') or user.get('receiver') or user
                if isinstance(contact_info, dict):
                    phone = (contact_info.get('phone_number') or 
                            contact_info.get('phone') or 
                            contact_info.get('mobile') or
                            contact_info.get('mobile_number'))
                    if phone and phone == cached_phone:
                        logger.info(f"Found {fam_id} in cache")
                        return user
    
    # Search in list
    for user in users:
        if user:
            # Extract contact info from various possible fields
            contact_info = user.get('contact') or user.get('user') or user.get('sender') or user.get('receiver') or user
            
            if isinstance(contact_info, dict):
                name = str(contact_info.get('name', '')).lower().strip()
                phone = (contact_info.get('phone_number') or 
                        contact_info.get('phone') or 
                        contact_info.get('mobile') or
                        contact_info.get('mobile_number') or
                        '')
                vpa = str(contact_info.get('vpa', '')).lower().strip()
                fam_id_field = str(contact_info.get('fam_id', '')).lower().strip()
                username = str(contact_info.get('username', '')).lower().strip()
                
                logger.debug(f"Checking user: name={name}, vpa={vpa}, fam_id={fam_id_field}, username={username}")
                
                # Direct matches
                if (fam_id_clean in name or 
                    fam_id.lower() == vpa or 
                    fam_id_clean == fam_id_field or
                    fam_id_clean == username or
                    fam_id.lower() == str(contact_info.get('vpa', '')).lower()):
                    
                    if phone:
                        FAM_ID_MAPPING[fam_id] = phone
                    logger.info(f"Found {fam_id} by direct match")
                    logger.info(f"User details: {contact_info}")
                    return user
                
                # Also check if fam_id is in other fields
                for key, value in contact_info.items():
                    if isinstance(value, str) and fam_id_clean in value.lower():
                        if phone:
                            FAM_ID_MAPPING[fam_id] = phone
                        logger.info(f"Found {fam_id} in field '{key}': {value}")
                        return user

    logger.warning(f"User {fam_id} not found in blocked list")
    return None

def block_user(fam_id: str) -> Tuple[bool, str]:
    """Block a user and return success status"""
    try:
        session = init_session()
        block_payload = {"block": True, "vpa": fam_id}
        
        logger.info(f"Attempting to block {fam_id}")
        
        # Try multiple endpoints
        endpoints = [
            f"{OFFICIAL_API_HOST}/user/vpa/block/",
            f"{OFFICIAL_API_HOST}/activity/block/",
            f"{OFFICIAL_API_HOST}/block/",
            f"{OFFICIAL_API_HOST}/api/block/",
            f"{OFFICIAL_API_HOST}/v1/block/"
        ]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                response = session.post(
                    endpoint,
                    json=block_payload,
                    timeout=15
                )
                
                logger.info(f"Block response from {endpoint}: {response.status_code}")
                logger.info(f"Block response text: {response.text[:200]}")
                
                if response.status_code in [200, 201]:
                    try:
                        data = response.json()
                        logger.info(f"Block successful: {data}")
                        return True, f"Blocked via {endpoint}"
                    except:
                        return True, f"Blocked via {endpoint} (no JSON)"
                elif response.status_code == 400:
                    try:
                        error = response.json()
                        logger.warning(f"Bad request: {error}")
                        if "already blocked" in str(error).lower():
                            return True, "User already blocked"
                    except:
                        pass
                elif response.status_code == 404:
                    logger.warning(f"Endpoint not found: {endpoint}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error with endpoint {endpoint}: {e}")
                continue
        
        return False, "All block endpoints failed"
        
    except Exception as e:
        logger.error(f"Error blocking user {fam_id}: {e}")
        return False, str(e)

def instant_unblock(fam_id: str) -> None:
    """INSTANT unblock in background thread"""
    def unblock_task():
        try:
            time.sleep(1)  # Wait a bit before unblocking
            session = init_session()
            
            unblock_payload = {"block": False, "vpa": fam_id}
            logger.info(f"Attempting to unblock {fam_id}")
            
            endpoints = [
                f"{OFFICIAL_API_HOST}/user/vpa/block/",
                f"{OFFICIAL_API_HOST}/activity/block/",
                f"{OFFICIAL_API_HOST}/block/",
                f"{OFFICIAL_API_HOST}/api/block/",
                f"{OFFICIAL_API_HOST}/v1/block/"
            ]
            
            for endpoint in endpoints:
                try:
                    response = session.post(
                        endpoint,
                        json=unblock_payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"✓ Successfully unblocked: {fam_id} via {endpoint}")
                        if fam_id in FAM_ID_MAPPING:
                            del FAM_ID_MAPPING[fam_id]
                        break
                    elif response.status_code == 404:
                        continue
                except:
                    continue
            else:
                logger.error(f"✗ Failed to unblock {fam_id}: All endpoints failed")
                
        except Exception as e:
            logger.error(f"Error in unblock task for {fam_id}: {e}")
    
    thread = threading.Thread(target=unblock_task, daemon=True)
    thread.start()

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
    auth_status, auth_msg = test_authentication()
    
    return jsonify({
        "message": "Fam ID to Number API - DEBUG MODE",
        "status": "authenticated" if auth_status else "not_authenticated",
        "authentication_message": auth_msg,
        "credits": get_credits_info(),
        "endpoints": {
            "get_number": "GET /get-number?id=username@fam",
            "auth_test": "GET /auth-test",
            "device_info": "GET /device-info",
            "blocked_list": "GET /blocked",
            "credits": "GET /credits",
            "debug": "GET /debug-test"
        },
        "version": VERSION,
        "ready": True
    })

@app.route('/debug-test', methods=['GET'])
def debug_test():
    """Debug endpoint to test API directly"""
    try:
        session = init_session()
        
        # Test multiple endpoints
        endpoints = [
            "/activity/v2/requests/all/?status=1",
            "/user/blocked_list/",
            "/user/vpa/block/",
            "/activity/block/"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = session.get(f"{OFFICIAL_API_HOST}{endpoint}", timeout=10)
                results[endpoint] = {
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "preview": response.text[:500] if response.text else "No content"
                }
            except Exception as e:
                results[endpoint] = {"error": str(e)}
        
        return jsonify({
            "success": True,
            "debug_info": results,
            "device_id": DEVICE_ID,
            "token_preview": AUTH_TOKEN[:50] + "...",
            "credits": get_credits_info()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "credits": get_credits_info()
        }), 500

@app.route('/get-number', methods=['GET'])
def get_number():
    """MAIN ENDPOINT - Get phone number from Fam ID with auto-unblock"""
    fam_id = request.args.get('id', '').strip()
    debug_mode = request.args.get('debug', 'false').lower() == 'true'
    
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
    
    logger.info(f"Processing request for Fam ID: {fam_id}")
    
    # Step 1: Check authentication
    auth_success, auth_msg = test_authentication()
    if not auth_success:
        return jsonify({
            "error": "Authentication failed",
            "message": auth_msg,
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 401
    
    # Step 2: Check if already in blocked list
    blocked_data = fetch_blocked_list()
    
    if blocked_data is None:
        return jsonify({
            "error": "Failed to fetch blocked list",
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 500
    
    user = find_user_in_list(fam_id, blocked_data)
    
    if user:
        contact_info = user.get('contact') or user.get('user') or user.get('sender') or user.get('receiver') or user
        name = contact_info.get('name') if isinstance(contact_info, dict) else None
        phone = None
        
        if isinstance(contact_info, dict):
            phone = (contact_info.get('phone_number') or 
                    contact_info.get('phone') or 
                    contact_info.get('mobile') or
                    contact_info.get('mobile_number'))
        
        instant_unblock(fam_id)
        
        return jsonify({
            "status": True,
            "success": True,
            "fam_id": fam_id,
            "name": name,
            "phone": phone,
            "vpa": contact_info.get('vpa') if isinstance(contact_info, dict) else None,
            "type": user.get('type'),
            "source": "existing_block",
            "message": "User found in blocked list",
            "credits": get_credits_info(),
            "unblocked": True,
            "timestamp": datetime.now().isoformat(),
            "debug": debug_mode,
            "raw_user": user if debug_mode else None
        })
    
    # Step 3: Block to get info
    logger.info(f"User {fam_id} not found in blocked list. Attempting to block...")
    
    block_success, block_msg = block_user(fam_id)
    
    if not block_success:
        return jsonify({
            "status": False,
            "success": False,
            "error": "Block failed",
            "message": block_msg,
            "fam_id": fam_id,
            "credits": get_credits_info(),
            "timestamp": datetime.now().isoformat()
        }), 500
    
    # Step 4: Get updated list (wait longer)
    logger.info(f"Block successful. Waiting for API to update...")
    time.sleep(2)  # Increased wait time
    
    updated_data = fetch_blocked_list()
    
    if not updated_data:
        # Try again with different delay
        time.sleep(1)
        updated_data = fetch_blocked_list()
    
    if not updated_data:
        return jsonify({
            "error": "Failed to fetch updated blocked list after blocking",
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 500
    
    # Step 5: Find the newly blocked user
    user = find_user_in_list(fam_id, updated_data)
    
    if user:
        contact_info = user.get('contact') or user.get('user') or user.get('sender') or user.get('receiver') or user
        name = contact_info.get('name') if isinstance(contact_info, dict) else None
        phone = None
        
        if isinstance(contact_info, dict):
            phone = (contact_info.get('phone_number') or 
                    contact_info.get('phone') or 
                    contact_info.get('mobile') or
                    contact_info.get('mobile_number'))
        
        instant_unblock(fam_id)
        
        return jsonify({
            "status": True,
            "success": True,
            "fam_id": fam_id,
            "name": name,
            "phone": phone,
            "vpa": contact_info.get('vpa') if isinstance(contact_info, dict) else None,
            "type": user.get('type'),
            "source": "new_block",
            "message": "User blocked and info retrieved",
            "credits": get_credits_info(),
            "unblocked": True,
            "timestamp": datetime.now().isoformat(),
            "debug": debug_mode,
            "raw_user": user if debug_mode else None
        })
    
    # If still not found, check if the API returned any users at all
    users = []
    if isinstance(updated_data, dict):
        users = updated_data.get('results', updated_data.get('data', []))
    elif isinstance(updated_data, list):
        users = updated_data
    
    logger.warning(f"User {fam_id} not found after blocking. Total users in response: {len(users)}")
    
    if debug_mode and users:
        logger.info(f"First few users in response: {users[:3]}")
    
    return jsonify({
        "status": False,
        "success": False,
        "fam_id": fam_id,
        "error": "User not found after blocking",
        "message": "The Fam ID might be invalid, user doesn't exist, or API structure changed",
        "debug_info": {
            "block_success": block_success,
            "block_message": block_msg,
            "total_users_fetched": len(users),
            "api_used": "/activity/v2/requests/all/?status=1"
        } if debug_mode else None,
        "credits": get_credits_info(),
        "timestamp": datetime.now().isoformat()
    }), 404

# ... (keep all other routes the same as before: /credits, /device-info, /auth-test, /blocked, /cache, /health, etc.)

if __name__ == '__main__':
    global app_start_time
    app_start_time = time.time()
    
    print("=" * 70)
    print("FAM API SERVER - DEBUG VERSION 3.3")
    print("=" * 70)
    print(f"Owner: {OWNER}")
    print(f"Developer: {DEVELOPER}")
    print(f"Version: {VERSION}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"User Agent: {USER_AGENT}")
    print(f"Token: {AUTH_TOKEN[:50]}...")
    print(f"Token Length: {len(AUTH_TOKEN)} characters")
    print(f"API Endpoint: /activity/v2/requests/all/?status=1")
    print("\nTesting authentication...")
    
    auth_success, auth_msg = test_authentication()
    if auth_success:
        print(f"✅ Authentication SUCCESSFUL: {auth_msg}")
        print("\n✅ SERVER IS READY!")
        print("Use these endpoints:")
        print("1. Test: http://localhost:5000/auth-test")
        print("2. Get number: http://localhost:5000/get-number?id=username@fam")
        print("3. Debug mode: http://localhost:5000/get-number?id=username@fam&debug=true")
        print("4. Debug test: http://localhost:5000/debug-test")
        print("5. View blocked: http://localhost:5000/blocked")
        print("6. Credits: http://localhost:5000/credits")
    else:
        print(f"❌ Authentication FAILED: {auth_msg}")
        print("\n⚠️  Check your captured data. Token may be expired.")
    
    print("=" * 70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
