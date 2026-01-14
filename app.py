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
VERSION = "3.2"

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
        return False, f"Connection error: {str(e)}"

def fetch_blocked_list() -> Optional[Dict[str, Any]]:
    """Fetch blocked list from the new endpoint with error handling"""
    try:
        session = init_session()
        response = session.get(
            f"{OFFICIAL_API_HOST}/activity/v2/requests/all/?status=1",
            timeout=15
        )
        
        if response.status_code == 401:
            logger.error(f"Authentication error: {response.status_code}")
            return None
        elif response.status_code != 200:
            logger.error(f"Failed to fetch blocked list: {response.status_code}")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # Handle different response structures
        if isinstance(data, list):
            logger.info(f"Fetched blocked list with {len(data)} users (list format)")
            return {"results": data}
        elif 'results' in data:
            logger.info(f"Fetched blocked list with {len(data.get('results', []))} users")
            return data
        else:
            # Try to find the actual data structure
            logger.info(f"Fetched blocked list with custom structure: {list(data.keys())}")
            return data
        
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
    
    # Check cache first
    if fam_id in FAM_ID_MAPPING:
        cached_phone = FAM_ID_MAPPING[fam_id]
        users = blocked_data.get('results', []) if isinstance(blocked_data, dict) else blocked_data
        
        for user in users:
            if user:
                contact_info = user.get('contact') or user.get('user') or user
                if isinstance(contact_info, dict):
                    phone = contact_info.get('phone_number') or contact_info.get('phone') or contact_info.get('mobile')
                    if phone == cached_phone:
                        logger.info(f"Found {fam_id} in cache")
                        return user
    
    # Search in list
    users = blocked_data.get('results', []) if isinstance(blocked_data, dict) else blocked_data
    
    for user in users:
        if user:
            contact_info = user.get('contact') or user.get('user') or user
            
            if isinstance(contact_info, dict):
                name = contact_info.get('name', '').lower().strip()
                phone = contact_info.get('phone_number') or contact_info.get('phone') or contact_info.get('mobile')
                vpa = contact_info.get('vpa', '')
                fam_id_field = contact_info.get('fam_id', '')
                username = contact_info.get('username', '')
                
                # Direct matches
                if (fam_id_clean in name or 
                    fam_id == vpa or 
                    fam_id_clean == fam_id_field or
                    fam_id_clean == username):
                    if phone:
                        FAM_ID_MAPPING[fam_id] = phone
                    logger.info(f"Found {fam_id} by direct match")
                    return user
                
                # Handle variations
                if 'send' in fam_id_clean:
                    name_part = fam_id_clean.replace('send', '').replace('2', '').replace('3', '').strip()
                    if name_part and name_part in name:
                        if phone:
                            FAM_ID_MAPPING[fam_id] = phone
                        logger.info(f"Found {fam_id} by partial match")
                        return user

    logger.warning(f"User {fam_id} not found in blocked list")
    return None

