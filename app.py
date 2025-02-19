from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient,DESCENDING
from dotenv import load_dotenv
import os
import pytz

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
users_collection = db.snap-capture # type: ignore

@app.route('/')
def home():
    return "Hello, Flask on Vercel! "

def time_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/signup', methods=['POST'])
def signup():
    user_data = request.get_json()
    if user_data:
        parent_name = user_data.get('parentName')
        kidnames = [
            user_data.get('kidName1'),
            user_data.get('kidName2'),
            user_data.get('kidName3')
        ]
        schoolnames = [
            user_data.get('schoolName1'),
            user_data.get('schoolName2'),
            user_data.get('schoolName3')
        ]
        gradenames = [
            user_data.get('schoolgrade1'),
            user_data.get('schoolgrade2'),
            user_data.get('schoolgrade3')
        ]
        email = user_data.get('email')
        phone = user_data.get('phone')
        
        # Check if email already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return jsonify({'error': 'User already exists. Please login.'}), 400
        
        # Handle kid1 specific checks
        if not kidnames[0]:  # kidName1
            kidnames[0] = "not a kid"
        if not schoolnames[0]:  # schoolName1
            schoolnames[0] = "not a kid"
        if not gradenames[0]:  # schoolgrade1
            gradenames[0] = "not a kid"
        
        # Insert a record for each kid
        inserted_ids = []
        for kidname, schoolname, gradename in zip(kidnames, schoolnames, gradenames):
            if kidname and schoolname:
                new_user = {
                    'parentName': parent_name,
                    'kidName': kidname,
                    'schoolName': schoolname,
                    'gradename': gradename,
                    'email': email,
                    'phone': phone,
                }
                result = users_collection.insert_one(new_user)
                inserted_ids.append(str(result.inserted_id))  # Convert ObjectId to string
        
        return jsonify({'success': True, 'insertedIds': inserted_ids}), 201
    else:
        return jsonify({'error': 'Invalid data format.'}), 400

@app.route('/signin', methods=['POST'])
def signin():
    user_data = request.get_json()
    
    # Ensure phone number is provided
    if not user_data or 'phone' not in user_data:
        return jsonify({'error': 'Phone number is required.'}), 400
    
    phone = user_data.get('phone')

    # Get the current timestamp in IST
    ist_time_zone = pytz.timezone('Asia/Kolkata')
    current_timestamp = datetime.now(ist_time_zone).isoformat()

    # Update `last_signin` for all matching users
    update_result = users_collection.update_many(
        {'phone': phone},
        {'$set': {'last_signin': current_timestamp}}
    )

    # Find and return updated user records (excluding `_id` and `capture_datetime`)
    matching_users = list(users_collection.find({'phone': phone}, {'_id': 0}))

    if matching_users:
        return jsonify({
            'success': True,
            'users': matching_users,
            'message': 'Sign-in successful. Last sign-in time updated.'
        }), 200
    else:
        return jsonify({'error': 'No users found with this phone number.'}), 404
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
    app.run()