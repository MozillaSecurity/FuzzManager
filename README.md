[![Task Status](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/WebCompatManager/master/badge.svg)](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/WebCompatManager/master/latest)
[![codecov](https://codecov.io/gh/MozillaSecurity/WebCompatManager/branch/master/graph/badge.svg)](https://codecov.io/gh/MozillaSecurity/WebCompatManager)
[![Matrix](https://img.shields.io/badge/dynamic/json?color=green&label=chat&query=%24.chunk[%3F(%40.canonical_alias%3D%3D%22%23fuzzing%3Amozilla.org%22)].num_joined_members&suffix=%20users&url=https%3A%2F%2Fmozilla.modular.im%2F_matrix%2Fclient%2Fr0%2FpublicRooms&style=flat&logo=matrix)](https://riot.im/app/#/room/#fuzzing:mozilla.org)

# What is WebCompatManager

With this project, we aim to create a management toolchain for fuzzing. Unlike
other toolchains and frameworks, we want to be modular in such a way that you
can use those parts of WebCompatManager that seem interesting to you without forcing
a process upon you that does not fit your requirements.

## ReportManager

ReportManager is the part of WebCompatManager responsible for managing report results
submitted to the server. The main features are:

* Store report information gathered from various sources. See FTB.

* Bucket reports using flexible, human-readable signatures that can match a
large number of symptoms of a report, are proposed by the server but can be
altered and tuned by the user. The server also includes semi-automatic
optimization of signatures that helps you group duplicates into one bucket.

* Report bugs directly to a bug tracker using the best testcase available. We
support only Bugzilla as a bugtracker right now, but again the API is designed
to be extendable.

### FTB

FTB (Fuzzing Tool Box) is the underlying library that contains classes for parsing
report output from various tools (ReportInfo), bucketing reports (ReportSignature), and
parsing assertions (AssertionHelper). This can be used locally without having a
running WebCompatManager server instance to support report logging and bucketing. FTB already
supports a variety of tools like GDB, ASan and Minidumps but can be extended to support
any form of report information you would like.

### Collector

Collector is a command-line utility or a Python class that can be used to communicate
with a ReportManager server.  Collector provides an easy client interface that allows
your clients to submit reports as well as download and match existing signatures to
avoid reporting frequent issues repeatedly.

# Questions

Please send any questions regarding the project to choller-at-mozilla-dot-com.


# Getting Started

## Client Setup

The client portion of WebCompatManager (FTB and Collector) can be installed with
`pip install WebCompatManager`. This is all you need if you just need to talk to a
WebCompatManager server instance or use FTB locally.

## Server Setup

The server part of WebCompatManager is a Django application. Please note that it
requires the full repository to be checked out, not just the server directory.

Dependency constraints are listed in [requirements.txt](requirements.txt). You can ask pip to respect these contraints by installing WebCompatManager using:

```pip install -c requirements.txt '.[server]'```

A [Redis](https://redis.io/) server is also required, and can be installed on a Debian-based Linux
with: 

```sudo apt-get install redis-server```

You can set the server up just like any other Django project. The Django
configuration file is found at `server/server/settings.py`. The default will
work, but for a production setup, you should at least review the database
settings.

Afterward, you should run the following commands

```
$ cd server
$ python manage.py migrate
$ cd frontend
$ npm install
$ npm run build
$ cd ..
```

Create the webcompatmanager user.
```
$ python manage.py createsuperuser
Username (leave blank to use 'user'): webcompatmanager
Email address: webcompatmanager@internal.com
Password:
Password (again):
Superuser created successfully.
```
Get webcompatmanager authorization token
```
$ python manage.py get_auth_token webcompatmanager
4a253efa90f514bd89ae9a86d1dc264aa3133945
```
Since the webcompatmanager account is used as a service account, we need to set the http basic authentication password to the auth token.
```
htpasswd -cb .htpasswd webcompatmanager 4a253efa90f514bd89ae9a86d1dc264aa3133945`
```
This .htpasswd file can be stored anywhere on your hard drive.
Your Apache AuthUserFile line should be updated to reflect your path.
See examples/apache2/default.vhost for an example

### Important changes in settings.py
It is important that you edit WebCompatManager/server/settings.py and adjust the following variables according to your needs.

    ALLOWED_HOSTS = ['host']
    CSRF_TRUSTED_ORIGINS = ['scheme://host']

See [ALLOWED_HOSTS](https://docs.djangoproject.com/en/4.1/ref/settings/#allowed-hosts) and [CSRF_TRUSTED_ORIGINS](https://docs.djangoproject.com/en/4.1/ref/settings/#csrf-trusted-origins) documentation.


You may also want to increase the maximum size in bytes allowed in a request body. The default of 2.5MB may not be enough
in some cases by adding the following variable.

    DATA_UPLOAD_MAX_MEMORY_SIZE = <YOUR VALUE HERE>

See [DATA_UPLOAD_MAX_MEMORY_SIZE](https://docs.djangoproject.com/en/4.1/ref/settings/#data-upload-max-memory-size)

### Local testing

For local testing, you can use the builtin debug webserver:

`python manage.py runserver`

For a production setup, see the next section about Apache+WSGI.

### Using Apache+WSGI for a production setup

To properly run WebCompatManager in a production setup, using Apache+WSGI is the
recommended way.

In the `examples/apache2/` directory you'll find an example vhost file that
shows you how to run WebCompatManager in an Apache+WSGI setup. You should
adjust the configuration to use HTTPs if you don't plan to use any sort of
TLS load balancer in front of it.

### Getting/Creating the authentication token for clients

Use the following command to get an authentication token for a Django user:

`python manage.py get_auth_token username`

You can use the user that you created during `syncdb` for simple setups.

### Server Cronjobs

The following is an example crontab using `cronic` to run several important
WebCompatManager jobs:

```
# Fetch the status of all bugs from our external bug tracker(s)
*/15 * * * * cd /path/to/WebCompatManager/server && cronic python manage.py bug_update_status
# Cleanup old report entries and signatures according to configuration
*/30 * * * * cd /path/to/WebCompatManager/server && cronic python manage.py cleanup_old_reports
# Attempt to fit recently added report entries into existing buckets
*/5  * * * * cd /path/to/WebCompatManager/server && cronic python manage.py triage_new_reports
# Export all signatures to a zip file for downloading by clients
*/30 * * * * cd /path/to/WebCompatManager/server && cronic python manage.py export_signatures files/signatures.new.zip mv files/signatures.new.zip files/signatures.zip
```

### Run server with Docker

A docker image is available by building the `Dockerfile`.

You can easily run a local server (and Mysql database server) by using [docker-composer](https://docs.docker.com/compose/):

```console
docker compose up
```

On a first run, you must execute the database migrations:

```console
docker compose exec backend python manage.py migrate
```

And create a superuser to be able to log in on http://localhost:8000

```console
docker compose exec backend python manage.py createsuperuser
```

By default, the docker image uses Django settings set in Python module `server.settings_docker`, with the following settings:
- `DEBUG = False` to enable production mode
- `ALLOWED_HOSTS = ["localhost", ]` to allow development usage on `http://localhost:8000`

You can customize settings by mounting a file from your host into the container:

```yaml
volumes:
  - "./settings_docker.py:/src/server/server/settings_docker.py:ro"
```

## Client Usage

In order to talk to WebCompatManager, your fuzzer should use the client interface provided, called the Collector. It can be used as a standalone command line tool or directly as a Python class in case your fuzzer is written in Python.

We'll first describe how to use the class interface directly from Python. If you want to use the command line interface instead, I still suggest that you read on because the command line interface is very similar to the class interface in terms of functionality and configuration.

For simple cases where you can just (re)run a command with a testcase that produces a report, we also provide an easy report class that runs your command and figures out all the report information on its own. You will find the description of this mode at the end of this section as it still requires configuration files to be setup properly, but tl;dr, it can be as easy as:

`$ python Collector.py --autosubmit mybadprogram --someopt yourtest`

And you're done submitting everything, report information as well as program information.

### Constructing the Collector instance

The Collector constructor takes various arguments that are required for later operations. These arguments include a directory for signatures, server data such as hostname, port, etc. as well as authentication data and a client name. However, the preferred way to pass these options is not through the constructor, but through a configuration file. The constructor will try to read the configuration file located at ~/.webcompatmanagerconf and use any parameters from there if it hasn't been explicitly specified in the constructor call. This makes deployment very easy and saves time. An example configuration could look like this:

```
[Main]
sigdir = /home/example/signatures
serverhost = 127.0.0.1
serverport = 8000
serverproto = http
serverauthtoken = 4a253efa90f514bd89ae9a86d1dc264aa3133945
```

With this file present and readable, instantiating the Collector doesn't require any further arguments.


#### Creating the ReportInfo

Several methods of the collector work with the `ReportInfo` class. This class stores all the necessary data about a report. In order to get a ReportInfo instance, you need:

* A variable containing the stdout output of your program
* A variable containing the stderr output of your program
* A variable containing report information as outputted by GDB or AddressSanitizer
* A ProgramConfiguration instance

The first three sets of data are typically already available in a fuzzer. Note that for GDB traces, the trace should contain first the stack trace, then a dump of all registers and then a dissassembly of the program counter (see also the FTB/Running/AutoRunner.py file which demonstrates how to output all information properly for WebCompatManager).

The last thing required is the `ProgramConfiguration`. This class is largely a container class storing various properties of the program, e.g. product name, the platform, version and runtime options. Instead of instantiating the class and providing all the data manually, it is again recommended to use the configuration file support. Assuming your binary is located at /home/example/foo then creating a configuration file at /home/example/foo.webcompatmanagerconf with the necessary data is recommended. Such a file could look like this:

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

Once this file is present, you can call `ProgramConfiguration.fromBinary` with your binary path and the configuration will be created from the file. You can add program arguments and environment variables through the provided `addProgramArguments` and `addEnvironmentVariables` methods afterward. Finally, call `ReportInfo.fromRawReportData` with all the described data. Here's a simple example:

```
    # Note: This could fail and return None when the configuration is missing or throw if misconfigured
    configuration = ProgramConfiguration.fromBinary(opts.binary)
    configuration.addEnvironmentVariables(env)
    configuration.addProgramArguments(args)
    reportInfo = ReportInfo.fromRawReportData(stdout, stderr, configuration, auxReportData=reportdata)
```

### Refreshing Signatures

Calling the `refresh` method of our Collector instance will download a zipfile from the server, containing the signatures and metadata exported by the server. Once the download is complete, the Collector will first delete *all* signatures including their metadata from the signature directory. Then the downloaded zipfile is extracted.

### Searching Signatures

The `search` method is the first of a few methods requiring a `reportInfo` variable. Create it as described above and the Collector will search inside the signature directory for any matching signatures. Upon match, it will return a tuple containing the filename of the signature matching as well as a metadata object corresponding to that signature.

### Submitting Reports

The `submit` method can be used to send a report report to the WebCompatManager server. Again the `reportInfo` parameter works as described above. In addition, you can provide a file containing a test and an optional "quality" indicator of the test (the best quality is 0). The use of this quality indicator largely depends on how your fuzzer/reducer works. The server will prefer better qualities when proposing test cases for filing bugs. Finally, the method accepts an additional metadata parameter which can contain arbitrary information that is stored with the report on the server. Note that this metadata is *combined* with the metadata found in the `ProgramConfiguration` of the `reportInfo`. When using binary configuration files, this means that the metadata supplied in that configuration file is automatically submitted with the report to the server.

### Further methods

Further methods of the Collector include `generate` for generating signatures locally and `download` for downloading testcases from the server. Both methods work as documented in the source code and are only useful in special cases depending on the application scenario.a

### Using the automated submit method

If your reports can be reproduced on the command line by just running a command with your testcase, then you can use the automated submit method (`--autosubmit` in the command line client) and just pass the failing command line to the client. The client will automatically run the target program, gather report and program configuration and submit it to the server. Of course this mode requires that both the global configuration file and the binary configuration file are present.

## Web Interface Usage and Workflow

TBD
