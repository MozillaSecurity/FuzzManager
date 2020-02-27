[![Task Status](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/FuzzManager/master/badge.svg)](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/FuzzManager/master/latest)
[![codecov](https://codecov.io/gh/MozillaSecurity/FuzzManager/branch/master/graph/badge.svg)](https://codecov.io/gh/MozillaSecurity/FuzzManager)
[![Matrix](https://img.shields.io/badge/dynamic/json?color=green&label=chat&query=%24.chunk[%3F(%40.canonical_alias%3D%3D%22%23fuzzing%3Amozilla.org%22)].num_joined_members&suffix=%20users&url=https%3A%2F%2Fmozilla.modular.im%2F_matrix%2Fclient%2Fr0%2FpublicRooms&style=flat&logo=matrix)](https://riot.im/app/#/room/#fuzzing:mozilla.org)

# What is FuzzManager

With this project, we aim to create a management toolchain for fuzzing. Unlike
other toolchains and frameworks, we want to be modular in such a way that you
can use those parts of FuzzManager that seem interesting to you without forcing
a process upon you that does not fit your requirements.

## CrashManager

CrashManager is the part of FuzzManager responsible for managing crash results
submitted to the server. The main features are:

* Store crash information gathered from various sources. See FTB.

* Bucket crashes using flexible, human-readable signatures that can match a
large number of symptoms of a crash, are proposed by the server but can be
altered and tuned by the user. The server also includes semi-automatic
optimization of signatures that helps you group duplicates into one bucket.

* Report bugs directly to a bug tracker using the best testcase available. We
support only Bugzilla as a bugtracker right now, but again the API is designed
to be extendable.

### FTB

FTB (Fuzzing Tool Box) is the underlying library that contains classes for parsing
crash output from various tools (CrashInfo), bucketing crashes (CrashSignature), and
parsing assertions (AssertionHelper). This can be used locally without having a
running FuzzManager server instance to support crash logging and bucketing. FTB already
supports a variety of tools like GDB, ASan and Minidumps but can be extended to support
any form of crash information you would like.

### Collector

Collector is a command-line utility or a Python class that can be used to communicate
with a CrashManager server.  Collector provides an easy client interface that allows
your clients to submit crashes as well as download and match existing signatures to
avoid reporting frequent issues repeatedly.

## EC2SpotManager

EC2SpotManager is another (optional) part of FuzzManager that allows you to
manage large pools of spot instances in the Amazon Cloud. It supports hierachical
configurations to avoid configuration duplication and ensures that your
instances are always running in the desired quantity as well as in the cheapest
zone.

# Questions

Please send any questions regarding the project to choller-at-mozilla-dot-com.


# Getting Started

## Client Setup

The client portion of FuzzManager (FTB and Collector) can be installed with
`pip install FuzzManager`. This is all you need if you just need to talk to a
FuzzManager server instance or use FTB locally.

## Server Setup

The server part of FuzzManager is a Django application. Please note that it
requires the full repository to be checked out, not just the server directory.

Server dependencies are listed in `server/requirements.txt`. You can use pip to install
these dependencies using `pip install -r server/requirements.txt` and/or you can
use your distribution's package management to fulfill them. A [Redis](https://redis.io/)
server is also required for EC2SpotManager, and can be installed on a Debian-based Linux
with: `sudo apt-get install redis-server`.

You can set the server up just like any other Django project. The Django
configuration file is found at `server/server/settings.py`. The default will
work, but for a production setup, you should at least review the database
settings.

Afterwards, you should run the following commands

```
$ cd server
$ python manage.py migrate
```

Create the fuzzmanager user.
```
$ python ./manage.py createsuperuser
Username (leave blank to use 'user'): fuzzmanager
Email address: fuzzmanager@internal.com
Password:
Password (again):
Superuser created successfully.
```
Get fuzzmanager authorization token
```
$ python manage.py get_auth_token fuzzmanager
4a253efa90f514bd89ae9a86d1dc264aa3133945
```
Since the fuzzmanager account is used as a service account, we need to set the http basic authentication password to the auth token.
```
htpasswd -cb .htpasswd fuzzmanager 4a253efa90f514bd89ae9a86d1dc264aa3133945`
```
This .htpasswd file can be stored anywhere on your hard drive.
Your Apache AuthUserFile line should be updated to reflect your path.
See examples/apache2/default.vhost for an example

### Important changes in settings.py
It is important that you edit FuzzManager/server/settings.py and adjust the following variables according to your needs.

    ALLOWED_HOSTS = []

See [ALLOWED_HOSTS documentation](https://docs.djangoproject.com/en/1.11/ref/settings/#allowed-hosts)


You may also want to increase the maximum size in bytes allowed in a request body. The default of 2.5MB may not be enough
in some cases by adding the following variable.

    DATA_UPLOAD_MAX_MEMORY_SIZE = <YOUR VALUE HERE>

See [DATA_UPLOAD_MAX_MEMORY_SIZE](https://docs.djangoproject.com/en/1.11/ref/settings/#data-upload-max-memory-size)

### Local testing

For local testing, you can use the builtin debug webserver:

`python manage.py runserver`

For a production setup, see the next section about Apache+WSGI.

### Using Apache+WSGI for a production setup

To properly run FuzzManager in a production setup, using Apache+WSGI is the
recommended way.

In the `examples/apache2/` directory you'll find an example vhost file that
shows you how to run FuzzManager in an Apache+WSGI setup. Of course you should
adjust the configuration to use HTTPs if you don't plan to use any sort of
TLS load balancer in front of it.

### Getting/Creating the authentication token for clients

Use the following command to get an authentication token for a Django user:

`python manage.py get_auth_token username`

You can use the user that you created during `syncdb` for simple setups.

### Server Cronjobs

The following is an example crontab using `cronic` to run several important
FuzzManager jobs:

```
# Fetch the status of all bugs from our external bug tracker(s)
*/15 * * * * cd /path/to/FuzzManager/server && cronic python manage.py bug_update_status
# Cleanup old crash entries and signatures according to configuration
*/30 * * * * cd /path/to/FuzzManager/server && cronic python manage.py cleanup_old_crashes
# Attempt to fit recently added crash entries into existing buckets
*/5  * * * * cd /path/to/FuzzManager/server && cronic python manage.py triage_new_crashes
# Export all signatures to a zip file for downloading by clients
*/30 * * * * cd /path/to/FuzzManager/server && cronic python manage.py export_signatures files/signatures.new.zip mv files/signatures.new.zip files/signatures.zip
```

## Client Usage

In order to talk to FuzzManager, your fuzzer should use the client interface provided, called the Collector. It can be used as a standalone command line tool or directly as a Python class in case your fuzzer is written in Python.

We'll first describe how to use the class interface directly from Python. If you want to use the command line interface instead, I still suggest that you read on because the command line interface is very similar to the class interface in terms of functionality and configuration.

For simple cases where you can just (re)run a command with a testcase that produces a crash, we also provide an easy report class that runs your command and figures out all the crash information on its own. You will find the description of this mode at the end of this section as it still requires configuration files to be setup properly, but tl;dr, it can be as easy as:

`$ python Collector.py --autosubmit mybadprogram --someopt yourtest`

And you're done submitting everything, crash information as well as program information.

### Constructing the Collector instance

The Collector constructor takes various arguments that are required for later operations. These arguments include a directory for signatures, server data such as hostname, port, etc. as well as authentication data and a client name. However, the preferred way to pass these options is not through the constructor, but through a configuration file. The constructor will try to read the configuration file located at ~/.fuzzmanagerconf and use any parameters from there if it hasn't been explicitly specified in the constructor call. This makes deployment very easy and saves time. An example configuration could look like this:

```
[Main]
sigdir = /home/example/signatures
serverhost = 127.0.0.1
serverport = 8000
serverproto = http
serverauthtoken = 4a253efa90f514bd89ae9a86d1dc264aa3133945
```

With this file present and readable, instantiating the Collector doesn't require any further arguments.


#### Creating the CrashInfo

Several methods of the collector work with the `CrashInfo` class. This class stores all the necessary data about a crash. In order to get a CrashInfo instance, you need:

* A variable containing the stdout output of your program
* A variable containing the stderr output of your program
* A variable containing crash information as outputted by GDB or AddressSanitizer
* A ProgramConfiguration instance

The first three sets of data are typically already available in a fuzzer. Note that for GDB traces, the trace should contain first the stack trace, then a dump of all registers and then a dissassembly of the program counter (see also the FTB/Running/AutoRunner.py file which demonstrates how to output all information properly for FuzzManager).

The last thing required is the `ProgramConfiguration`. This class is largely a container class storing various properties of the program, e.g. product name, the platform, version and runtime options. Instead of instantiating the class and providing all the data manually, it is again recommended to use the configuration file support. Assuming your binary is located at /home/example/foo then creating a configuration file at /home/example/foo.fuzzmanagerconf with the necessary data is recommended. Such a file could look like this:

```
[Main]
platform = x86
product = mozilla-central
product_version = 70de2960aa87
os = linux

[Metadata]
pathPrefix = /srv/repos/mozilla-central/
buildFlags = --enable-optimize --enable-posix-nspr-emulation --enable-valgrind --enable-gczeal --target=i686-pc-linux-gnu --disable-tests --enable-debug
```

Once this file is present, you can call `ProgramConfiguration.fromBinary` with your binary path and the configuration will be created from the file. You can add program arguments and environment variables through the provided `addProgramArguments` and `addEnvironmentVariables` methods afterwards. Finally, call `CrashInfo.fromRawCrashData` with all of the described data. Here's a simple example:

```
    # Note: This could fail and return None when the configuration is missing or throw if misconfigured
    configuration = ProgramConfiguration.fromBinary(opts.binary)
    configuration.addEnvironmentVariables(env)
    configuration.addProgramArguments(args)
    crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, configuration, auxCrashData=crashdata)
```

### Refreshing Signatures

Calling the `refresh` method of our Collector instance will download a zipfile from the server, containing the signatures and metadata exported by the server. Once the download is complete, the Collector will first delete *all* signatures including their metadata from the signature directory. Then the downloaded zipfile is extracted.

### Searching Signatures

The `search` method is the first of a few methods requiring a `crashInfo` variable. Create it as described above and the Collector will search inside the signature directory for any matching signatures. Upon match, it will return a tuple containing the filename of the signature matching as well as a metadata object corresponding to that signature.

### Submitting Crashes

The `submit` method can be used to send a crash report to the FuzzManager server. Again the `crashInfo` parameter works as described above. In addition, you can provide a file containing a test and an optional "quality" indicator of the test (best quality is 0). The use of this quality indicator largely depends on how your fuzzer/reducer works. The server will prefer better qualities when proposing test cases for filing bugs. Finally, the method accepts an additional metadata parameter which can contain arbitrary information that is stored with the crash on the server. Note that this metadata is *combined* with the metadata found in the `ProgramConfiguration` of the `crashInfo`. When using binary configuration files, this means that the metadata supplied in that configuration file is automatically submitted with the crash to the server.

### Further methods

Further methods of the Collector include `generate` for generating signatures locally and `download` for downloading testcases from the server. Both methods work as documented in the source code and are only useful in special cases depending on the application scenario.a

### Using the automated submit method

If your crashes can be reproduced on the command line by just running a command with your testcase, then you can use the automated submit method (`--autosubmit` in the command line client) and just pass the failing command line to the client. The client will automatically run the target program, gather crash and program configuration and submit it to the server. Of course this mode requires that both the global configuration file as well as the binary configuration file are present.

## Web Interface Usage and Workflow

TBD
