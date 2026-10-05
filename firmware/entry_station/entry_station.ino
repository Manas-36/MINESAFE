// =====================================================================
//  MineSafe - ENTRY STATION v3 (RFID gear tags + camera photo)
//  Board : ESP32-C6 (scanning system, no camera): ESP32-C6-WROOM-1 DevKit ("ESP32C6 Dev Module")
//          or Seeed XIAO ESP32-C6 ("XIAO_ESP32C6"). The entry photo comes from the phone page
//          http://<laptop-ip>:5000/phone and is matched with the scanned tags on the hub.
//          Still builds for the XIAO ESP32-S3 Sense (built-in camera, PSRAM: "OPI PSRAM").
//          Arduino ESP32 core 3.x.
//  Parts : PN532 NFC (I2C mode), SSD1306 0.96" 128x64 I2C OLED,
//          3 push buttons (READ, WRITE, PHOTO), NTAG215 tags, OV2640/OV3660 camera (Sense board)
//  Libs  : Adafruit PN532 (latest), Adafruit SSD1306, Adafruit GFX
//
//  WIRING (PN532 and OLED share I2C: PN532=0x24, OLED=0x3C; PN532 DIP: I2C = 1 ON, 2 OFF)
//                                          C6-WROOM-1 DevKit   XIAO C6        XIAO S3 Sense
//    PN532 VCC / OLED VCC -> 3V3      PN532 GND / OLED GND -> GND
//    PN532 SDA / OLED SDA              GPIO6               D4 (GPIO22)    D4 (GPIO5)
//    PN532 SCL / OLED SCL              GPIO7               D5 (GPIO23)    D5 (GPIO6)
//    READ  button  -> GND              GPIO18              D1 (GPIO1)     D1 (GPIO2)
//    WRITE button  -> GND              GPIO19              D0 (GPIO0)     D0 (GPIO1)
//    PHOTO button  -> GND (optional)   GPIO20              D3 (GPIO21)    D3 (GPIO4)
//    (buttons use the internal pull-up, no resistors)
//    Camera: plugged into the Sense expansion board (B2B connector), no wires.
//
//  HOW IT WORKS
//   READ button  : always takes you to READ mode (from any screen).
//   READ mode    : "Tap tag" -> tap a tag -> SUCCESS screen with the gear
//                  name + admin verdict -> back to "Tap tag" after 3 s.
//   WRITE button : opens the gear menu (HELMET / VEST / PANTS / SHOES).
//     in menu    : WRITE tap = next item, WRITE hold = select
//     after pick : "Place tag for VEST" -> tap tag -> SUCCESS -> back to the menu.
//   PHOTO button : (after the worker has tapped all gear tags) 3-2-1 countdown,
//                  takes a photo and sends it to the hub with the scanned tags ->
//                  hub runs the AI kit check -> verdict shown on the OLED.
//                  Admin approves on the Entry check tab and pairs a body unit.
//   30 s with no button press in write screens -> back to READ.
//
//  TAG FORMAT (NTAG215 pages 4..7, 16 bytes): "MS1:" + gear name, zero padded.
//  Pages 0..3 (UID, lock bits, CC) are never touched.
//
//  HUB ADDRESS: if the laptop IP changes (phone hotspot), the station scans the
//  hotspot subnet for the hub on port 5000 by itself (HUB_AUTOFIND).
// =====================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <NetworkClient.h>
#include <Wire.h>
#include <Adafruit_PN532.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#if CONFIG_IDF_TARGET_ESP32S3
  #define HAS_CAMERA 1
  #include "esp_camera.h"
#else
  #define HAS_CAMERA 0
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

// ------------------------- CONFIG ------------------------------------
// Copy secrets.example.h to secrets.h and fill it in (not uploaded to GitHub).
#if __has_include("secrets.h")
  #include "secrets.h"
