FROM openresty/openresty:alpine
RUN apk add --no-cache wget \
    && mkdir -p /usr/local/openresty/lualib/resty \
    && wget -q -O /usr/local/openresty/lualib/resty/prometheus.lua \
       https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus.lua \
    && wget -q -O /usr/local/openresty/lualib/prometheus_resty_counter.lua \
       https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus_resty_counter.lua \
    && wget -q -O /usr/local/openresty/lualib/prometheus_keys.lua \
       https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus_keys.lua
