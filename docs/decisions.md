# Design decisions

Why the prototype differs from the original design, and what we learned on the bench.

| # | Decision | Why |
|---|---|---|
| 1 | **Zigbee (802.15.4) → ESP-NOW** for every radio link | The ESP32-S3 has no 802.15.4 radio — the first repeater build failed to link (`undefined reference to esp_ieee802154_enable`). ESP-NOW runs on every ESP32 (S3 and C6), needs no pairing or router, and shares the 2.4 GHz band with the Wi-Fi hotspot. |
| 2 | **UWB → step + gyro dead reckoning** for location | UWB modules (DWM3000) cost about ₹2,000 per worker and per anchor. Dead reckoning with the MPU6050, corrected by tunnel map matching and repeater check-points, gives a live position for almost no extra cost. UWB stays in future scope. |
| 3 | **LoRa backbone → ESP-NOW chain** | Short demo tunnels do not need LoRa range; a self-forming ESP-NOW chain is cheaper and simpler. LoRa remains the upgrade for long tunnels. |
| 4 | **UHF RFID portal → NFC (NTAG215) tags + entry station** | A UHF fixed reader costs about ₹28,000; a PN532 / RC522 reader on a XIAO ESP32-C6 costs a few hundred rupees and proves the same idea (UID registry + tag text). |
| 5 | **Raspberry Pi edge AI → laptop AI** | The admin laptop already runs the hub; YOLOv8 pose + PPE models run there with the phone as the camera. |
| 6 | **MLX90614 → DS18B20 probe** for body temperature | Contact probe is cheaper and was available; same alarm logic. |
| 7 | **AHT25 / BMP280 → BMP180** | BMP180 was available; gives pressure (height / depth) and air temperature. |
| 8 | **Gas sensor on repeaters, not on the body** | MQ heaters draw a lot of current and get hot — wrong for a battery wearable. |
| 9 | **Main repeater finds the laptop by itself** | Android hotspots pick a new subnet when restarted (10.118.42.x → 10.180.64.x); the repeater now scans the subnet for the hub after 3 failed posts. |
| 10 | **Gas alarms relative to clean air** | A new MQ sensor read ~2.4 V in clean air and tripped the fixed 1.8 V / 2.5 V alarms. Alarms now use the learned clean-air level, and only the gases a sensor is built for raise the automatic alert. |
| 11 | **Phone test page on every repeater** | Lets any phone act as a worker (fall, SOS, walking on the map) so the whole chain can be tested before the body unit is finished. |
| 12 | **External antenna on the repeater, not the body** | The antenna improves the link equally from either end, but on a repeater it helps every worker and the repeater-to-repeater link. Only the XIAO ESP32-C6 has an antenna socket. |
| 13 | **ESP-NOW kept for the V3 prototype; Zigbee later (V4)** | Zigbee (802.15.4) gives ~7 dB more link budget per hop and a standard mesh (as in the CSIR-CIMFR system, routers every 50–80 m), but only ESP32-C6/H2 have the radio — the ESP32-S3 body unit cannot. The CC2530 module has no PA (+4.5 dBm), so it would *reduce* range. Plan: move body + repeaters to C6 Zigbee (or S3 + C6 radio bridge) after the prototype review. |
| 14 | **Camera on the entry station (XIAO ESP32-S3 Sense)** | The worker no longer needs someone with a phone: tap tags, press PHOTO, the station sends the photo + tags to the hub for the AI kit check. The phone page stays as a backup. |
