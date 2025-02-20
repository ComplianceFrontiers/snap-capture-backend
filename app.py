from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient,DESCENDING
from dotenv import load_dotenv
import os
import base64,random

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

app = Flask(__name__)
CORS(app)
load_dotenv()

# Get the MongoDB URI from the environment variable 
mongo_uri = os.getenv('MONGO_URI')
# MongoDB setup
client = MongoClient(mongo_uri)
db = client.chessschool
users_collection = db.snap_capture

@app.route('/')
def home():
    return "Hello, Flask on Vercel! "

def time_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@app.route('/signin', methods=['POST'])
def signin():
    user_data = request.get_json()

    # Ensure phone number is provided
    if not user_data or 'phone' not in user_data:
        return jsonify({'error': 'Phone number is required.'}), 400

    phone = user_data.get('phone')


    # Search for users whose phone number contains the entered digits
    matching_users = list(users_collection.find(
        {'phone': {'$regex': phone, '$options': 'i'}},  # Case-insensitive search
        {'_id': 0}
    ))

    if matching_users:
       
        return jsonify({
            'success': True,
            'users': matching_users,
            'message': 'Matching users found.'
        }), 200
    else:
        return jsonify({'error': 'No matching users found.'}), 404

def generate_unique_user_id():
    """Generate a unique 6-digit user ID"""
    while True:
        user_id = str(random.randint(100000, 999999))  # Generate 6-digit number
        if not users_collection.find_one({"user_id": user_id}):  # Ensure it's unique
            return user_id

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json

    # Validate required fields
    required_fields = ["phone", "email", "first_name", "last_name", "last_signin"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Generate unique user ID
    user_id = generate_unique_user_id()

    # Prepare user data
    user_data = {
        "phone": data["phone"],
        "email": data["email"],
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "user_id": user_id,  # Unique 6-digit user ID
        "last_signin": data["last_signin"],
        "profile_pic": data.get("profile_pic", ""),
    }

    # Insert new user into MongoDB
    result = users_collection.insert_one(user_data)

    # Fetch inserted user data
    inserted_user = users_collection.find_one({"_id": result.inserted_id}, {"_id": 0})  # Exclude `_id` field

    return jsonify({"message": "Signup successful", "user": inserted_user}), 200

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    try:
        user_id = request.form.get('user_id')
        last_signin = request.form.get('last_signin')  # Taking last_signin from request
        profile_pic = request.files.get('profile_pic')
        signin = True

        if not user_id or not last_signin or not profile_pic:
            return jsonify({'error': 'User ID, last_signin, and profile picture are required.'}), 400

        # 🔴 Convert bytes (image) to a Base64-encoded string
        profile_pic_base64 = base64.b64encode(profile_pic.read()).decode('utf-8')

        # Update or insert user profile
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'last_signin': last_signin, 'profile_pic': profile_pic_base64,'signin':signin}},
            upsert=True
        )

        return jsonify({'success': True, 'message': 'Profile picture updated successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/today_logins', methods=['GET'])
def today_logins():
    try:
        # Get date from request parameters (default to today's date in UTC)
        date_str = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))  

        # Query using regex to match timestamps that start with the given date
        today_users = users_collection.find({
            "last_signin": {"$regex": f"^{date_str}"},
            "signin": True
        })

        # Convert results to JSON
        users_list = [
            {
                "user_id": user["user_id"],
                "signin": user["signin"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "last_signin": user["last_signin"],
                "profile_pic": user.get("profile_pic", None)
            }
            for user in today_users
        ]

        return jsonify({"success": True, "users": users_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_signin', methods=['POST'])
def update_signin():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        signin_flag = data.get("signin")  # Boolean value (True/False)

        if user_id is None or signin_flag is None:
            return jsonify({"error": "Missing user_id or signin flag"}), 400

        # Update the signin flag for the given user_id
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"signin": signin_flag}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"success": True, "message": "Signin flag updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
        # Fetch all records from the collection, sorted by last_signin in descending order
        users = users_collection.find({}, {'_id': 0}).sort('last_signin',DESCENDING)  # Exclude the _id field
        # Convert MongoDB documents to a list of dictionaries
        users_list = list(users)
        return jsonify(users_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)