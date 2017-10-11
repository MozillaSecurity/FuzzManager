## fuzzmanager_setup_helper.py
The fuzzmanager_setup_helper.py will perform the following:
* `python manage.py migrate`
* create fuzzmanager super user account
* Obtain fuzzmanager auth_token
* Create .htpasswd file and create fuzzmanager user account with auth_token as password 
* Create .fuzzmanagerconf file
* Prompt you to create additional regular and super user accounts as desired.

Example run:
```bash
 python ./fuzzmanager_setup_helper.py 
[+] Performing python manage.py migrate
Operations to perform:
  Synchronize unmigrated apps: rest_framework, chartjs
  Apply all migrations: authtoken, sessions, admin, ec2spotmanager, auth, contenttypes, crashmanager, covmanager
Synchronizing apps without migrations:
  Creating tables...
  Installing custom SQL...
  Installing indexes...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying authtoken.0001_initial... OK
  Applying crashmanager.0001_initial... OK
  Applying crashmanager.0002_bugzillatemplate_security... OK
  Applying crashmanager.0003_bucket_frequent... OK
  Applying crashmanager.0004_add_tool... OK
  Applying crashmanager.0005_add_user... OK
  Applying crashmanager.0006_user_defaultproviderid... OK
  Applying crashmanager.0007_bugzillatemplate_comment... OK
  Applying crashmanager.0008_crashentry_crashaddressnumeric... OK
  Applying crashmanager.0009_copy_crashaddress... OK
  Applying crashmanager.0010_bugzillatemplate_security_group... OK
  Applying crashmanager.0011_bucket_permanent... OK
  Applying crashmanager.0012_crashentry_cachedcrashinfo... OK
  Applying crashmanager.0013_init_cachedcrashinfo... OK
  Applying crashmanager.0014_bugzillatemplate_testcase_filename... OK
  Applying crashmanager.0015_crashentry_triagedonce... OK
  Applying crashmanager.0016_auto_20160308_1500... OK
  Applying crashmanager.0017_user_restricted... OK
  Applying crashmanager.0018_auto_20170620_1503... OK
  Applying covmanager.0001_initial... OK
  Applying ec2spotmanager.0001_initial... OK
  Applying ec2spotmanager.0002_instancestatusentry_poolstatusentry... OK
  Applying ec2spotmanager.0003_auto_20150505_1225... OK
  Applying ec2spotmanager.0004_auto_20150507_1311... OK
  Applying ec2spotmanager.0005_auto_20150520_1517... OK
  Applying ec2spotmanager.0006_auto_20150625_2050... OK
  Applying sessions.0001_initial... OK

[+] Creating fuzzmanager user account.
[+] Super user fuzzmanager created
[+] Obtaining auth token for fuzzmanager
[+] Creating .fuzzmanagerconf
Enter the the path to store fuzzmanager signatures. /home/example/signatures would be a good choice.
/home/example/signatures
Enter the IP Address for the fuzzmanager host or to accept 127.0.0.1, press ENTER

Enter the TCP port for fuzzmanager or to accept 8000, press ENTER

Type https to use https protocol or to accept http, press ENTER

[Main]
sigdir = /home/example/signatures
serverhost = 127.0.0.1
serverport = 8000
serverproto = http
serverauthtoken = 4a253efa90f514bd89ae9a86d1dc264aa3133945
tool = jsfunfuzz

[+] The fuzzmanager account password has been set to the auth_token 4a253efa90f514bd89ae9a86d1dc264aa3133945
Adding password for user fuzzmanager

[+] .htpasswd created for apache basic authentication with the fuzzmanager user password set to 81bd6220b2d7b038781010d1a463c6f0470e31e1
Update the AuthUserFile path/to/.htpasswd line as shown in examples/apache2/default.vhost to point to this file
Please enter a user account to create, or ENTER to quit

```