#else
const char* WIFI_SSID  = "YOUR_HOTSPOT";
const char* WIFI_PASS  = "YOUR_PASSWORD";
const char* ADMIN_URL  = "http://192.168.1.100:5000/api/gear";   // laptop IP running admin_hub.py
#endif
const char* STATION_ID = "ENTRY-01";

#define PN532_IRQ    -1   // not wired - update "Adafruit PN532" to the latest version (1.3.x)
#define PN532_RESET  -1   // not wired
#if CONFIG_IDF_TARGET_ESP32C6 && !defined(ARDUINO_XIAO_ESP32C6)   // ESP32-C6-WROOM-1 DevKit
  #define I2C_SDA    6
  #define I2C_SCL    7
  #define BTN_READ   18
  #define BTN_WRITE  19
  #define BTN_PHOTO  20
#else                                                             // XIAO C6 / XIAO S3 Sense
  #define I2C_SDA    SDA      // D4
  #define I2C_SCL    SCL      // D5
  #define BTN_READ   D1
  #define BTN_WRITE  D0
  #define BTN_PHOTO  D3
#endif
#define HUB_AUTOFIND 1    // find the hub on the subnet if the laptop IP changed
#define HUB_PORT     5000
#define COUNTDOWN_S  3    // photo countdown

#define LONG_MS            800     // hold time to select in menu
#define DEBOUNCE_MS        30
#define IDLE_TIMEOUT_MS    30000   // write screens fall back to READ
#define RESULT_MS          3000    // how long the read result stays
#define SAME_TAG_IGNORE_MS 3000    // ignore the same tag sitting on the reader
// ---------------------------------------------------------------------

#define W SSD1306_WHITE
#define B SSD1306_BLACK

Adafruit_PN532   nfc(PN532_IRQ, PN532_RESET);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

const char*   GEAR[] = {"HELMET", "VEST", "PANTS", "SHOES"};
const uint8_t GEAR_N = 4;
const char    TAG_PREFIX[] = "MS1:";

enum Mode { READ_IDLE, READ_RESULT, MENU, WRITE_WAIT };
Mode mode = READ_IDLE;

uint8_t cursor = 0;
uint16_t writtenCount[GEAR_N];   // how many of each item written this session

#define SESSION_MAX 60           // remember tags written this session
String  sessUid[SESSION_MAX];
uint8_t sessGear[SESSION_MAX];
uint8_t sessN = 0;
unsigned long lastTouch = 0, resultAt = 0;
String  lastSeenUid = "";
unsigned long lastSeenAt = 0;

// ------------------------- BUTTONS -----------------------------------
enum BtnEvent { BTN_NONE, BTN_SHORT, BTN_LONG };

struct Button {
  uint8_t pin;
  bool down = false, longFired = false;
  unsigned long pressedAt = 0, lastEdge = 0;
};
Button btnR{BTN_READ}, btnW{BTN_WRITE}, btnP{BTN_PHOTO};

BtnEvent poll(Button& b) {
  bool pressed = (digitalRead(b.pin) == LOW);
  unsigned long now = millis();
  if (pressed != b.down && now - b.lastEdge > DEBOUNCE_MS) {
    b.lastEdge = now;
    b.down = pressed;
    if (pressed) { b.pressedAt = now; b.longFired = false; }
    else if (!b.longFired) return BTN_SHORT;
  }
  if (b.down && !b.longFired && now - b.pressedAt >= LONG_MS) {
    b.longFired = true;
    return BTN_LONG;
  }
  return BTN_NONE;
}

// ------------------------- DRAW HELPERS ------------------------------
void centerText(const String& s, int y, uint8_t size) {
  oled.setTextSize(size);
  int x = (128 - (int)s.length() * 6 * size) / 2;
  oled.setCursor(x < 0 ? 0 : x, y);
  oled.print(s);
}

