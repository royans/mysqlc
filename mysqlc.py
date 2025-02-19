#!/usr/bin/env python3
import os
import mysql.connector
import time
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.filters import Condition
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import MySqlLexer
from prompt_toolkit.completion import NestedCompleter, WordCompleter
from prompt_toolkit.application import get_app # Import get_app

version = 0.18

# History file path
history_file = os.path.expanduser('~/.mysqlc.history')
history = {} 

# Setup global configuration
gemini_api_key = os.environ["GEMINI_API_KEY"]

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
sql_completer = WordCompleter([], ignore_case=True)

    
bindings = KeyBindings()    
@bindings.add('tab')
def _(event: KeyPressEvent):
    "Allow tabs to be inserted as input."
    event.app.current_buffer.insert_text("  ")
       
session = PromptSession(
    history=FileHistory(history_file),
    multiline=True,
    key_bindings=bindings,
    completer=sql_completer  # Add the completer to the session
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
    print(f"   -- Using Gemini model: {filtered_models[0]}")
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
- Note that table names are case sensitive. 
- YOU MUST NOTE CHANGE THE CASE OF THE TABLE or FIELD NAMES.
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

    columns = [desc[0] for desc in cursor.description]  # Extract column names directly

    col_widths = [len(col) for col in columns] # Initialize with header length

    # Calculate column widths, including NULL/None representation
    for row in results:
        for i, col in enumerate(columns):
            value = row[col]
            col_widths[i] = max(col_widths[i], len(str(value) if value is not None else "None"))

    # Print header
    header = "|" + "|".join(f" {col:<{col_widths[i]}} " for i, col in enumerate(columns)) + "|"
    separator = "+" + "+".join("-" * (col_widths[i] + 2) for i in range(len(columns))) + "+"
    print(separator)
    print(header)
    print(separator)

    # Print rows
    for row in results:
        row_str = "|" + "|".join(f" {str(row[col]) if row[col] is not None else ' None':<{col_widths[i]}} " for i, col in enumerate(columns)) + "|"
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
    global history
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            row_id = 1
            current_command = ""  # Initialize current_command here
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    # New command starts
                    if current_command:
                        history[row_id] = current_command.strip()
                        row_id += 1
                        current_command = ""
                elif line.startswith("+"):
                    # Add to previous command
                    current_command += " " + line[1:].strip()
                else:
                    # New command
                    if current_command:  # Add previous command if exists
                        history[row_id] = current_command.strip()
                        row_id += 1
                    current_command = line
            # Add the last command if it exists
            if current_command:
                history[row_id] = current_command.strip()
    return history

def save_history(history_file):
    """Saves command history to the history file."""
    global history
    try:
        with open(history_file, 'w') as f:
            for row_id, cmd in history.items():
                f.write(f"{cmd}\n")
    except Exception as e:
        print(f"Error saving history: {e}")


def infobanner():
    print(f"""
------------------------------------------------          
mysqlc: A modern MySQL client
- Version: {version}
- Source: https://github.com/royans/mysqlc

Note: Press "ALT+Enter" to execute command.
------------------------------------------------          
""")

def execute_recent_match(history, partial_command):
    """
    Finds and executes the most recent command in history that matches the partial command.

    Args:
        history: A dictionary containing command history (row_id: command).
        partial_command: The partial command to search for.

    Returns:
        True if a matching command was found and executed, False otherwise.
    """
    import re

    matching_commands = []
    for row_id, command in history.items():
        if re.search(f"^\\s*{partial_command}", command, re.IGNORECASE): # Improved regex for partial match at the beginning of the command
            matching_commands.append((row_id, command))

    if matching_commands:
        # Sort by row_id to get the most recent command
        matching_commands.sort(reverse=True)
        most_recent_row_id, most_recent_command = matching_commands[0]
        print(f"Executing: {most_recent_command}")
        return most_recent_command
    else:
        print("No matching command found.")
        return None

def broken_update_completer(cursor):
    """Updates the WordCompleter with SQL keywords and table/column names."""

    sql_keywords = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "INSERT", "UPDATE", "DELETE",
        "CREATE", "ALTER", "DROP", "TABLE", "DATABASE", "INDEX", "VIEW",
        "USE", "SHOW", "DESCRIBE", "EXPLAIN", "GRANT", "REVOKE", "COMMIT",
        "ROLLBACK", "SAVEPOINT", "SET", "NULL", "TRUE", "FALSE", "LIMIT",
        "ORDER BY", "GROUP BY", "HAVING", "JOIN", "INNER", "LEFT", "RIGHT",
        "FULL", "OUTER", "ON", "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MIN",
        "MAX", "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "NOT IN", "BETWEEN",
        "LIKE", "ILIKE", "IS", "NOT", "EXISTS", "ANY", "ALL", "SOME", "UNION",
        "INTERSECT", "EXCEPT", "WITH", "RECURSIVE", "PRIMARY KEY", "FOREIGN KEY",
        "UNIQUE", "CONSTRAINT", "AUTO_INCREMENT", "DEFAULT", "CHECK", "COLUMN",
        "VARCHAR", "INT", "BIGINT", "TEXT", "DATE", "DATETIME", "TIMESTAMP", "ENUM",
        "BOOLEAN", "DECIMAL" # Add more SQL keywords as needed
    ]

    table_names = []
    start_time = time.time()  # Record start time
    try:
        cursor.execute("SHOW TABLES")
        for table in cursor.fetchall():
            table_names.append(list(table.values()))
    except mysql.connector.Error as err:
        print(f"Error fetching table names: {err}")
        return  # Exit early if there's an error
    end_time = time.time()  # Record end time
    table_fetch_time = end_time - start_time  # Calculate execution time
    print(f"Fetched tables in ({table_fetch_time:.3f} sec)")

    column_names = []
    start_time = time.time()  # Record start time
    for table in table_names:
        try:
            cursor.execute(f"DESCRIBE {table}")
            for column in cursor.fetchall():
                column_names.append(f"{table}.{column['Field']}") # Add table prefix
        except mysql.connector.Error as err:
            print(f"Error fetching columns for table {table}: {err}")
            continue # Skip to the next table if there's an error
    end_time = time.time()  # Record end time
    column_fetch_time = end_time - start_time  # Calculate execution time
    print(f"Fetched columns in ({column_fetch_time:.3f} sec)")

    start_time = time.time()  # Record start time        
    keyword_completer = WordCompleter(sql_keywords, ignore_case=True)
    table_completer = WordCompleter(table_names, ignore_case=True)
    column_completer = WordCompleter(column_names, ignore_case=True)

    global sql_completer
    sql_completer = NestedCompleter({
        '.': column_completer,
        ' ': NestedCompleter({
            '': table_completer
        }),
        '': keyword_completer
    })
    end_time = time.time()  # Record end time
    completer_time = end_time - start_time  # Calculate execution time
    print(f"sql_completer in ({completer_time:.3f} sec)")

