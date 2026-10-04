// =====================================================================
//  MineSafe - ENTRY STATION HARDWARE TEST (XIAO ESP32-S3 Sense)
//  Checks the PN532 RFID reader, the OLED, the 3 buttons and the camera,
//  and shows a live camera photo in a phone/laptop browser - no hub needed.
//  Run this before flashing entry_station.ino.
//
//  Board : Tools -> Board: "XIAO_ESP32S3",  Tools -> PSRAM: "OPI PSRAM"  (camera needs it)
//          Tools -> USB CDC On Boot: "Enabled".  Serial Monitor 115200.
//  Libs  : Adafruit PN532, Adafruit SSD1306, Adafruit GFX
//  WiFi  : copy secrets.h from firmware/entry_station into this folder (optional - only for the web photo)
//
//  WIRING (same as entry_station.ino; PN532 DIP switch: I2C = SW1 ON, SW2 OFF)
//    PN532 VCC + OLED VCC -> 3V3        PN532 GND + OLED GND -> GND
//    PN532 SDA + OLED SDA -> D4 (GPIO5)  PN532 SCL + OLED SCL -> D5 (GPIO6)
//    READ  button -> D1 and GND    WRITE button -> D0 and GND    PHOTO button -> D3 and GND
//    Camera: on the Sense expansion board (B2B connector), nothing to wire.
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
#include "esp_camera.h"
#include "esp_log.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
const char* WIFI_SSID = "YOUR_HOTSPOT";
const char* WIFI_PASS = "YOUR_PASSWORD";
#endif

#define BTN_READ  D1
#define BTN_WRITE D0
#define BTN_PHOTO D3

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

void checkAll() {
  Serial.println("\n==== MineSafe entry station hardware test (XIAO ESP32-S3 Sense) ====");
  Wire.begin();                       // XIAO S3: SDA D4 = GPIO5, SCL D5 = GPIO6
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

  screen("MINESAFE HW TEST", "Checking camera...");
  if (!camOk) camOk = camBegin();

  Serial.printf("  [INFO] buttons now: READ %s  WRITE %s  PHOTO %s  (should all be 'up')\n",
                digitalRead(BTN_READ) ? "up" : "DOWN", digitalRead(BTN_WRITE) ? "up" : "DOWN",
                digitalRead(BTN_PHOTO) ? "up" : "DOWN");
  screen("NFC  " + String(nfcOk ? "OK" : "FAIL"), "CAM  " + String(camOk ? "OK" : "FAIL"),
         wifiOk ? WiFi.localIP().toString() : "WiFi: no",
         "Tap tag / press btn");
}

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
    web.on("/", handleRoot);
    web.on("/jpg", handleJpg);
    web.begin();
    Serial.printf("  [PASS] WiFi '%s'  ->  open  http://%s/  on a phone/laptop on the same hotspot\n",
                  WIFI_SSID, WiFi.localIP().toString().c_str());
  } else {
    Serial.println("  [INFO] WiFi not connected (no secrets.h?) - web photo off, everything else still tested");
  }
  screen("NFC  " + String(nfcOk ? "OK" : "FAIL"), "CAM  " + String(camOk ? "OK" : "FAIL"),
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
  if (wifiOk) web.handleClient();
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 's') checkAll();
    if (c == 'w') { armWrite = true; Serial.println("Write armed: tap a TEST tag (it will hold MS1:TEST)"); }
  }
  bool r = digitalRead(BTN_READ), w = digitalRead(BTN_WRITE), p = digitalRead(BTN_PHOTO);
  if (!r && lr) { Serial.println("BUTTON READ pressed");  screen("BUTTON", "READ  (D1)  OK"); }
  if (!w && lw) { Serial.println("BUTTON WRITE pressed"); screen("BUTTON", "WRITE (D0)  OK"); }
  if (!p && lp) {
    Serial.println("BUTTON PHOTO pressed");
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
    } else screen("BUTTON", "PHOTO (D3)  OK", "camera not ready");
  }
  lr = r; lw = w; lp = p;
  if (nfcOk) readTag();
  delay(20);
}