void header(const char* left, const char* right) {
  oled.clearDisplay();
  oled.setTextColor(W);
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print(left);
  oled.setCursor(128 - strlen(right) * 6, 0);
  oled.print(right);
  oled.drawFastHLine(0, 10, 128, W);
}

void footer(const char* text) {
  oled.setTextSize(1);
  oled.setCursor(0, 55);
  oled.print(text);
}

void drawTick(int x, int y) {
  oled.drawCircle(x, y, 11, W);
  for (int d = 0; d < 2; d++) {
    oled.drawLine(x - 6, y + d, x - 2, y + 4 + d, W);
    oled.drawLine(x - 2, y + 4 + d, x + 6, y - 4 + d, W);
  }
}

void drawCross(int x, int y) {
  oled.drawCircle(x, y, 11, W);
  for (int d = 0; d < 2; d++) {
    oled.drawLine(x - 5 + d, y - 5, x + 5 + d, y + 5, W);
    oled.drawLine(x + 5 + d, y - 5, x - 5 + d, y + 5, W);
  }
}

const char* wifiTag() { return WiFi.status() == WL_CONNECTED ? "WiFi" : "no WiFi"; }

// ------------------------- SCREENS -----------------------------------
void showReadIdle() {
  header("READ MODE", wifiTag());
  centerText("Tap tag", 20, 2);
  centerText("on the reader", 40, 1);
  footer(HAS_CAMERA ? "W:write  P:photo" : "W: write mode");
  oled.display();
}

void showMenu(float holdFrac = 0) {
  header("WRITE MODE", "R:exit");
  for (uint8_t i = 0; i < GEAR_N; i++) {
    int y = 13 + i * 10;
    if (i == cursor) { oled.fillRect(0, y - 1, 128, 10, W); oled.setTextColor(B); }
    else             { oled.setTextColor(W); }
    oled.setTextSize(1);
    oled.setCursor(4, y);
    oled.print(i == cursor ? "> " : "  ");
    oled.print(GEAR[i]);
    if (writtenCount[i]) {
      String c = "x" + String(writtenCount[i]);
      oled.setCursor(124 - c.length() * 6, y);
      oled.print(c);
    }
  }
  oled.setTextColor(W);
  if (holdFrac > 0) {                                   // hold-to-select progress bar
    oled.drawRect(0, 55, 128, 8, W);
    oled.fillRect(2, 57, (int)(124 * holdFrac), 4, W);
  } else {
    footer("W:next  Hold W:select");
  }
  oled.display();
}

void showWriteWait(const char* note = "") {
  header("WRITE MODE", "R:exit");
  centerText("Place tag for", 15, 1);
  centerText(GEAR[cursor], 27, 2);
  centerText(note, 45, 1);
  footer("W: change item");
  oled.display();
}

void showBusy(const char* text) {
  oled.clearDisplay();
  oled.setTextColor(W);
  centerText(text, 26, 2);
  oled.display();
}

void showResult(bool ok, const char* title, const String& l1, const String& l2) {
  oled.clearDisplay();
  oled.setTextColor(W);
  if (ok) drawTick(12, 20); else drawCross(12, 20);
  oled.setTextSize(2);
  oled.setCursor(28, 13);
  oled.print(title);
  oled.setTextSize(1);
  oled.setCursor(0, 40);
  oled.print(l1);
  oled.setCursor(0, 52);
  oled.print(l2);
  oled.display();
}

// ------------------------- TAG I/O -----------------------------------
String uidToStr(const uint8_t* uid, uint8_t len) {
  String s;
  char b[3];
  for (uint8_t i = 0; i < len; i++) { sprintf(b, "%02X", uid[i]); s += b; }
  return s;
}

// false = I/O error. out = gear name, or "BLANK" if no MS1 record.
bool readGear(char* out, size_t n) {
  uint8_t data[16];
  for (uint8_t p = 0; p < 4; p++)
    if (!nfc.ntag2xx_ReadPage(4 + p, data + p * 4)) return false;
  if (memcmp(data, TAG_PREFIX, 4) != 0) { strlcpy(out, "BLANK", n); return true; }
  char tmp[13];
  memcpy(tmp, data + 4, 12);
  tmp[12] = 0;
  strlcpy(out, tmp, n);
  return true;
}