def update_completer(cursor):
    """Updates the WordCompleter with SQL keywords and table/column names."""

    sql_keywords = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "INSERT", "UPDATE", "DELETE",
        "CREATE", "ALTER", "DROP", "TABLE", "DATABASE", "INDEX", "VIEW",
        "USE", "SHOW", "DESCRIBE", "EXPLAIN", "GRANT", "REVOKE", "COMMIT",
        "ROLLBACK", "SAVEPOINT", "SET", "NULL", "TRUE", "FALSE", "LIMIT",
        "ORDER BY", "GROUP BY", "HAVING", "JOIN", "INNER", "LEFT", "RIGHT",
        "FULL", "OUTER", "ON", "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MIN",
        "MAX", "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "NOT IN", "BETWEEN",
        "LIKE", "ILIKE", "IS", "NOT", "EXISTS", "ANY", "ALL", "SOME", "UNION",
        "INTERSECT", "EXCEPT", "WITH", "RECURSIVE", "PRIMARY KEY", "FOREIGN KEY",
        "UNIQUE", "CONSTRAINT", "AUTO_INCREMENT", "DEFAULT", "CHECK", "COLUMN",
        "VARCHAR", "INT", "BIGINT", "TEXT", "DATE", "DATETIME", "TIMESTAMP", "ENUM",
        "BOOLEAN", "DECIMAL" # Add more SQL keywords as needed
    ]

    table_names = []
    cursor.execute("SHOW TABLES")
    for table in cursor.fetchall():
        table_names.append(list(table.values())[0])

    column_names = []
    for table in table_names:
        cursor.execute(f"DESCRIBE {table}")
        for column in cursor.fetchall():
           column_names.append(f"{table}.{column['Field']}") # Add table prefix

    all_completions = sql_keywords + table_names + column_names
    sql_completer.words = all_completions  # Update the WordCompleter


