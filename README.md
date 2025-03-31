# lamplight-django


## Nginx Configs
admin/conf/web/kingdomwith.in.nginx.conf
admin/conf/web/kingdomwith.in.nginx.ssl.conf

## Deploying python change(s)
Gunicorn provides a socket that launches the application's wsgi.  Therefore, we need to restart gunicorn to reload the project:
`sudo systemctl restart gunicorn`
