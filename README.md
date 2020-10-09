# Hass Amplifi

A sensor hass integration that allows you to monitor devices connected to Amplifi on Wifi (LAN in progress).

You can use this addon to perform the following automations:
- As a presense sensor (when your mobile connects to wifi)
- Internet bandwidth usage monitor (amplifi reports data transfers on the WAN port)
- When your TV is on/off (monitoring its wifi traffic)
- Security (Create alerts for unknown devices connected to your wifi)


## Supported devices
- Amplifi HD firmware version 3.4.2

### Caveats
- When logged in the amplifi portal on your browser the current hass session is invalidated. However, the next data refresh should resuming monitoring.


### Development

Enable logging by defining the logger entry to your configuration.yaml.

```
logger:
  default: info
  logs:
    custom_components.amplifi: debug
```