def launch():
    schema = None
    conn = None
    cur = None
    model = None
    chat_history = []
    completer_needs_update = True

    # Set up command-line arguments
    parser = argparse.ArgumentParser(description='A Smarter Modern MySQL client')
    parser.add_argument('--port', help='MySQL port', type=int, default=3306)
    parser.add_argument('-u', '--user', help='MySQL username')
    parser.add_argument('-p', '--password', help='MySQL password')
    parser.add_argument('-H', '--host', help='MySQL host')
    parser.add_argument('-d', '--database', help='Default database')
    parser.add_argument('-g', '--gemini_api_key', help='Gemini API key')
    parser.add_argument('-s', '--syntax-highlighting', action='store_true', help='Enable syntax highlighting')
    parser.add_argument('--no-password', action='store_true', help='Do not use a password even if it is in env variables')

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
        db_config['port'] = args.port
    if args.no_password and 'password' in db_config:
        del db_config['password']
    if args.gemini_api_key:
        global gemini_api_key
        gemini_api_key = args.gemini_api_key

    try:
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary=True)
        conn.autocommit = False

        history = load_history(history_file)
        sql_accumulator = ""

        infobanner()

        while True:
            current_db = conn.database

            if schema is None or db_config['database']!= current_db:
                schema = get_database_schema(cur)
                db_config['database'] = current_db
                completer_needs_update = True

            if completer_needs_update:
                update_completer(cur)
                completer_needs_update = False

            prompt = f"Mysql [{current_db}] SQL> " if current_db else "Mysql SQL> "

            try:
                lexer = PygmentsLexer(MySqlLexer) if args.syntax_highlighting else None
                line = session.prompt(prompt, lexer=lexer)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break

            if not line:
                continue

            if line.strip() == "history":
                last_100_keys = sorted(history.keys())[-100:]
                for row_id in last_100_keys:
                    print(f"{row_id}. {history[row_id]}")
                continue

            if line.startswith("!"):
                try:
                    # Try to convert to int first to see if it is a specific command number
                    cmd_num = int(line[1:])
                    sql = history[cmd_num]  # Access history using row ID
                    print(f"Executing: {sql}")
                except ValueError:
                    # If it's not an integer, then it's a partial match
                    sql = execute_recent_match(history, line[1:])
                    if sql is None:
                        continue
                except (IndexError):
                    print("Invalid history command.")
                    continue
            else:
                sql_accumulator += line + "\n"
                sql = sql_accumulator.strip()
                sql_accumulator = ""

            try:
                if not conn.is_connected():
                    print("Connection lost. Reconnecting...")
                    conn = reconnect(db_config)
                    cur = conn.cursor(dictionary=True)
                    completer_needs_update = True

                if sql.startswith("translate") or not sql.lstrip().upper().startswith(validSqlCommands):
                    print(" --Requesting GenAI help")
                    if model is None:
                        model = get_top_flash_model()
                    translate = sql[len("translate"):].strip()
                    _sql, chat_history = askGemini(
                        f"Answer with a single line Mysql SQL query to answer the following question '{translate}'. \n",
                        schema,
                        chat_history,
                        model,
                    )
                    sql = extract_sql_command(_sql)
                    print(f" Running: {sql} ")

                start_time = time.time()
                cur.execute(sql)
                end_time = time.time()
                execution_time = end_time - start_time

                try:
                    results = cur.fetchall()
                    row_count = len(results)
                    print_formatted_results(cur, results)
                    print(f"{row_count} rows in set ({execution_time:.3f} sec)")
                except mysql.connector.errors.ProgrammingError:
                    print("Query executed successfully.")

                history[len(history) + 1] = sql  # Add command to history with new row ID
                save_history(history_file)
                conn.commit()

            except mysql.connector.Error as err:
                print(f"Error: {err}")
                if err.errno == mysql.connector.errorcode.CR_SERVER_LOST:
                    conn = reconnect(db_config)
                    cur = conn.cursor(dictionary=True)
                    completer_needs_update = True

    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL Platform: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            
def main():
    launch()

if __name__ == '__main__':
    main()
