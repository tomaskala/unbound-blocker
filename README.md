# unbound-blocker

A script that fetches blocklists in the hosts file format from a specified list 
and feeds them to a running unbound(8) instance using unbound-control(8). 
Supports an optional whitelist of domains that should never be blocked.

## Example

Install the package.
```
$ pip install .
```

Create a file with one blocklist source per line. Empty lines are ignored, 
strings starting with `#` are discarded.
```
$ cat blocklist-sources.txt
https://someonewhocares.org/hosts/hosts
https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-gambling/hosts
```

Create a file with one whitelisted domain per line.
```
$ cat whitelist.txt
s.youtube.com
signal.org
```

Run the script.
```
$ fetch_blocklist ./blocklist-sources.txt -w ./whitelist.txt
```

Optionally specify the path to unbound-control(8).
```
$ fetch_blocklist ./blocklist-sources.txt -w ./whitelist.txt -u /usr/sbin/unbound-control
```
