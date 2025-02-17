# mysqlc - the modern MySQL client

We all love Mysql/Mariadb, but one thing which we all could benifit from is having a few more features in its barebones command line client. There are commercial options available which are significantly more powerful, but some things should just be free for all. This tiny project addresses a few of these gaps which I personally dislike. 

I built this primarily for myself, but hope its helpful for others as well.

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
* Or pass the variables as command line options
  <pre>
  options:
  -h, --help            show this help message and exit
  -u USER, --user USER  MySQL username
  -p PASSWORD, --password PASSWORD
                        MySQL password
  -H HOST, --host HOST  MySQL host
  -d DATABASE, --database DATABASE
                        Default database
  -g GEMINI_API_KEY, --gemini_api_key GEMINI_API_KEY
                        Gemini API key
  </pre>
* Add the location of this directory to your PATH variable
* Finally, execute: **mysqlc** 