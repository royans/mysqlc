#!/usr/bin/env python3
import os
import mysql.connector
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import MySqlLexer
import argparse

version = 0.16

# Database connection details from environment variables
db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE')
}

validSqlCommands = ("SELECT", "USE", "SHOW", "DESC","UPDATE", "INSERT", "DELETE", "CREATE", "ALTER", "DROP")
validGenAISqlCommands = ("SELECT", "USE", "SHOW", "DESC")

GenAICurrentSchema = None


gemini_api_key = os.environ["GEMINI_API_KEY"]

# History file path
history_file = os.path.expanduser('~/.mysqlc.history')

bindings = KeyBindings()

@bindings.add('tab')
def _(event: KeyPressEvent):
    "Allow tabs to be inserted as input."
    event.app.current_buffer.insert_text("  ")
       
session = PromptSession(
    history=FileHistory(history_file),
    multiline=True,
    key_bindings=bindings
)

def get_top_flash_model():
    """
    Retrieves a sorted list of available Gemini models that contain "flash" in their name,
    with "models/" removed from the strings.  The list is sorted with the latest models
    appearing first.

    Returns:
        list: A sorted list of matching model names.
    """
    import google.generativeai as genai
    global gemini_api_key

    genai.configure(api_key=gemini_api_key)

    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        models = genai.list_models()
        filtered_models = [model.name.replace("models/", "") for model in models if "flash" in model.name and not "preview" in model.name and not "thinking" in model.name]

        # Sort by name in reverse alphabetical order to put "flash-latest" or similar at the top.
        filtered_models.sort(reverse=True)
    except Exception as e:
        return
    print(f"Using Gemini model: {filtered_models[0]}")
    return filtered_models[0]

def askGemini(query, schema, chat_history=None, default_model_name="gemini-2.0-flash"):
    import os
    import google.generativeai as genai

    global gemini_api_key, GenAICurrentSchema

    genai.configure(api_key=gemini_api_key)

    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name=default_model_name,
        generation_config=generation_config,
    )

    # Initialize chat history if not provided
    if chat_history is None:
        chat_history = []

    chat_session = model.start_chat(history=chat_history)
    
    if chat_history == None or len(chat_history)==0: 
        query = f"""
You are a MySQL query helper who is helping a database admin in their regular job.
- Please note that the questions the user is asking assumes you will try to understand the context, the history and respond back with single line valid MySQL query which the admin can execute.
- If the question has nothing to do with the current database, please do answer using a SELECT command: 
   - Example: if the question is "What is the capital of India", you could answer with " SELECT 'New Delhi'; " 

Please see the following schema to understand how to structure the sql to answer the question which follows
- Note that table names are case sensitive. Do not try to change them.
- Here is the schema: 
---------------
    {schema} 
---------------
\n\n
{query}
"""
        GenAICurrentSchema=schema

    if GenAICurrentSchema != schema:
        GenAICurrentSchema=schema
        query = f"""
Please note this is the latest database schema. The question will follow the schema:
---------------
    {schema} 
---------------
\n\n
{query}        
"""
    response = chat_session.send_message(query)

    # Append the current interaction to the history in the correct format.
    chat_history.append({
        "role": "user",  # Changed to "role": "user"
        "parts": [{"text": query}]
    })
    chat_history.append({
        "role": "model",  # Changed to "role": "model"
        "parts": [{"text": response.text}]
    })

    return response.text, chat_history

def print_formatted_results(cursor, results):
    """Prints the results in a formatted table."""

    if not results:
        return

        # Get column names (extract just the column name from the tuple)
    columns = [desc for desc in cursor.description]  # Corrected line

    col_width = 10
    col_widths = []
    # Calculate column widths
    for i in range(len(columns)):
        
        col_width = 0
        for row in results:
            col_width = max(col_width, len(str(row[columns[i][0]])))
    
        col_widths.append(col_width)
        
    # Print header
    header = "|" + "|".join(f" {columns[i][0]:<{col_widths[i]}} " for i in range(len(columns))) + "|"
    separator = "+" + "+".join("-" * (col_widths[i] + 2) for i in range(len(columns))) + "+"
    print(separator)
    print(header)
    print(separator)
    # Print rows
    for row in results:
        row_str = "|" + "|".join(f" {str(row[columns[i][0]]):<{col_widths[i]}} " for i in range(len(columns))) + "|"
        print(row_str)

    # Print footer
    print(separator)

def extract_sql_command(sql_string):
    """
    Extracts the first SQL command from a multiline string.

    Args:
        sql_string: The multiline string containing SQL commands.

    Returns:
        The first SQL command found, without quotes.
    """
    lines = sql_string.splitlines()
    
    #print(lines)
    for line in lines:
        line = line.strip()
        if line.upper().startswith(validGenAISqlCommands):
            return line
    print(f"Answer (not executing): {line}")
    return None

def reconnect(conn_params):
    """Attempts to reconnect to the MySQL server."""
    try:
        cnx = mysql.connector.connect(**conn_params)
        return cnx
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.CR_SERVER_LOST:
            print("Reconnecting...")
            time.sleep(2)  # Optional: Wait before retrying
            return reconnect(conn_params)  # Recursive call to retry
        else:
            raise err  # Re-raise other MySQL errors
        
def get_database_schema(cursor):
    """
    Retrieves the schema of all tables in the current database.

    Args:
        cursor: The database cursor object.

    Returns:
        A string containing the schema of all tables.
    """

    cursor.execute("SHOW TABLES")
    tables = [table for table in cursor.fetchall()]

    schema_str = ""
    for _table in tables:
        table = (list(_table.values())[0])
        schema_str += f"\n{table} = "
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        for column in columns:
            schema_str += f"  {column['Field']}: {column['Type']} , "
    return schema_str

