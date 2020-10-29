###  hass tinymu toiletlid
copy toiletlid or xiaomi_toiletlid to $hass/.homeassistant/custom_components


Hassos:
```
cat << EOF >> /config/configuration.yaml 

toiletlid:
  - platform: xiaomi_toiletlid
    name: iot-toiletlid
    host: <ip>
    token: xxxxxxxxxxxxxxxxxxxxxxx
EOF

wget https://github.com/scp10011/xiaomi_toiletlid/releases/download/v0.1-0.114/xiaomi_toiletlid.tar -O - | tar x -C /config/custom_components/
chown root:root /config/custom_components/{toiletlid,xiaomi_toiletlid}

ha core restart

```