def instant_unblock(fam_id: str) -> None:
    """INSTANT unblock in background thread"""
    def unblock_task():
        try:
            time.sleep(0.5)
            session = init_session()
            
            unblock_payload = {"block": False, "vpa": fam_id}
            logger.info(f"Attempting to unblock {fam_id}")
            
            endpoints = [
                f"{OFFICIAL_API_HOST}/user/vpa/block/",
                f"{OFFICIAL_API_HOST}/activity/block/",
                f"{OFFICIAL_API_HOST}/block/"
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

@app.route('/')
def home():
    """Home page"""
    auth_status, auth_msg = test_authentication()
    
    return jsonify({
        "message": "Fam ID to Number API - READY TO USE",
        "status": "authenticated" if auth_status else "not_authenticated",
        "authentication_message": auth_msg,
        "credits": get_credits_info(),
        "endpoints": {
            "get_number": "GET /get-number?id=username@fam",
            "auth_test": "GET /auth-test",
            "device_info": "GET /device-info",
            "blocked_list": "GET /blocked",
            "credits": "GET /credits"
        },
        "version": VERSION,
        "ready": True
    })

@app.route('/credits', methods=['GET'])
def credits():
    """Get credits information"""
    return jsonify({
        "success": True,
        "credits": get_credits_info(),
        "message": "Thanks for using our API!",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/device-info', methods=['GET'])
def device_info():
    """Get current device information"""
    auth_status, auth_msg = test_authentication()
    
    return jsonify({
        "device_id": DEVICE_ID,
        "user_agent": USER_AGENT,
        "authentication_status": auth_status,
        "authentication_message": auth_msg,
        "token_available": True,
        "token_preview": f"{AUTH_TOKEN[:50]}...",
        "host": OFFICIAL_API_HOST,
        "credits": get_credits_info()
    })

@app.route('/auth-test', methods=['GET'])
def auth_test():
    """Test authentication"""
    auth_success, auth_msg = test_authentication()
    
    return jsonify({
        "authenticated": auth_success,
        "message": auth_msg,
        "device_id": DEVICE_ID,
        "user_agent": USER_AGENT,
        "token_length": len(AUTH_TOKEN),
        "credits": get_credits_info()
    })

@app.route('/get-number', methods=['GET'])
def get_number():
    """MAIN ENDPOINT - Get phone number from Fam ID with auto-unblock"""
    fam_id = request.args.get('id', '').strip()
    
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
        contact_info = user.get('contact') or user.get('user') or user
        name = contact_info.get('name') if isinstance(contact_info, dict) else None
        phone = None
        
        if isinstance(contact_info, dict):
            phone = contact_info.get('phone_number') or contact_info.get('phone') or contact_info.get('mobile')
        
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
            "timestamp": datetime.now().isoformat()
        })
    
    # Step 3: Block to get info
    block_payload = {"block": True, "vpa": fam_id}
    
    try:
        session = init_session()
        
        logger.info(f"Blocking {fam_id} to get info")
        
        block_endpoints = [
            f"{OFFICIAL_API_HOST}/user/vpa/block/",
            f"{OFFICIAL_API_HOST}/activity/block/",
            f"{OFFICIAL_API_HOST}/block/"
        ]
        
        block_success = False
        for endpoint in block_endpoints:
            try:
                block_response = session.post(
                    endpoint,
                    json=block_payload,
                    timeout=15
                )
                
                if block_response.status_code in [200, 201]:
                    logger.info(f"✓ Block successful via {endpoint}")
                    block_success = True
                    break
                elif block_response.status_code == 401:
                    return jsonify({
                        "error": "Authentication failed during block",
                        "message": "Token may be invalid or expired",
                        "fam_id": fam_id,
                        "credits": get_credits_info()
                    }), 401
                elif block_response.status_code == 404:
                    continue
            except:
                continue
        
        if not block_success:
            return jsonify({
                "error": "Block failed on all endpoints",
                "fam_id": fam_id,
                "credits": get_credits_info()
            }), 500
        
        # Step 4: Get updated list
        time.sleep(1.5)
        updated_data = fetch_blocked_list()
        
        if not updated_data:
            return jsonify({
                "error": "Failed to fetch updated blocked list",
                "fam_id": fam_id,
                "credits": get_credits_info()
            }), 500
        
        # Step 5: Find the newly blocked user
        users = updated_data.get('results', []) if isinstance(updated_data, dict) else updated_data
        
        if users:
            newest_user = users[0]
            
            contact_info = newest_user.get('contact') or newest_user.get('user') or newest_user
            name = contact_info.get('name') if isinstance(contact_info, dict) else None
            phone = None
            
            if isinstance(contact_info, dict):
                phone = contact_info.get('phone_number') or contact_info.get('phone') or contact_info.get('mobile')
            
            instant_unblock(fam_id)
            
            return jsonify({
                "status": True,
                "success": True,
                "fam_id": fam_id,
                "name": name,
                "phone": phone,
                "vpa": contact_info.get('vpa') if isinstance(contact_info, dict) else None,
                "type": newest_user.get('type'),
                "source": "new_block",
                "message": "User blocked and info retrieved",
                "credits": get_credits_info(),
                "unblocked": True,
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify({
            "status": False,
            "success": False,
            "fam_id": fam_id,
            "error": "User not found after blocking",
            "message": "The Fam ID might be invalid or user doesn't exist",
            "credits": get_credits_info(),
            "timestamp": datetime.now().isoformat()
        }), 404
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout processing {fam_id}")
        return jsonify({
            "error": "Request timeout",
            "message": "Please try again",
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error for {fam_id}: {e}")
        return jsonify({
            "error": "Network error",
            "message": str(e),
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 503
    except Exception as e:
        logger.error(f"Unexpected error for {fam_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "fam_id": fam_id,
            "credits": get_credits_info()
        }), 500

@app.route('/blocked', methods=['GET'])
def blocked_list():
    """View blocked list"""
    try:
        data = fetch_blocked_list()
        
        if data is None:
            return jsonify({
                "error": "Failed to fetch blocked list",
                "message": "Authentication or connection issue",
                "credits": get_credits_info()
            }), 500
        
        users = []
        user_list = data.get('results', []) if isinstance(data, dict) else data
        
        for user in user_list:
            if user:
                contact_info = user.get('contact') or user.get('user') or user
                if isinstance(contact_info, dict):
                    users.append({
                        "name": contact_info.get('name'),
                        "phone": contact_info.get('phone_number') or contact_info.get('phone') or contact_info.get('mobile'),
                        "vpa": contact_info.get('vpa'),
                        "type": user.get('type')
                    })
        
        return jsonify({
            "success": True,
            "count": len(users),
            "users": users,
            "cache_size": len(FAM_ID_MAPPING),
            "api_structure": "activity/v2/requests/all/?status=1",
            "credits": get_credits_info(),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in blocked_list endpoint: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "credits": get_credits_info()
        }), 500

@app.route('/cache', methods=['GET'])
def get_cache():
    """View cache contents"""
    return jsonify({
        "cache_size": len(FAM_ID_MAPPING),
        "mapping": FAM_ID_MAPPING,
        "credits": get_credits_info(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache"""
    global FAM_ID_MAPPING
    size = len(FAM_ID_MAPPING)
    FAM_ID_MAPPING = {}
    logger.info("Cache cleared")
    return jsonify({
        "success": True,
        "message": f"Cache cleared ({size} entries removed)",
        "cache_size": 0,
        "credits": get_credits_info(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        auth_success, auth_msg = test_authentication()
        
        return jsonify({
            "status": "healthy" if auth_success else "degraded",
            "timestamp": datetime.now().isoformat(),
            "authentication": {
                "success": auth_success,
                "message": auth_msg
            },
            "cache_size": len(FAM_ID_MAPPING),
            "session_initialized": SESSION is not None,
            "api_endpoint": "/activity/v2/requests/all/?status=1",
            "credits": get_credits_info(),
            "uptime": time.time() - app_start_time if 'app_start_time' in globals() else 0
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "credits": get_credits_info()
        }), 503

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "credits": get_credits_info()
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed",
        "credits": get_credits_info()
    }), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "credits": get_credits_info()
    }), 500

# For Vercel - no main block needed, but keep for local testing
if __name__ == '__main__':
    global app_start_time
    app_start_time = time.time()
    
    print("=" * 70)
    print("FAM API SERVER - UPDATED VERSION")
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
        print("3. View blocked: http://localhost:5000/blocked")
        print("4. Credits: http://localhost:5000/credits")
    else:
        print(f"❌ Authentication FAILED: {auth_msg}")
        print("\n⚠️  Check your captured data. Token may be expired.")
    
    print("=" * 70)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
