# FuzzManager Client Configuration Files

FuzzManager has two types of client configuration files, one for the machine
and one for the binary that is being tested. It is highly recommended to use
both as it makes the crash submit process a lot easier. However, if for some
reason you don't want to use configuration files, you can provide all the
information as well using the Python APIs.

## Machine Configuration File

The machine configuration file is typically stored in your home directory
and called `.fuzzmanagerconf`. It only has a `Main` section which may contain
the following directives:

* `sigdir` - Directory where to store downloaded/generated signatures
* `serverhost` - Server hostname/IP
* `serverport` - Server port
* `serverproto` - Server protocol (default: https), can be used to force http
* `serverauthtoken` - Server authentication token
* `serverauthtokenfile` - File containing server authentication token
* `clientid` - The ID (name) the client should use when talking to the server (default is hostname)
* `tool` - The name of the tool running on the machine

### Example

```
[Main]
sigdir = /home/example/signatures
serverhost = 127.0.0.1
serverport = 8000
serverproto = http
serverauthtoken = 4a253efa90f514bd89ae9a86d1dc264aa3133945
tool = myFuzzer
```

## Binary Configuration File

The binary configuration file should sit next to the binary that is being
tested. If your binary is `/path/to/bin` then the configuration file should be
at `/path/to/bin.fuzzmanagerconf`. Therefore, it makes sense to create the
configuration file on the fly while building your target program and automate
the process.

This configuration file also has a `Main` section which should contain the
following directives:

* `platform` - The platform this binary was built for (x86, x86-64, arm)
* `product` - Name of the product or repository
* `product_version` - A version number or version control revision
* `os` - Operating system this binary was built for (linux, windows, macosx)

In addition, it can have a `Metadata` section described below.

### Metadata Section

The `Metadata` section in the binary configuration file may contain
*arbitrary* key/value pairs. The data contained in there is submitted
with each crash that you send to the server.

While you can make free use of this section, some values in there are
interpreted by the server and/or used by other automation:

* `pathPrefix` - This is the path to your build directory. The server will
strip this value from your backtraces before reporting them to a bug tracker.

* `buildFlags` - These are the flags to build your binary. Using this field
may allow other automation to choose the right binaries for reproducing.

Metadata fields are especially powerful when you use the bug reporting
functionality in the server. Reporting templates may refer to fields in
metadata using e.g. `%metadata.buildFlags%` to load the `buildFlags` value
into the template. This allows passing custom information through the entire
reporting chain without the server having to know each of these fields.

### Example

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
