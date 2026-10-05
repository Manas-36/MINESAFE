// =====================================================================
//  MineSafe - ENTRY STATION (SCANNING SYSTEM) HARDWARE TEST
//  Checks the PN532 RFID reader + antenna, the OLED and the 3 buttons - no hub needed.
//  ESP32-C6 (DevKit or XIAO): no camera - the entry photo is taken on the phone page.
//  XIAO ESP32-S3 Sense: also tests the camera and shows a live photo in the browser.
//  Run this before flashing entry_station.ino.
//
//  Board : ESP32-C6-WROOM-1 DevKit -> "ESP32C6 Dev Module" | XIAO C6 -> "XIAO_ESP32C6"
//          (XIAO S3 Sense -> "XIAO_ESP32S3" + PSRAM "OPI PSRAM")   Serial Monitor 115200.
//  Libs  : Adafruit PN532, Adafruit SSD1306, Adafruit GFX
//  WiFi  : copy secrets.h from firmware/entry_station into this folder (optional - only for the web photo)
//
//  WIRING (same as entry_station.ino; PN532 DIP switch: I2C = SW1 ON, SW2 OFF)
//                                C6-WROOM-1 DevKit   XIAO C6 / XIAO S3
//    PN532 VCC + OLED VCC          3V3                 3V3
//    PN532 GND + OLED GND          GND                 GND
//    PN532 SDA + OLED SDA          GPIO6               D4
//    PN532 SCL + OLED SCL          GPIO7               D5
//    READ  button -> GND           GPIO18              D1
//    WRITE button -> GND           GPIO19              D0
//    PHOTO button -> GND           GPIO20              D3
//
//  WHAT TO DO
//    1. Open Serial Monitor: each part prints [PASS] or [FAIL].
//    2. Tap a gear tag on the reader -> UID + stored gear name on OLED and Serial.
//    3. Press each button -> its name shows on the OLED.
//    4. PHOTO button -> takes a photo, prints its size; open http://<IP shown>/ to see it.
//    Serial: s = recheck all, w = write "MS1:TEST" to the next tag (test tag only!)
// =====================================================================
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_PN532.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "esp_log.h"
#if CONFIG_IDF_TARGET_ESP32S3
  #define HAS_CAMERA 1
  #include "esp_camera.h"
#else
  #define HAS_CAMERA 0
  struct camera_fb_t;                 // no camera on the C6 (only so auto-generated prototypes compile)
#endif
// ---- print to BOTH the USB socket and the UART/COM socket, so the Serial Monitor
//      shows output whatever the "USB CDC On Boot" setting or the socket you use ----
#if ARDUINO_USB_MODE && SOC_USB_SERIAL_JTAG_SUPPORTED
#include "HWCDC.h"
#if ARDUINO_USB_CDC_ON_BOOT
  #define USB_PORT HWCDCSerial
#else
  HWCDC UsbPort;
  #define USB_PORT UsbPort
#endif
class DualSerial : public Print {
 public:
  void begin(unsigned long baud) {
    Serial0.begin(baud);
    USB_PORT.begin();
    USB_PORT.setTxTimeoutMs(0);             // never block when no USB monitor is open
  }
  size_t write(uint8_t c) override { Serial0.write(c); if (USB_PORT) USB_PORT.write(c); return 1; }
  size_t write(const uint8_t* b, size_t n) override { Serial0.write(b, n); if (USB_PORT) USB_PORT.write(b, n); return n; }
  int available() { return Serial0.available() + USB_PORT.available(); }
  int read() { return Serial0.available() ? Serial0.read() : USB_PORT.read(); }
  operator bool() { return (bool)USB_PORT; }
};
DualSerial DualOut;
#undef Serial
#define Serial DualOut
#endif

#if __has_include("secrets.h")
  #include "secrets.h"
#else
const char* WIFI_SSID = "YOUR_HOTSPOT";
const char* WIFI_PASS = "YOUR_PASSWORD";
#endif

#if CONFIG_IDF_TARGET_ESP32C6 && !defined(ARDUINO_XIAO_ESP32C6)   // ESP32-C6-WROOM-1 DevKit
  #define I2C_SDA   6
  #define I2C_SCL   7
  #define BTN_READ  18
  #define BTN_WRITE 19
  #define BTN_PHOTO 20
#else
  #define I2C_SDA   SDA   // D4
  #define I2C_SCL   SCL   // D5
  #define BTN_READ  D1
  #define BTN_WRITE D0
  #define BTN_PHOTO D3
#endif

Adafruit_PN532   nfc(-1, -1);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
WebServer        web(80);

bool oledOk = false, nfcOk = false, camOk = false, wifiOk = false, armWrite = false;
uint32_t photos = 0, lastPhotoBytes = 0;

void screen(const String& a, const String& b = "", const String& c = "", const String& d = "") {
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 0);  oled.print(a);
  oled.setCursor(0, 16); oled.print(b);
  oled.setCursor(0, 32); oled.print(c);
  oled.setCursor(0, 48); oled.print(d);
  oled.display();
}

