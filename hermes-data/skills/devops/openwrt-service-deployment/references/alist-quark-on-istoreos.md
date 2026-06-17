# Alist + Quark on iStoreOS/OpenWrt

This reference captures a practical workflow for installing/configuring Alist on an iStoreOS/OpenWrt router and mounting Quark Drive.

## Environment pattern

Observed target:
- iStoreOS/OpenWrt 22.03.x
- `aarch64` / `aarch64_generic`
- Alist installed at `/usr/bin/alist`
- Alist web UI/API on port `5244`
- UCI config may claim `data_dir='/etc/alist'`, but a hand-written init script can still start Alist without `--data`, causing Alist to use a relative `data` directory based on the process cwd.

## Discovery commands

Run these before changing anything:

```sh
uname -a
cat /etc/os-release 2>/dev/null || cat /etc/openwrt_release 2>/dev/null
df -h
opkg print-architecture 2>/dev/null || true
command -v alist || true
ls /etc/init.d/alist 2>/dev/null || true
netstat -tlnp 2>/dev/null | grep -E '(:5244|alist)' || true
alist version 2>&1 || /usr/bin/alist version 2>&1
uci show alist 2>/dev/null || true
ps | grep alist | grep -v grep
```

If Alist is running:

```sh
PID=$(pidof alist)
readlink /proc/$PID/cwd
tr '\0' ' ' < /proc/$PID/cmdline; echo
find / -maxdepth 3 -name data.db 2>/dev/null
find / -maxdepth 3 -name config.json 2>/dev/null
```

## Correcting the data directory

If the process is simply `/usr/bin/alist server`, Alist may use `/root/data`, `/data`, or another relative path instead of the directory expected by LuCI/UCI.

Use a procd init script that explicitly pins the data folder:

```sh
cp /etc/init.d/alist /etc/init.d/alist.bak 2>/dev/null || true
cat > /etc/init.d/alist <<'EOF'
#!/bin/sh /etc/rc.common

START=99
STOP=10
USE_PROCD=1

start_service() {
    procd_open_instance
    procd_set_param command /usr/bin/alist server --data /etc/alist
    procd_set_param respawn
    procd_set_param stdout 1
    procd_set_param stderr 1
    procd_close_instance
}

stop_service() {
    killall alist 2>/dev/null || true
}
EOF
chmod +x /etc/init.d/alist
/etc/init.d/alist enable
/etc/init.d/alist restart
sleep 3
PID=$(pidof alist)
tr '\0' ' ' < /proc/$PID/cmdline; echo
netstat -tlnp 2>/dev/null | grep :5244
```

## Reset admin password against the correct data dir

```sh
alist admin set 'NEW_STRONG_PASSWORD' --data /etc/alist
/etc/init.d/alist restart
```

Then verify from the operator machine:

```python
import requests
base = 'http://ROUTER_IP:5244'
r = requests.post(base + '/api/auth/login', json={'username':'admin','password':'NEW_STRONG_PASSWORD'}, timeout=10)
print(r.status_code, r.text[:500])
```

If login fails after a successful `alist admin set`, re-check `/proc/$PID/cmdline`; the running service is probably using a different data directory.

## Quark driver fields

For Alist v3.45 Quark driver:
- driver name: `Quark`
- required additional fields: `cookie`, `root_folder_id`
- root folder: `0`
- common fields include `mount_path`, `cache_expiration`, `webdav_policy`, `disable_index`, `enable_sign`
- example mount path: `/quark`

Driver template can be inspected with:

```python
import requests
base='http://ROUTER_IP:5244'
token = requests.post(base+'/api/auth/login', json={'username':'admin','password':'PASSWORD'}, timeout=10).json()['data']['token']
h={'Authorization': token}
drivers = requests.get(base+'/api/admin/driver/list', headers=h, timeout=10).json()['data']
print(drivers['Quark'])
```

Storage list:

```python
requests.get(base+'/api/admin/storage/list', headers=h, timeout=10).json()
```

## Getting Quark cookies from the user

Use the full request `Cookie:` header whenever possible. Quark may keep login-critical values in HttpOnly cookies that JavaScript cannot read; an Alist Quark storage created from only `document.cookie` can initialize as `require login [guest]`.

