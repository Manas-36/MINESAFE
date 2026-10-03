// =====================================================================
//  Miner Safety System - ENTRY STATION (gear tag reader / writer)
//  Board : Seeed XIAO ESP32-C6   (Arduino ESP32 core 3.x)
//  Parts : PN532 NFC (I2C mode), SSD1306 0.96" 128x64 I2C OLED,
//          1 push button, NTAG215 tags
//  Libs  : Adafruit PN532, Adafruit SSD1306, Adafruit GFX
//
//  WIRING (PN532 and OLED share the I2C bus: PN532=0x24, OLED=0x3C)
//    PN532 VCC/OLED VCC -> 3V3        PN532 GND/OLED GND -> GND
//    PN532 SDA/OLED SDA -> D4         PN532 SCL/OLED SCL -> D5
//    PN532 IRQ          -> D2         PN532 RST          -> D3
//    Button             -> D1 and GND (internal pull-up used)
//
//  BUTTON / MODES
//    READ   : default. Tap a tag -> shows gear + UID, sends "scan" to admin.
//             Long press -> SELECT.
//    SELECT : HELMET / VEST / PANTS / SHOES. Short press = next item,
//             long press = choose it -> WRITE. 20 s idle -> back to READ.
//    WRITE  : tap a tag -> writes the gear, verifies, sends "write" to admin,
//             then returns to SELECT with the NEXT item highlighted
//             (so a full kit is issued quickly). Long press = cancel -> READ.
//
//  TAG FORMAT (NTAG215 pages 4..7, 16 bytes): "MS1:" + gear name, zero padded.
//  Pages 0..3 (UID, lock bits, CC) are never touched.
// =====================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_PN532.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ------------------------- CONFIG ------------------------------------
const char* WIFI_SSID  = "YOUR_WIFI";
const char* WIFI_PASS  = "YOUR_PASSWORD";
const char* ADMIN_URL  = "http://192.168.1.100:5000/api/gear";  // admin hub endpoint
const char* STATION_ID = "ENTRY-01";

#define PN532_IRQ    D2
#define PN532_RESET  D3
#define BTN_PIN      D1

#define LONG_MS            800     // hold time for a long press
#define DEBOUNCE_MS        30
#define SELECT_TIMEOUT_MS  20000   // idle time before SELECT/WRITE falls back to READ
#define SAME_TAG_IGNORE_MS 3000    // don't resend the same tag while it sits on the reader
// ---------------------------------------------------------------------

Adafruit_PN532   nfc(PN532_IRQ, PN532_RESET);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

const char*   GEAR[]   = {"HELMET", "VEST", "PANTS", "SHOES"};
const uint8_t GEAR_N   = 4;
const char    TAG_PREFIX[] = "MS1:";

enum Mode { READ_MODE, SELECT_MODE, WRITE_MODE };
Mode    mode   = READ_MODE;
uint8_t cursor = 0;
unsigned long lastActivity = 0;

String lastGear   = "-";
String lastUid    = "";
String lastStatus = "";
String lastSeenUid = "";
unsigned long lastSeenAt = 0;

// ------------------------- BUTTON ------------------------------------
enum BtnEvent { BTN_NONE, BTN_SHORT, BTN_LONG };
bool btnDown = false, longFired = false;
unsigned long btnPressedAt = 0, lastEdge = 0;

BtnEvent pollButton() {
  bool pressed = (digitalRead(BTN_PIN) == LOW);
  unsigned long now = millis();

  if (pressed != btnDown && now - lastEdge > DEBOUNCE_MS) {
    lastEdge = now;
    btnDown  = pressed;
    if (pressed) {
      btnPressedAt = now;
      longFired = false;
    } else if (!longFired) {
      return BTN_SHORT;                       // released before long threshold
    }
  }
  if (btnDown && !longFired && now - btnPressedAt >= LONG_MS) {
    longFired = true;                         // fires while still held
    return BTN_LONG;
  }
  return BTN_NONE;
}

// ------------------------- DISPLAY -----------------------------------
void header(const char* title) {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.print(title);
  oled.setCursor(98, 0);
  oled.print(WiFi.status() == WL_CONNECTED ? "WiFi" : "----");
  oled.drawFastHLine(0, 10, 128, SSD1306_WHITE);
}

void footer(const char* text) {
  oled.setTextSize(1);
  oled.setCursor(0, 56);
  oled.print(text);
}

void showRead() {
  header("READ MODE");
  oled.setTextSize(2);
  oled.setCursor(0, 16);
  oled.print(lastGear);
  oled.setTextSize(1);
  oled.setCursor(0, 36);
  oled.print(lastUid.length() ? lastUid : "Tap a gear tag");
  oled.setCursor(0, 46);
  oled.print(lastStatus);
  footer("Hold: write mode");
  oled.display();
}

void showSelect() {
  header("SELECT GEAR");
  for (uint8_t i = 0; i < GEAR_N; i++) {
    oled.setCursor(0, 14 + i * 10);
    oled.print(i == cursor ? "> " : "  ");
    oled.print(GEAR[i]);
  }
  footer("Tap:next  Hold:ok");
  oled.display();
}

void showWrite() {
  header("WRITE MODE");
  oled.setTextSize(2);
  oled.setCursor(0, 16);
  oled.print(GEAR[cursor]);
  oled.setTextSize(1);
  oled.setCursor(0, 36);
  oled.print("Tap tag to write");
  oled.setCursor(0, 46);
  oled.print(lastStatus);
  footer("Hold: cancel");
  oled.display();
}

// ------------------------- TAG I/O -----------------------------------
String uidToStr(const uint8_t* uid, uint8_t len) {
  String s;
  char b[3];
  for (uint8_t i = 0; i < len; i++) { sprintf(b, "%02X", uid[i]); s += b; }
  return s;
}