#if HAS_CAMERA
bool camBegin() {                     // Seeed XIAO ESP32-S3 Sense pin map (same as entry_station.ino)
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 15; c.pin_d1 = 17; c.pin_d2 = 18; c.pin_d3 = 16;
  c.pin_d4 = 14; c.pin_d5 = 12; c.pin_d6 = 11; c.pin_d7 = 48;
  c.pin_xclk = 10; c.pin_pclk = 13; c.pin_vsync = 38; c.pin_href = 47;
  c.pin_sccb_sda = 40; c.pin_sccb_scl = 39;
  c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.grab_mode = CAMERA_GRAB_LATEST;
  c.frame_size = psramFound() ? FRAMESIZE_SVGA : FRAMESIZE_VGA;
  c.jpeg_quality = 12;
  c.fb_count = psramFound() ? 2 : 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.sccb_i2c_port = 1;                // camera on I2C port 1, PN532 + OLED on Wire (port 0)
  esp_err_t e = esp_camera_init(&c);
  if (e != ESP_OK) {
    Serial.printf("  [FAIL] camera init error 0x%x -> PSRAM set to OPI? camera ribbon pushed fully in?\n", e);
    return false;
  }
  sensor_t* s = esp_camera_sensor_get();
  const char* nm = !s ? "?" : s->id.PID == OV2640_PID ? "OV2640" : s->id.PID == OV3660_PID ? "OV3660" : "other";
  if (s && s->id.PID == OV3660_PID) { s->set_vflip(s, 1); s->set_brightness(s, 1); }
  Serial.printf("  [PASS] camera %s, %s, PSRAM %s\n", nm, psramFound() ? "800x600" : "640x480",
                psramFound() ? "found" : "NOT found (set Tools -> PSRAM: OPI PSRAM)");
  return true;
}

camera_fb_t* grab() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (fb) { esp_camera_fb_return(fb); fb = esp_camera_fb_get(); }   // fresh frame, not a stale one
  return fb;
}
#endif

void checkAll() {
  Serial.println("\n==== MineSafe entry station hardware test (XIAO ESP32-S3 Sense) ====");
  Wire.begin(I2C_SDA, I2C_SCL);
  Serial.print("I2C scan:");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X(%s)", a, a == 0x24 ? "PN532" : a == 0x3C || a == 0x3D ? "OLED" : "?"); n++;
    }
  }
  Serial.println(n ? "" : "  NOTHING -> check SDA D4 / SCL D5 / 3V3 / GND");

  oledOk = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  Serial.println(oledOk ? "  [PASS] OLED at 0x3C" : "  [FAIL] OLED not found at 0x3C");
  screen("MINESAFE HW TEST", "Checking NFC...");

  uint32_t fw = 0;
  for (int i = 0; i < 6 && !fw; i++) { nfc.begin(); delay(100); fw = nfc.getFirmwareVersion(); if (!fw) delay(400); }
  nfcOk = fw != 0;
  if (nfcOk) {
    nfc.SAMConfig();
    Serial.printf("  [PASS] PN532 firmware %d.%d\n", (int)((fw >> 16) & 0xFF), (int)((fw >> 8) & 0xFF));
  } else {
    Serial.println("  [FAIL] PN532 not answering -> DIP switch to I2C (1 ON, 2 OFF), SDA/SCL, unplug + replug USB");
  }

#if HAS_CAMERA
  screen("MINESAFE HW TEST", "Checking camera...");
  if (!camOk) camOk = camBegin();
#else
  Serial.println("  [INFO] no camera on this board - entry photo comes from http://<laptop-ip>:5000/phone");
#endif

  Serial.printf("  [INFO] buttons now: READ %s  WRITE %s  PHOTO %s  (should all be 'up')\n",
                digitalRead(BTN_READ) ? "up" : "DOWN", digitalRead(BTN_WRITE) ? "up" : "DOWN",
                digitalRead(BTN_PHOTO) ? "up" : "DOWN");
  screen("NFC  " + String(nfcOk ? "OK" : "FAIL"), HAS_CAMERA ? "CAM  " + String(camOk ? "OK" : "FAIL") : "CAM  phone page",
         wifiOk ? WiFi.localIP().toString() : "WiFi: no",
         "Tap tag / press btn");
}

#if HAS_CAMERA
void handleRoot() {
  String h = "<!doctype html><meta name=viewport content='width=device-width'><title>MineSafe cam test</title>"
             "<body style='font-family:sans-serif;background:#111;color:#eee;text-align:center'>"
             "<h3>XIAO S3 Sense camera</h3><img id=i src='/jpg' style='max-width:100%;border:2px solid #f2a900'>"
             "<p><button onclick=\"i.src='/jpg?'+Date.now()\" style='font-size:20px;padding:10px 24px'>Take photo</button></p>"
             "<p>Stand 2-3 m away so the whole body (helmet to shoes) is in the picture.</p></body>";
  web.send(200, "text/html", h);
}

