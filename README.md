# mysqlc - the modern MySQL client

## Features
* Allow multi-line SQL query creation/editing
* Maintains/saves execution history
* "history" command shows history of SQL execution
* "!" command followed by the history id, will allow you to execute a previous command
* "translate" command allows you to use "Google Gemini" to create and execute SQL queries for you

## Required
* You will need credentials to connect to a database
* Optionally, you can provide Gemini API key (get it from https://aistudio.google.com/apikey) if you need Gemini to help you create SQL scripts. 

## How to use
* Setup environment variables in your shell
  * Required
    * DB_USER='username'
    * DB_PASSWORD='password'
    * DB_HOST='hostname'
    * DB_DATABASE='default_database' 
  * Optional
  * GEMINI_API_KEY='api_key'
* Add the location of this directory to your PATH variable
* Finally, execute: **mysqlc** 