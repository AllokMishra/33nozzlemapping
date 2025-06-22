from flask import Flask, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv
import os, json, re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
mappings_collection = db['mappings']

# --- Helpers ---

def clean_trailing_commas(json_str):
    return re.sub(r',\s*(\]|\})', r'\1', json_str)

def extract_json_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'\[\s*{.*?}\s*\]', content, re.DOTALL)
        if match:
            raw_json = clean_trailing_commas(match.group(0))
            return json.loads(raw_json)
        else:
            print(f"No JSON block found in {file_path}")
            return []
    except Exception as e:
        print(f"Error loading {file_path}:", e)
        return []

# --- Load Data ---
tw_data = extract_json_from_file('tw.md')
digitory_data = extract_json_from_file('digi.md')

tw_beverages = [
    {'id': str(item['id']), 'name': item['name']}
    for item in tw_data if item.get('types') == 'Secondary menu'
]

digitory_items = [
    {'pluCode': item['pluCode'], 'name': item['name']}
    for item in digitory_data if item.get('pluCode')
]

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html',
                           tw_beverages=tw_beverages,
                           digitory_items=digitory_items)

@app.route('/map', methods=['POST'])
def map_items():
    total_rows = int(request.form.get('total_rows', 0))
    mappings = []

    for i in range(1, total_rows + 1):
        tw_id = request.form.get(f'tw_id_{i}')
        tw_name = request.form.get(f'tw_name_{i}')
        plu_code = request.form.get(f'plu_code_{i}')

        if tw_id and plu_code:
            digitory_name = next(
                (item['name'] for item in digitory_items if item['pluCode'] == plu_code),
                'Unknown'
            )
            mappings.append({
                'tw_id': tw_id,
                'tw_name': tw_name,
                'plu_code': plu_code,
                'digitory_name': digitory_name
            })

    if mappings:
        mappings_collection.insert_many(mappings)

    return render_template('success.html', mappings=mappings)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