bool writeGear(const char* gear) {
  uint8_t data[16] = {0};
  memcpy(data, TAG_PREFIX, 4);
  strncpy((char*)data + 4, gear, 12);
  for (uint8_t p = 0; p < 4; p++)
    if (!nfc.ntag2xx_WritePage(4 + p, data + p * 4)) return false;
  char check[16];
  return readGear(check, sizeof(check)) && strcmp(check, gear) == 0;   // verify
}

// ------------------------- ADMIN LINK --------------------------------
String hubBase;   // "http://10.180.64.143:5000" - taken from ADMIN_URL, updated by HUB_AUTOFIND

void initHubBase() {
  hubBase = ADMIN_URL;
  int k = hubBase.indexOf("/api/");
  if (k > 0) hubBase = hubBase.substring(0, k);
}

// Scan the /24 subnet for something listening on HUB_PORT (laptop running admin_hub.py).
bool findHub() {
#if HUB_AUTOFIND
  if (WiFi.status() != WL_CONNECTED) return false;
  IPAddress me = WiFi.localIP();
  showBusy("Finding hub");
  for (int i = 1; i < 255; i++) {
    if (i == me[3]) continue;
    IPAddress ip(me[0], me[1], me[2], i);
    NetworkClient c;
    if (c.connect(ip, HUB_PORT, 120)) {
      c.stop();
      hubBase = "http://" + ip.toString() + ":" + String(HUB_PORT);
      Serial.println("Hub found at " + hubBase);
      return true;
    }
  }
#endif
  return false;
}

// POST to hub path; on connection failure try to find the hub once and retry.
int hubPost(const String& path, const char* type, const uint8_t* body, size_t len, String& resp,
            const char* hdrName, const char* hdrVal, uint16_t timeoutMs) {
  for (int attempt = 0; attempt < 2; attempt++) {
    HTTPClient http;
    http.setTimeout(timeoutMs);
    http.begin(hubBase + path);
    http.addHeader("Content-Type", type);
    if (hdrName) http.addHeader(hdrName, hdrVal);
    int code = http.POST((uint8_t*)body, len);
    resp = (code > 0) ? http.getString() : "";
    http.end();
    if (code > 0 || attempt == 1 || !findHub()) return code;
  }
  return -1;
}

String jsonField(const String& resp, const char* key) {
  String k = String("\"") + key + "\":";
  int i = resp.indexOf(k);
  if (i < 0) return "";
  i += k.length();
  while (i < (int)resp.length() && resp[i] == ' ') i++;
  if (resp[i] == '"') { int e = resp.indexOf('"', i + 1); return resp.substring(i + 1, e); }
  int e = i;
  while (e < (int)resp.length() && resp[e] != ',' && resp[e] != '}') e++;
  return resp.substring(i, e);
}

// Returns admin verdict (OK / ISSUED / MISMATCH / UNKNOWN TAG) or OFFLINE / ERR.
String sendToAdmin(const char* event, const String& uid, const char* gear, const char* prev) {
  if (WiFi.status() != WL_CONNECTED) return "OFFLINE";
  char body[200];
  snprintf(body, sizeof(body),
           "{\"station\":\"%s\",\"event\":\"%s\",\"uid\":\"%s\",\"gear\":\"%s\",\"prev\":\"%s\"}",
           STATION_ID, event, uid.c_str(), gear, prev);
  String resp;
  int code = hubPost("/api/gear", "application/json", (const uint8_t*)body, strlen(body), resp, nullptr, nullptr, 2000);
  if (code < 200 || code >= 300) return code > 0 ? "ERR " + String(code) : "NO HUB";
  String c = jsonField(resp, "check");
  return c.length() ? c : "SENT";
}

