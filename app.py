import os
from dotenv import load_dotenv
from pathlib import Path

import random
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from recipe_agent import get_recipes
from agents.phrasal_verb_agent import get_ia_wrong_options, get_ia_sentence_feedback
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



@app.route('/practice')
def home_practice():
    session['thread_id'] = str(uuid.uuid4())  # Generate a unique thread ID for each session
    try:
        cursor = mysql.connection.cursor()
        
        # 1. Fetch the single random target phrasal verb
        cursor.execute("SELECT id_word, name, description FROM tt_phrasal_verb ORDER BY RAND() LIMIT 1")
        row_phrasal_verb = cursor.fetchall()    
        #print(f"Target verb: {row_phrasal_verb}")  
        
        tb_options = []
        if row_phrasal_verb:
            # Extract the correct ID and definition from your tuple structure
            correct_id = row_phrasal_verb[0]['id_word']
            correct_description = row_phrasal_verb[0]['description']
            #print(f"Correct ID: {correct_id}, Correct Description: {correct_description}")

            # 2. Fetch 2 RANDOM descriptions from rows that are NOT the correct one
            cursor.execute("""
                SELECT id_word, description 
                FROM tt_phrasal_verb 
                WHERE id_word != %s 
                ORDER BY RAND() 
                LIMIT 2
            """, (correct_id,))
            
            wrong_options = cursor.fetchall()

            #2.1 Bring wrong options from the IA agent as well, to make it more challenging for the user
            get_ia_wrong_options_response = get_ia_wrong_options(row_phrasal_verb[0]['name'])
            options_ia_list = get_ia_wrong_options_response.get('meaning', [])
            #print(f"Options from IA agent: {options_ia_list}")

            # 3. Combine the correct description and the wrong ones into a single list
            # using a dictionary cursor (DictCursor) allows us to access columns by name, which is more robust than relying on index positions
            tb_options = [correct_description] + [row['description'] for row in wrong_options]

            #3.1 Add the IA agent options to the list as well
            for option in options_ia_list:
                tb_options.append(option.get('wrong_meaning', ''))
            
            # 4. Shuffle the list so the correct answer isn't always the first choice!
            random.shuffle(tb_options)
            #print(f"Shuffled options: {tb_options}")
            
    except Exception as db_err:
        print(f"Database error encountered while fetching data: {db_err}")
        row_phrasal_verb = []
        tb_options = []
        
    return render_template('practice.html', tb_phrasal_verb=row_phrasal_verb, tb_options=tb_options)





@app.route('/submit_answer', methods=['POST'])
def send_option():
    # 1. Fetch the user's ingredients from the form
    user_choice = request.form['user_choice']
    phrasal_verb_id = request.form['phrasal_verb_id']
    phrasal_verb_name = request.form['phrasal_verb_name']
    user_sentence = request.form['user_sentence']
    #print(f"Form submitted option: {phrasal_verb_id}")
    #print(f"Form submitted option: {user_choice}")
    
    # 2. Guard clause: handling empty inputs
    if not user_choice.strip():
        return redirect(url_for('home_practice'))
    
    # 2.1 Send parameters to the IA agent to check your sentence and give you feedback
    get_ia_sentence_feedback_response = get_ia_sentence_feedback(phrasal_verb_name, user_choice, user_sentence)
    grammar_check = get_ia_sentence_feedback_response.get('grammar_check', [])
    grammar_feedback = get_ia_sentence_feedback_response.get('grammar_feedback', [])
    local_naturalness = get_ia_sentence_feedback_response.get('local_naturalness', [])

    # 3. Check if the user's choice is correct by comparing it to the correct description in the database
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT description FROM tt_phrasal_verb WHERE id_word = %s", (phrasal_verb_id,))
        correct_description = cursor.fetchone()
        
        if correct_description and user_choice == correct_description['description']:
            print("User's choice is correct!")
            return jsonify(
                {
                 'status': 'success', 
                 'correct': True, 
                 'message_j': 'Correct answer, You got the meaning!',
                 'grammar_check': grammar_check,
                 'grammar_feedback': grammar_feedback,
                 'local_naturalness': local_naturalness
                }
            )
        else:
            print("User's choice is incorrect.")
            return jsonify({
                'status': 'success', 
                'correct': False, 
                'message_j': 'Incorrect answer. You did not get the meaning.',
                'grammar_check': grammar_check,
                'grammar_feedback': grammar_feedback,
                'local_naturalness': local_naturalness
            })
    except Exception as db_err:
        print(f"Database error encountered while checking answer: {db_err}")
        return jsonify({'status': 'error', 'message_j': 'Database error occurred'}), 500
    





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