set -e
cp /mnt/conf/nginx.conf /etc/nginx/
nginx -g 'daemon off;'