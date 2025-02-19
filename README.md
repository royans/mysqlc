# mysqlc - Modern MySQL client with GenAI boost

We all love Mysql/Mariadb, but one thing which we all could benifit from is having a few more features in its barebones command line client. There are commercial options available which are significantly more powerful, but some things should just be free for all.  This tiny project addresses a few of these gaps which I personally dislike.

Note that this project uses **Google Gemini** to help you quickly use GenAI smarts to create your queries. Feel free to reuse this code to add other adapters as you see fit.

I built this primarily for myself, and hope its helpful for others as well.

## Features
* Allow multi-line SQL query creation/editing
* Maintains/saves execution history
* "history" command shows history of SQL execution
* "!" command followed by the history id, will allow you to execute a previous command
* Autocomplete support for some of the commands an table/column names  
* "translate" command allows you to use "Google Gemini" to create and execute SQL queries for you
  * Note that in some cases, you can skip "translate" and directly ask the question
  * Examples
    * translate: how many rows were added to table xyz in last 24 hours ?
    * give me a list of top 10 cities along with their frequencies

## Required
* You will need credentials to connect to a database
* Optionally, you can provide Gemini API key (get it from https://aistudio.google.com/apikey) if you need Gemini to help you create SQL scripts. 

## How to use
* Setup environment variables in your shell
  * Required
    * DB_USER=*'username'*
    * DB_PASSWORD=*'password'*
    * DB_HOST=*'hostname'*
    * DB_DATABASE=*'default_database'* 
  * Optional
  * GEMINI_API_KEY=*'your_api_key_here'*

* Or pass the variables as command line options
  <pre>
usage: mysqlc.py [-h] [--port PORT] [-u USER] [-p PASSWORD] [-H HOST] [-d DATABASE] [-g GEMINI_API_KEY] [--no-password]

A Smarter Modern MySQL client

options:
  -h, --help            show this help message and exit
  --port PORT           MySQL port
  -u USER, --user USER  MySQL username
  -p PASSWORD, --password PASSWORD
                        MySQL password
  -H HOST, --host HOST  MySQL host
  -d DATABASE, --database DATABASE
                        Default database
  -g GEMINI_API_KEY, --gemini_api_key GEMINI_API_KEY
                        Gemini API key
  --no-password         Do not use a password even if it is in env variables
  </pre>

* Add the location of this directory to your PATH variable

* Finally, execute: **mysqlc** 

## Examples

### Basic usage
<pre>
Mysql [hopot] SQL> show tables
+-----------------+
| Tables_in_hopot |
+-----------------+
| fakepages       |
| requests        |
+-----------------+
2 rows in set (0.001 sec)
Mysql [hopot] SQL> desc requests
+-----------------+------------------+------+-----+---------------------+----------------+
| Field           | Type             | Null | Key | Default             | Extra          |
+-----------------+------------------+------+-----+---------------------+----------------+
| id              | int(10) unsigned | NO   | PRI |  None               | auto_increment |
| timestamp       | timestamp        | NO   | MUL | current_timestamp() |                |
| remote_ip       | varchar(45)      | NO   | MUL |  None               |                |
| request_method  | varchar(10)      | NO   |     |  None               |                |
| request_uri     | varchar(255)     | NO   | MUL |  None               |                |
| user_agent      | text             | YES  |     |  None               |                |
| referer         | text             | YES  |     |  None               |                |
| request_headers | text             | YES  |     |  None               |                |
| request_body    | text             | YES  |     |  None               |                |
| response_code   | int(11)          | YES  |     |  None               |                |
+-----------------+------------------+------+-----+---------------------+----------------+
10 rows in set (0.005 sec)
</pre>

### Show history
<pre>
Mysql [hopot] SQL> history
 
1. show tables
2. desc requests
</pre>

### Execute previous command
<pre>
Mysql [hopot] SQL> !1
Executing: show tables
+-----------------+
| Tables_in_hopot |
+-----------------+
| fakepages       |
| requests        |
+-----------------+
</pre>

### Using Gemini to create the SQL queries for you
<pre>
Mysql [hopot] SQL> how many rows are there in the table requests ?
 
 [Requesting GenAI help]
 Running: SELECT COUNT(*) FROM requests; 
+----------+
| COUNT(*) |
+----------+
| 12137    |
+----------+
1 rows in set (0.010 sec)
</pre>

<pre>
Mysql [hopot] SQL> translate using the table requests, please tell me which is the most popular 10 user_agents in the last 24 hours, show the frequency and sort in reverse order of frequency
 
 Running: SELECT user_agent, COUNT(*) AS frequency FROM requests WHERE timestamp >= NOW() - INTERVAL 1 DAY GROUP BY user_agent ORDER BY frequency DESC LIMIT 10; 
+--------------------------------------------------------------------------------------------------------------------------+-----------+
| user_agent                                                                                                               | frequency |
+--------------------------------------------------------------------------------------------------------------------------+-----------+
| Go-http-client/1.1                                                                                                       | 49        |
| Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36                | 10        |
| Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36          | 4         |
| Mozilla/5.0 (l9scan/2.0.134313e25373e2830323e25333; +https://leakix.net)                                                 | 3         |
| Mozilla/5.0 (Linux; Android 9; CLT-L29) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.111 Mobile Safari/537.36 | 1         |
| Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6 GTB5                            | 1         |
| ALittle Client                                                                                                           | 1         |
| python-requests/2.22.0                                                                                                   | 1         |
+--------------------------------------------------------------------------------------------------------------------------+-----------+
</pre>

<pre>
Mysql [hopot] SQL> desc requests
+-----------------+------------------+------+-----+---------------------+----------------+
| Field           | Type             | Null | Key | Default             | Extra          |
+-----------------+------------------+------+-----+---------------------+----------------+
| id              | int(10) unsigned | NO   | PRI |  None               | auto_increment |
| timestamp       | timestamp        | NO   | MUL | current_timestamp() |                |
| remote_ip       | varchar(45)      | NO   | MUL |  None               |                |
| request_method  | varchar(10)      | NO   |     |  None               |                |
| request_uri     | varchar(255)     | NO   | MUL |  None               |                |
| user_agent      | text             | YES  |     |  None               |                |
| referer         | text             | YES  |     |  None               |                |
| request_headers | text             | YES  |     |  None               |                |
| request_body    | text             | YES  |     |  None               |                |
| response_code   | int(11)          | YES  |     |  None               |                |
+-----------------+------------------+------+-----+---------------------+----------------+

Mysql [hopot] SQL> list the top 10 request_uri in the last 1 week which had a response_code of 200
 [Requesting GenAI help]
 Running: SELECT request_uri, COUNT(*) AS frequency FROM requests WHERE timestamp >= NOW() - INTERVAL 1 WEEK AND response_code = 200 GROUP BY request_uri ORDER BY frequency DESC LIMIT 10; 
+----------------------------------+-----------+
| request_uri                      | frequency |
+----------------------------------+-----------+
| /debug/default/view?panel=config | 47        |
| /phpmyadmin/                     | 37        |
| /.env                            | 31        |
| /.git/config                     | 25        |
| /info.php                        | 17        |
| /config.json                     | 16        |
| /tool/view/phpinfo.view.php      | 16        |
| /debug/default/view.html         | 16        |
| /debug/default/view              | 16        |
| /frontend/web/debug/default/view | 16        |
+----------------------------------+-----------+
10 rows in set (0.370 sec)
</pre>

## Risks/Warnings
* This is a proof of concept. Don't trust it, but feel free to be inspired
* The "translate" command works perfectly for simple operations, but may require a few attempts for more complex operations
  * In a future version, I may introduce retries (which I do with gbash), but not in this current one
* There is no input validation at all - again the assumption is that its being run by someone fully trusted
* SQL History record could be a potential source of leak as well - we should assume the system is locked down


