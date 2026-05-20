# lamplight-django
os-level dependencies
`apk add python3 py3-pip py3-virtualenv git build-base python3-dev rust cargo libffi-dev certbot certbot-nginx nginx sqlite pkgconfig redis sudo`

## virtual env
```
python3.12 -m venv .venv
. .venv/bin/activate
pip install pip-tools
```

## Nginx Config(s)
- `etc/nginx/http.d/default.conf`

```
server {
	listen 80 default_server;
	listen [::]:80 default_server;
	root /var/www/html;
	index index.html;

	location / {
		try_files $uri $uri/ /index.html;
	}

	location /lamplight/ {
		alias /var/www/lamplight-react/dist/;
		try_files $uri $uri/ /lamplight/index.html;
	}

	location = /lamplight {
		return 301 /lamplight/;
	}

	location /ll {
		proxy_pass http://django;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_redirect off;
	}
}
```

Reload nginx with:
`rc-service nginx reload`

## Granian

```
/etc/init.d/granian
chmod +x /etc/init.d/granian

/etc/conf.d/granian (for exporting secret env vars)
```

```
export DJANGO_SETTINGS_MODULE="lamplight.settings"
export SECRET_KEY="____________"
export DJANGO_DEBUG="0"
export WHOOSH_INDEX_PATH=/var/lib/lamplight/whoosh
```

```
rc-update add granian default
rc-service granian start
```

## view error logs
`tail -f /var/log/granian/granian.err`

## Deploying python change(s)
Granian provides a socket that launches the application's asgi.  Therefore, we need to reload the project:
`rc-service granian restart`