// ------------------------- CAMERA ------------------------------------
#if HAS_CAMERA
bool camOk = false;

bool camBegin() {                     // Seeed XIAO ESP32-S3 Sense pin map
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer   = LEDC_TIMER_0;
  c.pin_d0 = 15; c.pin_d1 = 17; c.pin_d2 = 18; c.pin_d3 = 16;
  c.pin_d4 = 14; c.pin_d5 = 12; c.pin_d6 = 11; c.pin_d7 = 48;
  c.pin_xclk = 10; c.pin_pclk = 13; c.pin_vsync = 38; c.pin_href = 47;
  c.pin_sccb_sda = 40; c.pin_sccb_scl = 39;
  c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.grab_mode    = CAMERA_GRAB_LATEST;
  if (psramFound()) {
    c.frame_size = FRAMESIZE_SVGA;     // 800x600 is plenty for the AI kit check
    c.jpeg_quality = 12;
    c.fb_count = 2;
    c.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    c.frame_size = FRAMESIZE_VGA;
    c.jpeg_quality = 14;
    c.fb_count = 1;
    c.fb_location = CAMERA_FB_IN_DRAM;
  }
  c.sccb_i2c_port = 1;                 // camera on I2C port 1, PN532 + OLED on Wire (port 0)
  esp_err_t e = esp_camera_init(&c);
  if (e != ESP_OK) { Serial.printf("Camera init failed 0x%x (PSRAM on? camera seated?)\n", e); return false; }
  sensor_t* s = esp_camera_sensor_get();
  if (s && s->id.PID == OV3660_PID) { s->set_vflip(s, 1); s->set_brightness(s, 1); }
  Serial.println(psramFound() ? "Camera OK (SVGA, PSRAM)" : "Camera OK (VGA, no PSRAM)");
  return true;
}
#endif

void takeAndSendPhoto() {
#if !HAS_CAMERA
  showResult(false, "USE PHONE", "Photo on phone:", "<laptop-ip>:5000/phone");
#else
  if (!camOk) { showResult(false, "NO CAM", "Camera not found", "Check Sense board"); return; }
  for (int i = COUNTDOWN_S; i > 0; i--) {             // let the worker stand still
    oled.clearDisplay();
    oled.setTextColor(W);
    centerText("Stand in frame", 2, 1);
    centerText(String(i), 18, 4);
    oled.display();
    camera_fb_t* warm = esp_camera_fb_get();          // keep auto-exposure settling
    if (warm) esp_camera_fb_return(warm);
    delay(1000);
  }
  showBusy("Click!");
  camera_fb_t* fb = esp_camera_fb_get();
  if (fb) { esp_camera_fb_return(fb); fb = esp_camera_fb_get(); }   // fresh frame
  if (!fb) { showResult(false, "FAILED", "Camera error", "Press P again"); return; }
  size_t kb = fb->len / 1024;
  Serial.printf("Photo %ux%u %u KB\n", fb->width, fb->height, (unsigned)fb->len);

  if (WiFi.status() != WL_CONNECTED) { esp_camera_fb_return(fb); showResult(false, "OFFLINE", "No WiFi", "Photo not sent"); return; }
  showBusy("Sending...");
  String resp;
  int code = hubPost("/api/camphoto", "image/jpeg", fb->buf, fb->len, resp, "X-Station", STATION_ID, 20000);
  esp_camera_fb_return(fb);
  if (code < 200 || code >= 300) {
    showResult(false, "FAILED", code > 0 ? "Hub error " + String(code) : "Hub not found", String(kb) + " KB photo");
    return;
  }
  String ai = jsonField(resp, "ai"), det = jsonField(resp, "detail"), n = jsonField(resp, "scans");
  bool good = ai.startsWith("KIT COMPLETE") || ai == "OFF";
  String l1 = "AI: " + (ai == "OFF" ? String("admin checks") : ai);
  showResult(good, "SENT", l1.substring(0, 21), (n + " tags | " + det).substring(0, 21));
  Serial.println("Hub: " + resp);
#endif
  resultAt = millis();
  mode = READ_RESULT;
}