def load_history(history_file):
    """Loads command history from the history file."""
    history = []
    current_command = ""
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    # New command starts
                    if current_command:
                        history.append(current_command.strip())
                        current_command = ""
                elif line.startswith("+"):
                    # Add to current command
                    current_command += line[1:].strip() + " "  # Remove '+' and add space
            # Add the last command if it exists
            if current_command:
                history.append(current_command.strip())
    return history

def infobanner():
    print(f"""
------------------------------------------------          
mysqlc: A modern MySQL client
- Version: {version}
- Source: https://github.com/royans/mysqlc

Note: Press "ALT+Enter" to execute command.
------------------------------------------------          
""")

def launch():
    schema = None
    conn = None # Initialize conn to None
    cur = None # Initialize cur to None
    model = None
    chat_history = []  # Initialize chat history outside the loop
    
    # Set up command-line arguments
    parser = argparse.ArgumentParser(description='A Smarter Modern MySQL client')
    parser.add_argument('--port', help='MySQL port', type=int, default=3306)  # Add port argument
    parser.add_argument('-u', '--user', help='MySQL username')
    parser.add_argument('-p', '--password', help='MySQL password')
    parser.add_argument('-H', '--host', help='MySQL host')
    parser.add_argument('-d', '--database', help='Default database')
    parser.add_argument('-g', '--gemini_api_key', help='Gemini API key')
    parser.add_argument('--no-password', action='store_true', help='Do not use a password even if it is in env variables')  # Add no-password flag
   
    args = parser.parse_args()

    # Override environment variables with command-line arguments
    if args.user:
        db_config['user'] = args.user
    if args.password:
        db_config['password'] = args.password
    if args.host:
        db_config['host'] = args.host
    if args.database:
        db_config['database'] = args.database
    if args.port:
        db_config['port'] = args.port  # Add port to db_config
    if args.no_password and 'password' in db_config:  # If no-password flag is set, remove password from db_config
        del db_config['password']        
    if args.gemini_api_key:
        global gemini_api_key
        gemini_api_key = args.gemini_api_key
        
            
    try:
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary=True)  # Use dictionary cursor for easier access
        conn.autocommit = False  # disable autocommit

        history = load_history(history_file)  # Load history
        sql_accumulator = ""

        infobanner()        
        
        while True:
            # Get the current database name
            current_db = conn.database

            if schema == None or db_config['database'] != current_db:
                schema=(get_database_schema(cur))
                db_config['database'] = current_db
                 
            # Update the prompt
            prompt = f"Mysql [{current_db}] SQL> " if current_db else "Mysql SQL> "

            try:
                line = session.prompt(prompt, lexer=PygmentsLexer(MySqlLexer))
            except (KeyboardInterrupt, EOFError):  # Catch Ctrl+C and Ctrl+D
                print("\nExiting...")
                break
            
            if not line:
                continue

            if line.strip() == "history":
                # Print the last 100 commands with line numbers
                for i, cmd in enumerate(history[-100:], start=1):
                    print(f"{i}. {cmd}")
                continue

            if line.startswith("!"):
                try:
                    # Extract the command number and execute it
                    cmd_num = int(line[1:])
                    sql = history[cmd_num - 1]
                    print(f"Executing: {sql}")
                except (IndexError, ValueError):
                    print("Invalid history command.")
                    continue
            else:
                # Accumulate SQL and execute as before
                sql_accumulator += line + "\n"
                sql = sql_accumulator.strip()
                sql_accumulator = ""
                
            try:
                if not conn.is_connected():
                    print("Connection lost. Reconnecting...")
                    conn = reconnect(db_config)
                    cur = conn.cursor(dictionary=True)

                if sql.startswith("translate") or not sql.lstrip().upper().startswith(validSqlCommands):
                    print(" [Requesting GenAI help]")
                    if model == None:
                        model = get_top_flash_model()
                    translate = sql[len("translate"):].strip()
                    # Pass the chat history to askGemini
                    _sql, chat_history = askGemini(
                        f"Answer with a single line Mysql SQL query to answer the following question '{translate}'. \n",
                        schema,
                        chat_history,  # Pass the history here.
                        model,
                    )
                    sql = extract_sql_command(_sql)
                    print(f" Running: {sql} ")
                start_time = time.time()  # Record start time
                cur.execute(sql)  # Execute SQL
                end_time = time.time()  # Record end time
                execution_time = end_time - start_time  # Calculate execution time

                try:
                    results = cur.fetchall()
                    row_count = len(results)  # Get the number of rows
                    print_formatted_results(cur, results)  # Print formatted results
                    print(f"{row_count} rows in set ({execution_time:.3f} sec)")  # Print timing information
                except mysql.connector.errors.ProgrammingError:
                    print("Query executed successfully.")

                history.append(sql)
                conn.commit()  # manual commit.

            except mysql.connector.Error as err:
                if err.errno == mysql.connector.errorcode.CR_SERVER_LOST:
                    conn = reconnect(db_config) # Reconnect
                    cur = conn.cursor(dictionary=True)  # Reset the cursor
                    # Retry the query
                    cur.execute(sql)

    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.CR_SERVER_LOST:
            conn = reconnect(db_config) # Reconnect
            cur = conn.cursor(dictionary=True)  # Reset the cursor
            # Retry the query
            cur.execute(sql)
            print(f"Error connecting to MySQL Platform: {e}")
        else:
            raise err
    finally:
        if conn and conn.is_connected():
            conn.close()

def main():
    launch()

if __name__ == '__main__':
    main()