Preferred user-facing instruction when the user is already logged into Quark Web:

1. Open `https://pan.quark.cn/list#/list/all` in the browser where Quark is logged in.
2. Open DevTools (`F12` or right-click → Inspect/检查).
3. Go to Network/网络.
4. Refresh the Quark page so requests appear.
5. Click a `pan.quark.cn` request (names like `sort`, `file`, `list`, `member`, `capacity`, or similar are fine).
6. In the right/bottom request detail pane, click Headers/标头.
7. Under Request Headers/请求标头, copy the value after `Cookie:` and paste it back to the agent.

Fallback if Network is too hard to navigate:

```js
copy(document.cookie)
```

This fallback is easier for the user, but if Alist reports `require login [guest]`, switch to the Network → Headers full `Cookie:` method.

Do not echo the full cookie in replies. Use it only to configure the local Alist storage, and delete any temporary local scripts/files that contain it after verification.

If attempting direct Chrome cookie extraction on macOS:
- Cookie DB may be at `/Users/<user>/Library/Application Support/Google/Chrome/Default/Cookies` or `Default/Network/Cookies` depending on Chrome version.
- The user’s foreground Chrome session can be probed with AppleScript to find `quark.cn` tabs and run `document.cookie`, but that still excludes HttpOnly cookies.
- Newer Chrome/macOS cookie encryption may require Keychain access and may not expose `Chrome Safe Storage`; if decryption is not straightforward, fall back to DevTools Network → Headers rather than overfitting to local browser internals.

## WebDAV / VidHub verification

For Alist, WebDAV paths use `/dav` as the root prefix. If the Quark mount path is `/夸克网盘`, clients should use one of:

```text
server: http://ROUTER_IP:5244
path: /dav/夸克网盘
username: admin
password: <alist password>
```

or a single URL:

```text
http://ROUTER_IP:5244/dav/夸克网盘
```

If the client has trouble with Chinese paths, try URL encoding or mount with an ASCII path such as `/quark`:

```text
/dav/%E5%A4%B8%E5%85%8B%E7%BD%91%E7%9B%98
```

Verify WebDAV from the operator machine before debugging the media app:

```python
import requests
from requests.auth import HTTPBasicAuth
base = 'http://ROUTER_IP:5244'
for path in ['/dav', '/dav/夸克网盘', '/dav/%E5%A4%B8%E5%85%8B%E7%BD%91%E7%9B%98']:
    r = requests.request('PROPFIND', base + path,
                         auth=HTTPBasicAuth('admin', 'PASSWORD'),
                         headers={'Depth':'1'}, timeout=20)
    print(path, r.status_code, r.text[:200])
```

Expected success is HTTP `207 Multi-Status`. If `/api/fs/list` works but WebDAV returns `403`, inspect Alist users:

```python
import requests
base = 'http://ROUTER_IP:5244'
token = requests.post(base+'/api/auth/login', json={'username':'admin','password':'PASSWORD'}, timeout=10).json()['data']['token']
h = {'Authorization': token, 'Content-Type':'application/json'}
print(requests.get(base+'/api/admin/user/list', headers=h, timeout=10).text)
```

In Alist v3, a user with `permission: 0` may be able to log into the admin API/UI but still fail WebDAV `PROPFIND` with 403. Update the user with a broad permission mask, keeping password empty so the password is not changed:

```python
payload = {
    'id': 1,
    'username': 'admin',
    'password': '',
    'base_path': '/',
    'role': 2,
    'disabled': False,
    'permission': 1023,
    'sso_id': '',
}
r = requests.post(base+'/api/admin/user/update', headers=h, json=payload, timeout=10)
print(r.status_code, r.text)
```

After updating permissions, log in again and rerun the WebDAV `PROPFIND` checks. If the media app cached the failed state, delete and recreate the source.

## Expect/SSH notes

When using `expect` to automate router SSH:
- Tcl expands `[...]` and `$()` before the remote shell sees them.
- Avoid `grep [a]list` inside a Tcl double-quoted command; use `ps | grep alist | grep -v grep` or carefully brace/quote.
- Avoid dynamic backup names like `alist.bak.$(date +%s)` in Tcl strings unless escaped; a fixed backup path is simpler.