// ------------------------- MODE CHANGES ------------------------------
void goRead() {
  mode = READ_IDLE;
  showReadIdle();
}

void enterMenu() {
  for (uint8_t i = 0; i < GEAR_N; i++) writtenCount[i] = 0;   // new session
  sessN = 0;
  cursor = 0;
  lastTouch = millis();
  mode = MENU;
  showMenu();
}

int findSession(const String& u) {
  for (uint8_t i = 0; i < sessN; i++) if (sessUid[i] == u) return i;
  return -1;
}

// ------------------------- TAG HANDLERS ------------------------------
void handleRead(const uint8_t* uid, uint8_t len) {
  String u = uidToStr(uid, len);
  if (u == lastSeenUid && millis() - lastSeenAt < SAME_TAG_IGNORE_MS) {
    lastSeenAt = millis();                 // still sitting on the reader
    return;
  }
  lastSeenUid = u;
  lastSeenAt  = millis();
  resultAt    = millis();
  mode        = READ_RESULT;

  if (len != 7) { showResult(false, "WRONG", "Not an NTAG tag", u); return; }

  showBusy("Reading...");
  char gear[16];
  if (!readGear(gear, sizeof(gear))) { showResult(false, "FAILED", "Hold tag still", "and try again"); return; }
  if (strcmp(gear, "BLANK") == 0)    { showResult(false, "BLANK", "Tag not written", "Use W to write it"); return; }

  showBusy("Sending...");
  String verdict = sendToAdmin("scan", u, gear, "");

  if (verdict == "MISMATCH" || verdict == "UNKNOWN TAG") {
    showResult(false, "INVALID", String(gear) + " " + u, "Admin: " + verdict);
  } else {
    showResult(true, "SUCCESS", String(gear) + " " + u, "Admin: " + verdict);
  }
}

void handleWrite(const uint8_t* uid, uint8_t len) {
  String u = uidToStr(uid, len);
  lastTouch = millis();

  if (len != 7) { showWriteWait("Not an NTAG tag!"); delay(1000); showWriteWait(); return; }

  int s = findSession(u);                           // written as another item this session?
  if (s >= 0 && sessGear[s] != cursor) {
    showWriteWait((String("Tag is ") + GEAR[sessGear[s]] + "!").c_str());
    delay(1500);
    showWriteWait();
    return;
  }
  if (s >= 0) {                                     // same tag, same item again
    showWriteWait("Already done - next tag");
    delay(1200);
    showWriteWait();
    return;
  }

  char prev[16] = "";
  readGear(prev, sizeof(prev));

  showBusy("Writing...");
  if (!writeGear(GEAR[cursor])) {
    showResult(false, "FAILED", "Hold tag still", "and tap again");
    delay(1500);
    showWriteWait();
    return;
  }

  showBusy("Sending...");
  String verdict = sendToAdmin("write", u, GEAR[cursor], prev);
  showResult(true, "SUCCESS", String(GEAR[cursor]) + " written", "Admin: " + verdict);
  delay(1500);

  writtenCount[cursor]++;
  if (sessN < SESSION_MAX) { sessUid[sessN] = u; sessGear[sessN] = cursor; sessN++; }
  lastSeenUid = u;                                  // don't re-read it in READ mode
  lastSeenAt  = millis();

  // back to the menu, same item still highlighted
  lastTouch = millis();
  mode      = MENU;
  showMenu();
}

