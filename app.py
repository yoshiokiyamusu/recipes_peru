import os
from dotenv import load_dotenv
from pathlib import Path

import random
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from recipe_agent import get_recipes
import uuid
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key'

load_dotenv()

# Define the path to your .env file
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path) # Load the specific .env file
else:
    load_dotenv() # for Render's environment variables settings

# Mysql Settings
app.config['MYSQL_USER'] = os.getenv('DB_USER') or 'root'
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASS') or ''
app.config['MYSQL_HOST'] = os.getenv('DB_SERVER') or '127.0.0.1'
app.config['MYSQL_PORT'] = int(os.getenv('DB_PORT') or 3306)
app.config['MYSQL_DB'] = os.getenv('DB_NAME') or ''
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# MySQL Connection initialized here
mysql = MySQL(app)

@app.route('/')
def home():
    session['thread_id'] = str(uuid.uuid4())  # Generate a unique thread ID for each session
    if 'messages' not in session:
        session['messages'] = []
    try:
        # Fetch all recipes from the database to display on the homepage
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name, description, prep_time FROM tt_recipes_tb ORDER BY created_at DESC")
        tb_recipes = cursor.fetchall()    
        print(tb_recipes)  
    except Exception as db_err:
        print(f"Database error encountered while fetching recipes: {db_err}")
        tb_recipes = []  # Fallback to an empty list if there's a database error  
    return render_template('recipe.html', messages=session['messages'], tb_recipes = tb_recipes)

@app.route('/send_ingredient', methods=['POST'])
def send():
    # 1. Fetch the user's ingredients from the form
    user_message = request.form['message']
    print(f"Received user message: {user_message}")
    
    # 2. Guard clause: handling empty inputs
    if not user_message.strip():
        return redirect(url_for('home'))

    try:
        # 3. Call your recipe agent function
        agent_response = get_recipes(user_message)
        
        # 4. Save both the query and the result to the session messages
        # We use a structured format so your HTML template can easily loop through it
        new_interaction = {
            "user": user_message,
            "agent_response": agent_response
        }
        #print(new_interaction)

        # Flask sessions require you to re-assign or mark modified when mutating lists
        messages = session.get('messages', [])
        messages.append(new_interaction)
        session['messages'] = messages
        #print(f"Updated session messages: {session['messages']}")

        # 5. Isolated Database Transaction Block
        cursor = None
        try:
            # Insert the recipe into the MySQL database
            cursor = mysql.connection.cursor()
            # Generate a unified recipe batch ID for this generation
            batch_recipe_id = random.randint(100, 999) if 'random' in globals() else uuid.uuid4().int % 1000000

            # Pull the recipes array safely
            recipes_list = agent_response.get('recipes', [])

            query = """
                INSERT INTO tt_recipes_tb (id_recipe, name, description, prep_time, created_at) 
                VALUES (%s, %s, %s, %s, NOW())
            """

            # Loop through all available recipes in the agent's response
            #print("RECIPES_LIST CONTENT:", recipes_list)
            for recipe in recipes_list:
                recipe_data = (
                    batch_recipe_id,
                    recipe.get('name', 'Unknown Recipe'),
                    recipe.get('description', ''),
                    recipe.get('prep_time', 'N/A')
                )
                cursor.execute(query, recipe_data)
                
            mysql.connection.commit()
        except Exception as db_err:    
            print(f"Database error encountered: {db_err}")
            # Securely rollback since we know the transaction actually started
            try:
                mysql.connection.rollback()
                print("Database transaction rolled back successfully.")
            except Exception as rollback_err:
                print(f"Rollback failed: {rollback_err}") 
        finally:
        # This block ALWAYS runs        
            if cursor:
                cursor.close()

    except Exception as e:
        print(f"Error querying recipe agent: {e}")

    # 5. Return a response to the browser so the page reloads and shows the data
    return redirect(url_for('home'))
    
@app.route('/clear')
def clear_session():
    session.clear()
    return redirect(url_for('home'))
    


if __name__ == "__main__":
    #app.run(debug=True, port=8182, use_reloader=False)
    # To deploy in render, use the following lines instead of the above line:
    port = int(os.getenv("PORT", 8180))
    app.run(host="0.0.0.0", port=port)