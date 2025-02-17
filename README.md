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
    * DB_USER=*'username'*
    * DB_PASSWORD=*'password'*
    * DB_HOST=*'hostname'*
    * DB_DATABASE=*'default_database'* 
  * Optional
  * GEMINI_API_KEY=*'your_api_key_here'*

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

## Examples

### Basic usage
<pre>
Mysql [hopot] SQL> show tables
+-----------+
| Tables_in_hopot |
+-----------+
| fakepages |
| requests  |
+-----------+
2 rows in set (0.001 sec)
Mysql [hopot] SQL> desc requests
+-----------------+------------------+-----+-----+---------------------+----------------+
| Field           | Type             | Null | Key | Default             | Extra          |
+-----------------+------------------+-----+-----+---------------------+----------------+
| id              | int(10) unsigned | NO  | PRI | None                | auto_increment |
| timestamp       | timestamp        | NO  | MUL | current_timestamp() |                |
| remote_ip       | varchar(45)      | NO  | MUL | None                |                |
| request_method  | varchar(10)      | NO  |     | None                |                |
| request_uri     | varchar(255)     | NO  | MUL | None                |                |
| user_agent      | text             | YES |     | None                |                |
| referer         | text             | YES |     | None                |                |
| request_headers | text             | YES |     | None                |                |
| request_body    | text             | YES |     | None                |                |
| response_code   | int(11)          | YES |     | None                |                |
+-----------------+------------------+-----+-----+---------------------+----------------+
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
+-----------+
| Tables_in_hopot |
+-----------+
| fakepages |
| requests  |
+-----------+
</pre>


### Using Gemini to create the SQL queries for you
<pre>
Mysql [hopot] SQL> translate how many rows are there in the table requests ?
 Running: SELECT COUNT(*) FROM requests; 
+----+
| COUNT(*) |
+----+
| 40 |
+----+
1 rows in set (0.010 sec)</pre>

<pre>
Mysql [hopot] SQL> translate using the table requests, please tell me which is the most popular 10 user_agents in the last 24 hours, show the frequency and sort in reverse order of freq
                   uency
 
 Running: SELECT user_agent, COUNT(*) AS frequency FROM requests WHERE timestamp >= NOW() - INTERVAL 1 DAY GROUP BY user_agent ORDER BY frequency DESC LIMIT 10; 
+----------------------------------------------------------------------------------------------------------------------------------------------------------+----+
| user_agent                                                                                                                                               | frequency |
+----------------------------------------------------------------------------------------------------------------------------------------------------------+----+
| Go-http-client/1.1                                                                                                                                       | 30 |
| Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36                                      | 9  |
| Mozlila/5.0 (Linux; Android 7.0; SM-G892A Bulid/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/60.0.3112.107 Moblie Safari/537.36 | 3  |
| Mozilla/5.0 (l9scan/2.0.134313e25373e2830323e25333; +https://leakix.net)                                                                                 | 2  |
| Mozilla/5.0 (X11; CrOS x86_64 14816.131.5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36                                         | 1  |
| ALittle Client                                                                                                                                           | 1  |
| Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0                                                                           | 1  |
| Mozilla/5.0                                                                                                                                              | 1  |
| Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0                                                                       | 1  |
| Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36                                          | 1  |
+----------------------------------------------------------------------------------------------------------------------------------------------------------+----+
</pre>
<pre>
Mysql [hopot] SQL> translate using the table requests, please tell me which is the most popular 10 IP addresses in the last 24 hours, show the frequency and sort in reverse order of fre
                   quency
 
 Running: SELECT remote_ip, COUNT(*) AS frequency FROM requests WHERE timestamp >= NOW() - INTERVAL 1 DAY GROUP BY remote_ip ORDER BY frequency DESC LIMIT 10; 
+-----------------+----+
| remote_ip       | frequency |
+-----------------+----+
| 138.68.82.23    | 16 |
| 159.203.96.42   | 16 |
| 3.236.6.49      | 9  |
| 13.37.233.235   | 2  |
| 147.182.231.184 | 2  |
| 23.150.248.224  | 2  |
| 195.26.242.224  | 1  |
| 194.38.23.16    | 1  |
| 41.249.72.163   | 1  |
| 45.61.161.77    | 1  |
+-----------------+----+
</pre>