// Reads pages 4..7. Returns false on I/O error.
// out = gear name, or "BLANK" if the tag has no MS1 record.
bool readGear(char* out, size_t n) {
  uint8_t data[16];
  for (uint8_t p = 0; p < 4; p++) {
    if (!nfc.ntag2xx_ReadPage(4 + p, data + p * 4)) return false;
  }
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
  for (uint8_t p = 0; p < 4; p++) {
    if (!nfc.ntag2xx_WritePage(4 + p, data + p * 4)) return false;
  }
  char check[16];                                   // read back to verify
  return readGear(check, sizeof(check)) && strcmp(check, gear) == 0;
}

// ------------------------- ADMIN LINK --------------------------------
// Returns the admin's "check" verdict, or "OFFLINE" / "ERR <code>".
String sendToAdmin(const char* event, const String& uid, const char* gear, const char* prev) {
  if (WiFi.status() != WL_CONNECTED) return "OFFLINE";

  char body[200];
  snprintf(body, sizeof(body),
           "{\"station\":\"%s\",\"event\":\"%s\",\"uid\":\"%s\",\"gear\":\"%s\",\"prev\":\"%s\"}",
           STATION_ID, event, uid.c_str(), gear, prev);

  HTTPClient http;
  http.setTimeout(2000);
  http.begin(ADMIN_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  String resp = (code > 0) ? http.getString() : "";
  http.end();

  if (code < 200 || code >= 300) return "ERR " + String(code);

  int k = resp.indexOf("\"check\":\"");               // tiny parse, no JSON lib needed
  if (k < 0) return "SENT";
  k += 9;
  int e = resp.indexOf('"', k);
  return resp.substring(k, e);
}

// ------------------------- HANDLERS ----------------------------------
void handleReadTag(const uint8_t* uid, uint8_t len) {
  String u = uidToStr(uid, len);
  if (u == lastSeenUid && millis() - lastSeenAt < SAME_TAG_IGNORE_MS) {
    lastSeenAt = millis();
    return;                                         // same tag still on reader
  }
  lastSeenUid = u;
  lastSeenAt  = millis();
  lastUid     = u;

  if (len != 7) {
    lastGear = "NOT NTAG";
    lastStatus = "";
    showRead();
    return;
  }

  char gear[16];
  if (!readGear(gear, sizeof(gear))) {
    lastGear = "READ ERR";
    lastStatus = "Hold tag steady";
    showRead();
    return;
  }

  lastGear   = gear;
  lastStatus = "Sending...";
  showRead();
  lastStatus = "Admin: " + sendToAdmin("scan", u, gear, "");
  showRead();
}

void handleWriteTag(const uint8_t* uid, uint8_t len) {
  String u = uidToStr(uid, len);

  if (len != 7) {
    lastStatus = "Not an NTAG tag";
    showWrite();
    delay(800);
    return;
  }

  char prev[16] = "";
  readGear(prev, sizeof(prev));                     // what was on it before (for admin log)

  if (!writeGear(GEAR[cursor])) {
    lastStatus = "Write failed, retry";
    showWrite();
    delay(800);
    return;
  }

  lastStatus = "OK! Sending...";
  showWrite();
  lastStatus = "Admin: " + sendToAdmin("write", u, GEAR[cursor], prev);
  showWrite();
  delay(1200);                                      // let the user see the result

  // move on to the next item of the kit
  lastSeenUid  = u;                                 // so READ mode won't instantly resend it
  lastSeenAt   = millis();
  cursor       = (cursor + 1) % GEAR_N;
  lastStatus   = "";
  lastActivity = millis();
  mode = SELECT_MODE;
  showSelect();
}

// ------------------------- SETUP / LOOP ------------------------------
void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);

  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED not found");
  }
  header("BOOTING");
  oled.setCursor(0, 16);
  oled.print("Starting NFC...");
  oled.display();

  nfc.begin();
  uint32_t ver = nfc.getFirmwareVersion();
  if (!ver) {
    header("ERROR");
    oled.setCursor(0, 16);
    oled.print("PN532 not found.\nCheck wiring and\nDIP switch (I2C).");
    oled.display();
    while (1) delay(10);
  }
  nfc.SAMConfig();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  oled.setCursor(0, 28);
  oled.print("Connecting WiFi...");
  oled.display();
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 10000) delay(200);
  Serial.println(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "WiFi offline");

  showRead();
}

void loop() {
  BtnEvent ev = pollButton();
  uint8_t uid[7];
  uint8_t len = 0;

  switch (mode) {
    case READ_MODE:
      if (ev == BTN_LONG) {
        mode = SELECT_MODE;
        cursor = 0;
        lastActivity = millis();
        showSelect();
        return;
      }
      // short timeout keeps the button responsive
      if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len, 50)) {
        handleReadTag(uid, len);
      }
      break;

    case SELECT_MODE:
      if (ev == BTN_SHORT) {
        cursor = (cursor + 1) % GEAR_N;
        lastActivity = millis();
        showSelect();
      } else if (ev == BTN_LONG) {
        mode = WRITE_MODE;
        lastStatus = "";
        lastActivity = millis();
        showWrite();
      } else if (millis() - lastActivity > SELECT_TIMEOUT_MS) {
        mode = READ_MODE;
        showRead();
      }
      break;

    case WRITE_MODE:
      if (ev == BTN_LONG || millis() - lastActivity > SELECT_TIMEOUT_MS) {
        mode = READ_MODE;
        lastStatus = "";
        showRead();
        return;
      }
      if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len, 50)) {
        handleWriteTag(uid, len);
      }
      break;
  }
}