void handleJpg() {
  if (!camOk) { web.send(503, "text/plain", "camera not ready"); return; }
  camera_fb_t* fb = grab();
  if (!fb) { web.send(500, "text/plain", "capture failed"); return; }
  web.setContentLength(fb->len);
  web.send(200, "image/jpeg", "");
  web.client().write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}
#endif

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 4000) delay(10);
  esp_log_level_set("i2c.master", ESP_LOG_NONE);
  pinMode(BTN_READ, INPUT_PULLUP);
  pinMode(BTN_WRITE, INPUT_PULLUP);
  pinMode(BTN_PHOTO, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  checkAll();
  t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 10000) delay(200);
  wifiOk = WiFi.status() == WL_CONNECTED;
  if (wifiOk) {
#if HAS_CAMERA
    web.on("/", handleRoot);
    web.on("/jpg", handleJpg);
    web.begin();
    Serial.printf("  [PASS] WiFi '%s'  ->  open  http://%s/  on a phone/laptop on the same hotspot\n",
                  WIFI_SSID, WiFi.localIP().toString().c_str());
#else
    Serial.printf("  [PASS] WiFi '%s' connected, IP %s\n", WIFI_SSID, WiFi.localIP().toString().c_str());
#endif
  } else {
    Serial.println("  [INFO] WiFi not connected (no secrets.h?) - web photo off, everything else still tested");
  }
  screen("NFC  " + String(nfcOk ? "OK" : "FAIL"), HAS_CAMERA ? "CAM  " + String(camOk ? "OK" : "FAIL") : "CAM  phone page",
         wifiOk ? WiFi.localIP().toString() : "WiFi: no", "Tap tag / press btn");
  Serial.println("\nReady: tap a tag, press the buttons. Serial: s = recheck, w = write test tag\n");
}

void readTag() {
  uint8_t uid[7], len = 0;
  if (!nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len, 60)) return;
  String u;
  for (uint8_t i = 0; i < len; i++) { char b[3]; sprintf(b, "%02X", uid[i]); u += b; }
  String txt = "";
  uint8_t pg[4];
  for (uint8_t p = 4; p < 8; p++) {
    if (!nfc.ntag2xx_ReadPage(p, pg)) break;
    for (uint8_t i = 0; i < 4; i++) if (pg[i] >= 32 && pg[i] < 127) txt += (char)pg[i];
  }
  if (armWrite) {
    uint8_t data[16] = {'M', 'S', '1', ':', 'T', 'E', 'S', 'T'};
    bool ok = true;
    for (uint8_t p = 0; p < 4 && ok; p++) ok = nfc.ntag2xx_WritePage(4 + p, data + p * 4);
    armWrite = false;
    Serial.printf("WRITE %s on tag %s\n", ok ? "OK" : "FAILED", u.c_str());
    txt = ok ? "MS1:TEST" : txt;
  }
  Serial.printf("TAG  UID %s  (%d bytes)  data \"%s\"%s\n", u.c_str(), len, txt.c_str(),
                txt.startsWith("MS1:") ? "  <- MineSafe gear tag" : "  (blank / not written yet)");
  screen("TAG READ OK", "UID " + u, txt.length() ? txt : "(blank tag)", "");
  delay(1200);
}

void loop() {
  static bool lr = true, lw = true, lp = true;
#if HAS_CAMERA
  if (wifiOk) web.handleClient();
#endif
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 's') checkAll();
    if (c == 'w') { armWrite = true; Serial.println("Write armed: tap a TEST tag (it will hold MS1:TEST)"); }
  }
  bool r = digitalRead(BTN_READ), w = digitalRead(BTN_WRITE), p = digitalRead(BTN_PHOTO);
  if (!r && lr) { Serial.println("BUTTON READ pressed");  screen("BUTTON", "READ   OK"); }
  if (!w && lw) { Serial.println("BUTTON WRITE pressed"); screen("BUTTON", "WRITE  OK"); }
  if (!p && lp) {
    Serial.println("BUTTON PHOTO pressed");
#if HAS_CAMERA
    if (camOk) {
      uint32_t t = millis();
      camera_fb_t* fb = grab();
      if (fb) {
        photos++; lastPhotoBytes = fb->len;
        Serial.printf("PHOTO %lu: %ux%u, %lu bytes in %lu ms%s\n", (unsigned long)photos, fb->width, fb->height,
                      (unsigned long)fb->len, (unsigned long)(millis() - t),
                      wifiOk ? "  (see it at the web page)" : "");
        screen("PHOTO OK", String(fb->width) + "x" + String(fb->height), String(fb->len / 1024) + " kB",
               wifiOk ? WiFi.localIP().toString() : "");
        esp_camera_fb_return(fb);
      } else { Serial.println("PHOTO FAILED"); screen("PHOTO FAILED"); }
    } else screen("BUTTON", "PHOTO  OK", "camera not ready");
#else
    screen("BUTTON", "PHOTO  OK", "photo: phone page", "<laptop>:5000/phone");
#endif
  }
  lr = r; lw = w; lp = p;
  if (nfcOk) readTag();
  delay(20);
}