// ------------------------- SETUP / LOOP ------------------------------
void setup() {
  Serial.begin(115200);
  pinMode(BTN_READ, INPUT_PULLUP);
  pinMode(BTN_WRITE, INPUT_PULLUP);
  pinMode(BTN_PHOTO, INPUT_PULLUP);
  initHubBase();
  Wire.begin(I2C_SDA, I2C_SCL);       // set the pins first; the PN532 / OLED libraries then reuse this bus

  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) Serial.println("OLED not found");
  oled.clearDisplay();
  oled.setTextColor(W);
  centerText("MINESAFE", 10, 1);
  centerText("Entry Station", 22, 1);
  centerText("Starting NFC...", 44, 1);
  oled.display();

  // PN532 often misses the first wake-up over I2C (no reset wire) -> retry
  uint32_t fw = 0;
  for (uint8_t attempt = 0; attempt < 6 && !fw; attempt++) {
    nfc.begin();
    delay(100);
    fw = nfc.getFirmwareVersion();
    if (!fw) delay(400);
  }
  if (!fw) {
    // scan the I2C bus so we can see what is actually connected
    String found = "";
    bool pnSeen = false;
    for (uint8_t a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        char b[5];
        sprintf(b, "%02X ", a);
        found += b;
        if (a == 0x24) pnSeen = true;
      }
    }
    Serial.println("I2C devices: " + found);
    oled.clearDisplay();
    drawCross(12, 20);
    oled.setTextSize(1);
    oled.setCursor(28, 16); oled.print("PN532 not found");
    oled.setCursor(0, 36);  oled.print("I2C: "); oled.print(found);
    oled.setCursor(0, 48);
    oled.print(pnSeen ? "24 ok, no reply-replug" : "No 24: wires/DIP/power");
    oled.display();
    while (1) delay(10);
  }
  nfc.SAMConfig();

#if HAS_CAMERA
  oled.fillRect(0, 44, 128, 10, B);
  centerText("Starting camera...", 44, 1);
  oled.display();
  camOk = camBegin();
#endif

  oled.fillRect(0, 44, 128, 10, B);
  centerText("Connecting WiFi...", 44, 1);
  oled.display();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 10000) delay(200);
  Serial.println(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "WiFi offline");

  goRead();
}

void loop() {
  BtnEvent r = poll(btnR);
  BtnEvent w = poll(btnW);
  BtnEvent p = poll(btnP);
  uint8_t uid[7];
  uint8_t len = 0;

  // PHOTO button works from READ screens
  if (p == BTN_SHORT && (mode == READ_IDLE || mode == READ_RESULT)) { takeAndSendPhoto(); return; }

  // READ button works from anywhere
  if (r != BTN_NONE) {
    if (mode != READ_IDLE) goRead();
    return;
  }

  switch (mode) {
    case READ_IDLE:
    case READ_RESULT:
      if (w != BTN_NONE) { enterMenu(); return; }
      if (mode == READ_RESULT && millis() - resultAt > RESULT_MS) goRead();
      if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len, 50)) handleRead(uid, len);
      break;

    case MENU: {
      static unsigned long lastBarDraw = 0;
      if (w == BTN_SHORT) {
        cursor = (cursor + 1) % GEAR_N;
        lastTouch = millis();
        showMenu();
      } else if (w == BTN_LONG) {
        lastTouch = millis();
        mode = WRITE_WAIT;
        showWriteWait();
      } else if (btnW.down && !btnW.longFired) {
        if (millis() - lastBarDraw > 40) {           // animate hold bar
          lastBarDraw = millis();
          showMenu((millis() - btnW.pressedAt) / (float)LONG_MS);
        }
      } else if (millis() - lastTouch > IDLE_TIMEOUT_MS) {
        goRead();
      }
      break;
    }

    case WRITE_WAIT:
      if (w == BTN_SHORT) { lastTouch = millis(); mode = MENU; showMenu(); return; }
      if (millis() - lastTouch > IDLE_TIMEOUT_MS) { goRead(); return; }
      if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len, 50)) handleWrite(uid, len);
      break;
  }
}
