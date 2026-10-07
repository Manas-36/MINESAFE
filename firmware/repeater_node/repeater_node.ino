// =====================================================================
//  Miner Safety System - REPEATER NODE (chain / mesh) - ESP-NOW version
//  v3.3: LED-matrix exit sign (MAX7219 8x32) + evacuation arrows, up to 3 gas sensors, SOS button.
//        The tested v3.1 repeater (buzzer + 1 MQ + AHT only) is kept on the git branch
//        "version/v3.1-repeater-final".
//  Board : ESP32-S3 (N16R8 module), Arduino ESP32 core 3.x
//          Tools -> Board: "ESP32S3 Dev Module", Flash Size: 16MB, PSRAM: OPI PSRAM
//          Tools -> USB CDC On Boot: Enabled (cable in the "USB" port)
//                                    Disabled (cable in the "COM"/"UART" port)
//
//  EVERYTHING TALKS ESP-NOW (direct ESP-to-ESP radio, no router needed)
//    Body units  -> repeaters     : body packets (ID + serial number + readings)
//    Repeater   <-> repeater      : hop by hop towards the main repeater
//    Main repeater -> admin       : WiFi to the hotspot, HTTP POST every second
//
//  HOW THE CHAIN WORKS (nothing to configure except the number and the role)
//    The main repeater (IS_GATEWAY 1) is hop 0 and sits on the hotspot's WiFi
//    channel. Every repeater sends a beacon every second: "I am REP-xx, N hops
//    from the main repeater, channel C, current alert". Each repeater picks the
//    neighbour with the fewest hops as its parent and becomes N+1. Data only moves
//    to repeaters closer to the main repeater. A repeater that hears nothing for 8 s
//    searches channels 1-13 until it finds the chain again (same for body units).
//    The admin's alert rides down the chain inside the beacons: every repeater
//    buzzes, and body units turn their red LED on.
//
//  PHONE TEST PAGE (no body unit needed)
//    Every repeater serves a page where a phone pretends to be a body unit:
//      Main repeater   : phone joins the same hotspot, opens  http://<repeater IP>/
//                        (the IP is printed on the Serial Monitor and shown on the
//                         admin page -> Network tab)
//      Tunnel repeater : phone joins WiFi "MINE-REP-02" (password below) and opens
//                        http://192.168.4.1/   (appears once the repeater has found the chain)
//    The fake worker's packets go through the repeater exactly like a real body's,
//    so the admin page shows them (tagged PHONE TEST) with the route they took.
//
//  Also works on a Seeed XIAO ESP32-C6 (Tools -> Board: "XIAO_ESP32C6"), built-in antenna.
//
//  WIRING
//    Buzzer (+)  -> GPIO5 on the ESP32-S3,  D10 on the XIAO ESP32-C6      Buzzer (-) -> GND
//    (active 3.3 V buzzer; for a loud 5 V buzzer use an NPN transistor, 1k to the base)
//    Gas sensor (MQ module, e.g. "Flying-Fish MQ Sensor" board):
//      VCC -> 5V (VBUS)   GND -> GND   DO -> not used
//      AO  -> 10k resistor -> GPIO4 (S3) / D2 (XIAO C6),  and that pin -> 20k resistor -> GND
//      (the divider keeps the 0-5 V sensor output safe for the 3.3 V ESP32 pin)
//    No gas sensor yet? Leave it out - the admin page shows "not connected".
//    Air temperature + humidity (AHT10 / AHT20 / AHT21 / AHT25 module, I2C address 0x38):
//      VIN/VCC -> 3V3   GND -> GND
//      SDA -> D4 (GPIO22) on the XIAO ESP32-C6,  GPIO8 on the ESP32-S3
//      SCL -> D5 (GPIO23) on the XIAO ESP32-C6,  GPIO9 on the ESP32-S3
//      (the module already has its pull-up resistors). No AHT? The admin page shows "no sensor".
//    Do not use GPIO35, 36, 37 on the N16R8 - they belong to the PSRAM.
//
//    LED matrix exit sign (MAX7219 "FC-16" 4-in-1 8x32 module), DISPLAY_ENABLED 1:
//      VCC -> 5V (VBUS)  GND -> GND
//      DIN -> D9 (GPIO20) XIAO C6 / GPIO11 S3    CS -> D3 (GPIO21) / GPIO10    CLK -> D8 (GPIO19) / GPIO12
//      Text upside down / mirrored / letters in the wrong block?  Change MATRIX_FLIP_X / MATRIX_FLIP_Y /
//      MATRIX_TYPE below (type 1 = "generic" modules wired column-wise). Garbled at 3.3 V logic on some
//      modules: feed the matrix VCC from about 4.5 V (e.g. through a 1N4007 diode from 5 V).
//    Extra gas sensors (GAS_CHANNELS 2 or 3), each AO through its own 10k / 20k divider:
//      gas 2 -> D0 (GPIO0) XIAO C6 / GPIO6 S3     gas 3 -> D1 (GPIO1) / GPIO7
//      Pick the sensor model for each channel on the admin page (Gas & air tab), e.g. MQ-4 methane,
//      MQ-7 carbon monoxide, MQ-136 hydrogen sulphide.
//    SOS button (optional): D6 (GPIO16) XIAO C6 / GPIO13 S3 -> button -> GND. Hold 1.5 s = SOS on/off.
//
//  SETUP FOR EACH BOARD
//    Main repeater (near the admin laptop):  IS_GATEWAY 1, REPEATER_NO 1
//    Repeaters in the tunnel:                IS_GATEWAY 0, REPEATER_NO 2, 3, 4 ... (all different)
// =====================================================================

#include <WiFi.h>
#include <Wire.h>
#include "esp_log.h"
#include <WebServer.h>
#include <HTTPClient.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "esp_random.h"

// ------------------------- CONFIG ------------------------------------
#define IS_GATEWAY    1                 // 1 = main repeater (WiFi to admin). 0 = repeater in the tunnel
const uint8_t REPEATER_NO = 1;          // unique number 1..99  -> shown as REP-01, REP-02 ...

// Your hotspot and laptop: copy secrets.example.h to secrets.h and fill it in
// (secrets.h is not uploaded to GitHub). Without it these placeholders are used.
#if __has_include("secrets.h")
  #include "secrets.h"
#else
const char* WIFI_SSID = "YOUR_HOTSPOT";   // only used by the main repeater
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* HUB_URL   = "http://192.168.1.100:5000/api/telemetry";   // laptop IP running admin_hub.py
#endif
#define HUB_AUTOFIND  1   // 1 = if the laptop's IP changes, search the hotspot network for admin_hub (port 5000) by itself

#define TEST_PAGE     1                 // 1 = serve the phone test page, 0 = off
const char* TEST_AP_PASS = "minesafe";  // password of the tunnel repeaters' test WiFi (8+ chars)
#define USE_EXTERNAL_ANTENNA 0          // XIAO ESP32-C6 only: 1 = antenna on the u.FL socket (fit it first!)

#if CONFIG_IDF_TARGET_ESP32C6
  #define BUZZER_PIN     18             // Seeed XIAO ESP32-C6: pin D10
#else
  #define BUZZER_PIN     5              // ESP32-S3 N16R8: GPIO5
#endif
// BUZZER TYPE - if you hear nothing (or only a tiny click), change these:
#define BUZZER_PASSIVE   0    // 0 = ACTIVE buzzer (beeps by itself on DC, usually has a sticker / sealed bottom)
                              // 1 = PASSIVE buzzer (open bottom / green board; needs a tone - only clicks on DC)
#define BUZZER_ACTIVE_LOW 0   // 1 = 3-pin buzzer MODULE that beeps when the I/O pin is LOW (many "low level trigger" modules)
#define BUZZER_FREQ      2700 // tone for a passive buzzer, Hz

#define GAS_ENABLED      1    // 1 = read an MQ gas sensor (admin page works out the gases), 0 = no gas sensor
#if CONFIG_IDF_TARGET_ESP32C6
  #define GAS_PIN        2    // XIAO ESP32-C6: D2
#else
  #define GAS_PIN        4    // ESP32-S3: GPIO4
#endif
#define GAS_DIVIDER        1.5f         // 10k + 20k divider: sensor mV = pin mV x 1.5
#define GAS_WARMUP_MS      60000        // MQ heater needs ~1 min before readings mean anything
#define GAS_LOCAL_RISE_MV  1000         // fail-safe: beeps fast by itself when the reading rises this much
                                        // above its own clean-air level (learned after warm-up)
#define GAS_EVENT_STEP_MV  300          // tunnel repeaters report at once when gas rises this much

#define GAS_CHANNELS     1    // how many MQ gas sensors are fitted: 1, 2 or 3 (channel 1 = GAS_PIN above)
#if CONFIG_IDF_TARGET_ESP32C6
  #define GAS2_PIN       0    // XIAO ESP32-C6: D0
  #define GAS3_PIN       1    // XIAO ESP32-C6: D1
#else
  #define GAS2_PIN       6    // ESP32-S3: GPIO6
  #define GAS3_PIN       7    // ESP32-S3: GPIO7
#endif

#define DISPLAY_ENABLED  1    // 1 = MAX7219 8x32 LED matrix exit sign fitted (shows nothing harmful if it is missing)
#if CONFIG_IDF_TARGET_ESP32C6
  #define MX_DIN         20   // XIAO ESP32-C6: D9
  #define MX_CS          21   // XIAO ESP32-C6: D3
  #define MX_CLK         19   // XIAO ESP32-C6: D8
  #define SOS_PIN        16   // XIAO ESP32-C6: D6
#else
  #define MX_DIN         11
  #define MX_CS          10
  #define MX_CLK         12
  #define SOS_PIN        13
#endif
#define MATRIX_MODULES   4    // 4 x 8x8 = 32 columns
#define MATRIX_TYPE      0    // 0 = FC-16 modules (most common blue 4-in-1 boards), 1 = "generic" column-wise modules
#define MATRIX_FLIP_X    0    // 1 = text comes out mirrored left-right
#define MATRIX_FLIP_Y    0    // 1 = text is upside down
#define MATRIX_REVERSE   0    // 1 = the four blocks show their parts in the wrong order
#define SOS_ENABLED      1    // 1 = SOS button on SOS_PIN (hold 1.5 s)

#define AHT_ENABLED      1    // 1 = read an AHT10/AHT20/AHT25 air temperature + humidity sensor, 0 = none
#if CONFIG_IDF_TARGET_ESP32C6
  #define AHT_SDA        22   // XIAO ESP32-C6: D4
  #define AHT_SCL        23   // XIAO ESP32-C6: D5
#else
  #define AHT_SDA        8    // ESP32-S3: GPIO8 (same I2C pins as the body unit)
  #define AHT_SCL        9    // ESP32-S3: GPIO9
#endif
#define AHT_ADDR         0x38
#define AHT_EVERY_MS     2000           // one reading every 2 s
#define AHT_EVENT_STEP   100            // tunnel repeaters report at once when air temp moves 1.00 C

#define BEACON_MS        1000
#define STATUS_MS        5000
#define POST_MS          1000
#define NEIGHBOR_TTL_MS  6000
#define LOST_MS          8000           // no beacon this long -> search channels (tunnel repeaters)
#define SCAN_DWELL_MS    1300           // listen this long per channel while searching
#define MIN_LINK_RSSI    -92            // ignore neighbours weaker than this
#define MAX_HOPS         15
#define MAX_BUFFER       30
// ---------------------------------------------------------------------

// ===== shared packet format (same in body_node.ino) ====================
#define MS_VER 3
enum : uint8_t { MS_TELEM = 1, MS_BEACON = 10, MS_UP = 11 };
// body flag bits (must match admin_hub.py)
enum : uint16_t { BF_FALL = 1, BF_NOMOTION = 2, BF_IMPACT = 4, BF_SOS = 8, BF_MPU_FAULT = 16,
                  BF_TEMP_FAULT = 32, BF_ALERT_LED = 64, BF_TEST = 128 };

struct __attribute__((packed)) MsTelem {        // body -> repeaters
  char     magic[2];      // 'M','S'
  uint8_t  ver, type;
  char     node[10];
  uint16_t boot;
  uint32_t seq;
  int16_t  tObj, tAmb;    // 0.01 C
  int16_t  ax, ay, az;    // milli-g
  int16_t  gx, gy, gz;    // 0.1 deg/s
  uint16_t flags;
  uint32_t uptime;
  uint8_t  nearRep;
  int8_t   nearRssi;
  uint16_t hum;           // 0.01 % RH (0xFFFF = none)
  uint16_t steps;         // step counter since power-on (for the map)
  int16_t  head;          // heading from the gyro, 0.1 deg, 0 = direction at power-on (0x7FFF = none)
  int16_t  alt;           // height from the pressure sensor, dm, relative to power-on (0x7FFF = none)
  uint8_t  hr;            // heart rate, beats per minute (0 = none)
  uint8_t  spo2;          // blood oxygen %, estimate (0 = none)
};
struct __attribute__((packed)) MsBeacon {       // repeater -> everyone, every second
  char     magic[2];
  uint8_t  ver, type;
  uint8_t  rep, hop, espCh;
  uint32_t alertId;
  uint8_t  level;
  char     target[10];
};
struct __attribute__((packed)) MsStatus {
  uint8_t  rep, hop, parent;
  int8_t   parentRssi;
  uint32_t alertId;
  uint8_t  buzzing;
  uint32_t uptime;
  uint16_t statusSeq;
  uint16_t bodies;
  uint8_t  neighbors;
  uint16_t gasMv;
  uint8_t  gasFlags;      // bit0 warming up, bit1 local alarm, bit2 sensor missing
  int16_t  airT;          // air temperature from the AHT, 0.01 C (0x7FFF = no sensor)
  uint16_t airH;          // air humidity from the AHT, 0.01 % RH (0xFFFF = no sensor)
  // v3.3
  uint16_t gas2Mv, gas3Mv;  // extra gas channels, mV (0xFFFF = channel not fitted)
  uint8_t  gasFlags2, gasFlags3;
  uint8_t  repFlags;      // bit0 SOS active, bit1 display fitted
  uint8_t  guideCode;     // what the exit sign shows (see GUIDE codes)
  uint32_t guideId;       // evacuation guide this repeater is showing
};
#define MS_STATUS_V2_LEN  21   // V2 repeaters: no airT / airH
#define MS_STATUS_V31_LEN 25   // v3.1 repeaters: no extra gas channels / SOS / guide
// evacuation guide, sent by the hub and carried down the chain at the end of every beacon
struct __attribute__((packed)) GuideEntry { uint8_t rep, code; uint16_t dist; };   // dist in metres
struct __attribute__((packed)) MsGuideHdr { char tag[2]; uint32_t id; uint8_t evac, n; };
#define GUIDE_MAX 40
// guide codes: what this repeater's sign shows (low 4 bits) + 0x10 = this repeater is inside the danger zone
enum : uint8_t { G_NONE = 0, G_LEFT = 1, G_RIGHT = 2, G_UP = 3, G_HERE = 4, G_NOWAY = 5, G_DANGER = 0x10 };
struct __attribute__((packed)) MsUpHdr {
  char     magic[2];
  uint8_t  ver, type;
  uint8_t  senderHop;     // hop count of the repeater that sent this copy
  uint8_t  kind;          // 1 = body telemetry, 2 = repeater status
  int8_t   bodyRssi;      // body -> first repeater signal
  uint8_t  pathLen;
  uint8_t  path[8];       // repeater numbers travelled, first = where the body was heard
};
enum : uint8_t { UP_TELEM = 1, UP_STATUS = 2 };
struct RxPacket { uint8_t len; uint8_t data[250]; int8_t rssi; };
struct Glyph { char c; uint8_t w; uint8_t col[5]; };     // LED-matrix font character
struct Neighbor { uint8_t rep, hop; int8_t rssi; uint32_t seen; };
// (types live up here: the Arduino IDE declares every function at the top of the sketch)
// =====================================================================

// ===== ESP-NOW radio ===================================================
const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
QueueHandle_t rxQueue;
volatile uint32_t rxCount = 0, txFail = 0;
uint8_t channel = 1;

void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len < 4 || len > 250 || data[0] != 'M' || data[1] != 'S' || data[2] != MS_VER) return;
  RxPacket p;
  p.len = len;
  memcpy(p.data, data, len);
  p.rssi = info->rx_ctrl ? info->rx_ctrl->rssi : -100;
  rxCount = rxCount + 1;
  xQueueSend(rxQueue, &p, 0);
}

bool radioBegin() {
  rxQueue = xQueueCreate(32, sizeof(RxPacket));
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(onEspNowRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = 0;                    // = the channel we are on
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  return esp_now_add_peer(&peer) == ESP_OK;
}

void radioSend(const void* data, size_t n) {
  if (esp_now_send(BROADCAST, (const uint8_t*)data, n) != ESP_OK) txFail = txFail + 1;
}

void setChannel(uint8_t ch) {
  channel = ch;
  esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
}
// =====================================================================

// ------------------------- state -------------------------------------
uint8_t  myHop = IS_GATEWAY ? 0 : 255;
uint8_t  parent = 0;
int8_t   parentRssi = -127;
uint32_t alertId = 0;
uint8_t  alertLevel = 0;
char     alertTarget[11] = "*";
bool     beaconNow = false;
uint32_t bodiesHeard = 0, lastBeaconHeard = 0, lastHop = 0;
uint32_t lastHubOk = 0, hubPosts = 0, hubErrors = 0;
int      lastHubCode = 0;
uint16_t statusSeq = 0;
uint16_t gasMv = 0;
uint8_t  gasFlags = GAS_ENABLED ? 1 : 4;
uint16_t gasMvX[3] = {0, 0xFFFF, 0xFFFF};   // all channels (index 0 = gasMv)
uint8_t  gasFlagsX[3] = {1, 4, 4};
bool     sosActive = false;
bool     displayOk = false;
uint32_t guideId = 0;                   // evacuation guide (0 = none yet)
uint8_t  guideEvac = 0;                 // 1 = evacuation in progress
uint8_t  guideN = 0;
GuideEntry guideTab[GUIDE_MAX];
uint8_t  myCode = G_NONE;               // this repeater's own instruction
uint16_t myDist = 0;
int16_t  airT = 0x7FFF;                 // AHT air temperature, 0.01 C (0x7FFF = no sensor)
uint16_t airH = 0xFFFF;                 // AHT air humidity, 0.01 % RH (0xFFFF = no sensor)
bool     statusNow = false;
Neighbor nbr[16];
uint32_t seenHash[64];
uint8_t  seenPos = 0;
String   hubPackets[MAX_BUFFER];  uint8_t nPackets = 0;   // main repeater only
String   hubStatuses[16];         uint8_t nStatuses = 0;

uint32_t fnv(const uint8_t* d, size_t n) {
  uint32_t h = 2166136261u;
  while (n--) { h ^= *d++; h *= 16777619u; }
  return h;
}
bool alreadySeen(uint32_t h) {
  for (uint32_t s : seenHash) if (s == h) return true;
  seenHash[seenPos++ % 64] = h;
  return false;
}
String repName(uint8_t n) { char b[8]; snprintf(b, sizeof(b), "REP-%02u", n); return b; }

void copyTelem(MsTelem& t, const uint8_t* data, int len) {
  memset(&t, 0, sizeof(t));
  t.hum = 0xFFFF;
  t.head = 0x7FFF;                      // older body units don't send position data
  t.alt = 0x7FFF;
  memcpy(&t, data, len < (int)sizeof(MsTelem) ? len : sizeof(MsTelem));
}

// ------------------------- gas ---------------------------------------
// Up to 3 MQ sensors, each on its own analog pin through a 10k / 20k divider.
// Channel 1 also keeps the old gasMv / gasFlags names (v3.1 status fields).
const uint8_t GAS_PINS[3] = {GAS_PIN, GAS2_PIN, GAS3_PIN};
struct GasCh { bool present = false; uint32_t lastCheck = 0; float base = 0; uint16_t lastReported = 0; };
GasCh gasCh[3];

void readGasChannel(uint8_t c, uint32_t now) {
  GasCh& g = gasCh[c];
  uint8_t pin = GAS_PINS[c];
  // Is a sensor really connected? An empty pin "floats" and reads random voltages (often
  // 1.5-2.5 V), which would look like gas. Every 5 s pull the pin down for a moment: an empty
  // pin drops to ~0 V, a pin driven by the sensor through the divider stays up.
  if (!g.lastCheck || now - g.lastCheck > 5000) {
    g.lastCheck = now | 1;
    pinMode(pin, INPUT_PULLDOWN);
    delay(2);
    uint32_t pd = 0;
    for (int i = 0; i < 8; i++) pd += analogReadMilliVolts(pin);
    pinMode(pin, INPUT);
    analogSetPinAttenuation(pin, ADC_11db);
    bool was = g.present;
    g.present = pd / 8 > 40;
    if (g.present != was) Serial.printf("Gas sensor %u %s\n", c + 1, g.present ? "connected" : "NOT connected (pin empty)");
  }
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(pin);
  uint16_t mv = g.present ? (uint16_t)(sum / 16 * GAS_DIVIDER) : 0;
  uint8_t f = 0;
  if (now < GAS_WARMUP_MS) f |= 1;
  if (!g.present || mv < 30) f |= 4;                         // sensor not connected
  // clean-air level: the lowest reading after warm-up, slowly following real drift upwards
  if (f & 5) g.base = 0;
  else if (g.base == 0 || mv < g.base) g.base = mv;
  else g.base += (mv - g.base) * 0.0005f;                    // ~15 min to follow a slow drift
  if (!(f & 5) && g.base > 0 && mv >= g.base + GAS_LOCAL_RISE_MV) f |= 2;
  if ((f & 2) != (gasFlagsX[c] & 2) || (!(f & 1) && mv > g.lastReported + GAS_EVENT_STEP_MV)) {
    statusNow = true;
    g.lastReported = mv;
  }
  if (mv + GAS_EVENT_STEP_MV < g.lastReported) g.lastReported = mv;
  if ((f & 2) && !(gasFlagsX[c] & 2)) Serial.printf("GAS %u HIGH %u mV - local alarm\n", c + 1, mv);
  gasMvX[c] = mv;
  gasFlagsX[c] = f;
}

void readGas(uint32_t now) {
#if GAS_ENABLED
  static uint32_t last = 0;
  if (now - last < 500) return;
  last = now;
  for (uint8_t c = 0; c < GAS_CHANNELS && c < 3; c++) readGasChannel(c, now);
  gasMv = gasMvX[0];
  gasFlags = gasFlagsX[0];
#endif
}

bool anyGasAlarm() {
  for (uint8_t c = 0; c < GAS_CHANNELS && c < 3; c++) if (gasFlagsX[c] & 2) return true;
  return false;
}

// ------------------------- AHT air temperature + humidity -------------
// AHT10 / AHT20 / AHT21 / AHT25 all answer at 0x38 with the same 0xAC measure command.
// Driver written here (no library): start a measurement, come back 80 ms later, read 6 bytes.
// Never blocks the radio for more than the I2C transfer itself.
bool ahtCmd(uint8_t a, uint8_t b, uint8_t c) {
  Wire.beginTransmission(AHT_ADDR);
  Wire.write(a); Wire.write(b); Wire.write(c);
  return Wire.endTransmission() == 0;
}

int ahtStatus() {                       // -1 = nobody answers at 0x38
  if (Wire.requestFrom((uint8_t)AHT_ADDR, (uint8_t)1) != 1) return -1;
  return Wire.read();
}

bool ahtInit() {
  Wire.beginTransmission(AHT_ADDR);
  if (Wire.endTransmission() != 0) return false;            // not connected
  int s = ahtStatus();
  if (s < 0) return false;
  if (!(s & 0x08)) {                                        // not calibrated yet: load the factory calibration
    if (!ahtCmd(0xBE, 0x08, 0x00)) ahtCmd(0xE1, 0x08, 0x00);   // AHT20/25 use 0xBE, the older AHT10 uses 0xE1
    delay(10);
  }
  return true;
}

void readAir(uint32_t now) {
#if AHT_ENABLED
  static uint8_t  state = 0;            // 0 = not found, 1 = idle, 2 = measuring
  static uint32_t t0 = 0, lastTry = 0;
  static uint8_t  fails = 0;
  static int16_t  lastReported = 0x7FFF;
  if (state == 0) {
    if (lastTry && now - lastTry < 10000) return;           // look for the sensor every 10 s
    lastTry = now | 1;
    if (ahtInit()) { state = 1; fails = 0; t0 = 0; Serial.println("AHT air sensor found (0x38)"); }
    return;
  }
  if (state == 1) {
    if (t0 && now - t0 < AHT_EVERY_MS) return;
    t0 = now;
    if (ahtCmd(0xAC, 0x33, 0x00)) state = 2;
    else fails++;
  } else if (now - t0 >= 80) {                              // measurement takes ~75 ms
    uint8_t d[6];
    bool ok = Wire.requestFrom((uint8_t)AHT_ADDR, (uint8_t)6) == 6;
    for (int i = 0; i < 6; i++) d[i] = ok ? Wire.read() : 0;
    if (ok && (d[0] & 0x80)) { if (now - t0 < 300) return; ok = false; }   // still busy: wait a little more
    state = 1;
    if (ok) {
      uint32_t rh = ((uint32_t)d[1] << 12) | ((uint32_t)d[2] << 4) | (d[3] >> 4);
      uint32_t tr = (((uint32_t)d[3] & 0x0F) << 16) | ((uint32_t)d[4] << 8) | d[5];
      float h = rh * 100.0f / 1048576.0f, t = tr * 200.0f / 1048576.0f - 50.0f;
      if (h >= 0 && h <= 100 && t > -40 && t < 85 && !(rh == 0 && tr == 0)) {
        airT = (int16_t)lroundf(t * 100); airH = (uint16_t)lroundf(h * 100); fails = 0;
        if (lastReported == 0x7FFF || abs(airT - lastReported) >= AHT_EVENT_STEP) { statusNow = true; lastReported = airT; }
      } else ok = false;
    }
    if (!ok) fails++;
  }
  if (fails >= 5) {                                         // unplugged: show "no sensor" and look again
    if (airT != 0x7FFF) Serial.println("AHT air sensor lost - check SDA/SCL/3V3/GND");
    airT = 0x7FFF; airH = 0xFFFF; state = 0; lastReported = 0x7FFF; statusNow = true;
  }
#endif
}

String airJson(int16_t t, uint16_t h) {                     // ,"air_t":31.25,"air_h":72.40  (null = no sensor)
  char b[48];
  if (t == 0x7FFF || h == 0xFFFF) return ",\"air_t\":null,\"air_h\":null";
  snprintf(b, sizeof(b), ",\"air_t\":%.2f,\"air_h\":%.2f", t / 100.0f, h / 100.0f);
  return b;
}

// ------------------------- routing -----------------------------------
uint8_t neighborCount(uint32_t now) {
  uint8_t c = 0;
  for (auto& n : nbr) if (n.rep && now - n.seen < NEIGHBOR_TTL_MS) c++;
  return c;
}

void recomputeRoute(uint32_t now) {
  if (IS_GATEWAY) return;
  uint8_t bestHop = 255, bestRep = 0;
  int8_t bestRssi = -127;
  for (auto& n : nbr) {
    if (!n.rep || now - n.seen > NEIGHBOR_TTL_MS || n.rssi < MIN_LINK_RSSI || n.hop >= MAX_HOPS) continue;
    if (n.hop < bestHop || (n.hop == bestHop && n.rssi > bestRssi)) { bestHop = n.hop; bestRep = n.rep; bestRssi = n.rssi; }
  }
  uint8_t newHop = bestRep ? bestHop + 1 : 255;
  if (newHop != myHop || bestRep != parent) {
    Serial.printf("Route: %s\n", bestRep ? (repName(bestRep) + ", " + String(newHop) + " hops to main").c_str() : "NONE");
    if (newHop < myHop) beaconNow = true;
  }
  myHop = newHop; parent = bestRep; parentRssi = bestRssi;
}

void adoptAlert(uint32_t id, uint8_t level, const char* target) {
  if (id == alertId && level == alertLevel) return;
  alertId = id; alertLevel = level;
  strncpy(alertTarget, target[0] ? target : "*", 10);
  alertTarget[10] = 0;
  beaconNow = true;                     // pass it down the chain right away
  Serial.printf("ALERT %s id=%lu target=%s\n", level ? "ON" : "CLEARED", (unsigned long)id, alertTarget);
}

// the evacuation guide at the end of a beacon (or from the hub): adopt it if it is newer
void lookupMyGuide() {
  myCode = G_NONE; myDist = 0;
  for (uint8_t i = 0; i < guideN; i++)
    if (guideTab[i].rep == REPEATER_NO) { myCode = guideTab[i].code; myDist = guideTab[i].dist; }
}

void adoptGuide(uint32_t id, uint8_t evac, uint8_t n, const GuideEntry* e) {
  if (id == guideId) return;
  guideId = id; guideEvac = evac; guideN = n > GUIDE_MAX ? GUIDE_MAX : n;
  memcpy(guideTab, e, guideN * sizeof(GuideEntry));
  lookupMyGuide();
  beaconNow = true;                     // pass it down the chain right away
  statusNow = true;
  Serial.printf("GUIDE %lu: %s, %u repeaters; this one shows code %u, %u m\n", (unsigned long)id,
                evac ? "EVACUATE" : "normal", guideN, myCode, myDist);
}

void onGuideBlock(const uint8_t* d, int len) {
  if (len < (int)sizeof(MsGuideHdr)) return;
  MsGuideHdr h; memcpy(&h, d, sizeof(h));
  if (h.tag[0] != 'G' || h.tag[1] != 'D') return;
  uint8_t n = h.n > GUIDE_MAX ? GUIDE_MAX : h.n;
  if (len < (int)(sizeof(h) + n * sizeof(GuideEntry))) return;
  if (h.id > guideId) adoptGuide(h.id, h.evac, n, (const GuideEntry*)(d + sizeof(h)));
}

void onBeacon(const MsBeacon& b, int8_t rssi, uint32_t now) {
  if (b.hop >= 255) return;                                  // it has no route itself
  lastBeaconHeard = now;
  Neighbor* slot = nullptr;
  for (auto& n : nbr) if (n.rep == b.rep) slot = &n;
  if (!slot) for (auto& n : nbr) if (!n.rep || now - n.seen > NEIGHBOR_TTL_MS * 2) { slot = &n; break; }
  if (slot) *slot = {b.rep, b.hop, rssi, now};
  recomputeRoute(now);
  if (IS_GATEWAY) return;                                    // the hub is the main repeater's source of truth
  char tgt[11] = {0};
  memcpy(tgt, b.target, 10);
  if (b.alertId > alertId || (b.alertId == alertId && b.level != alertLevel)) adoptAlert(b.alertId, b.level, tgt);
  if (b.rep == parent && b.espCh && b.espCh != channel) {   // follow the main repeater's channel
    Serial.printf("Moving to channel %u\n", b.espCh);
    setChannel(b.espCh);
  }
}

// tunnel repeaters: if the chain goes quiet, search channels 1..13 for it
void channelSearch(uint32_t now) {
  if (IS_GATEWAY || now - lastBeaconHeard < LOST_MS) return;
  if (now - lastHop > SCAN_DWELL_MS) {
    lastHop = now;
    setChannel(channel % 13 + 1);
    Serial.printf("Searching for the chain... channel %u\n", channel);
  }
}

// ------------------------- JSON for the hub (main repeater) ------------
String pathJson(const uint8_t* path, uint8_t len) {
  String s = "[";
  for (int i = 0; i < len; i++) { if (i) s += ","; s += "\"" + repName(path[i]) + "\""; }
  return s + "]";
}

void queueTelemetryForHub(const MsTelem& t, int8_t bodyRssi, const uint8_t* path, uint8_t pathLen) {
  char node[11] = {0};
  for (int i = 0; i < 10 && t.node[i]; i++)
    node[i] = isalnum((unsigned char)t.node[i]) || t.node[i] == '-' || t.node[i] == '_' ? t.node[i] : '?';
  char js[440];
  snprintf(js, sizeof(js),
           "{\"node\":\"%s\",\"seq\":%lu,\"bt\":%u,\"to\":%d,\"ta\":%d,\"ax\":%d,\"ay\":%d,\"az\":%d,"
           "\"gx\":%d,\"gy\":%d,\"gz\":%d,\"fl\":%u,\"up\":%lu,\"rssi\":%d,\"near\":\"%s\",\"near_rssi\":%d,\"hu\":%u,"
           "\"st\":%u,\"hd\":%d,\"al\":%d,\"hr\":%u,\"sp\":%u,\"path\":",
           node, (unsigned long)t.seq, t.boot, t.tObj, t.tAmb, t.ax, t.ay, t.az, t.gx, t.gy, t.gz,
           t.flags, (unsigned long)t.uptime, bodyRssi, t.nearRep ? repName(t.nearRep).c_str() : "", t.nearRssi, t.hum,
           t.steps, t.head, t.alt, t.hr, t.spo2);
  String s = String(js) + pathJson(path, pathLen) + "}";
  if (nPackets == MAX_BUFFER) { for (int i = 1; i < MAX_BUFFER; i++) hubPackets[i - 1] = hubPackets[i]; nPackets--; }
  hubPackets[nPackets++] = s;
}

void queueStatusForHub(const MsStatus& st, const uint8_t* path, uint8_t pathLen) {
  char js[400];
  snprintf(js, sizeof(js),
           "{\"id\":\"%s\",\"hop\":%u,\"parent\":\"%s\",\"prssi\":%d,\"alert_id\":%lu,\"buzzing\":%s,"
           "\"up\":%lu,\"bodies\":%u,\"nbrs\":%u,\"gas_mv\":%u,\"gas_warm\":%s,\"gas_alarm\":%s,\"gas_missing\":%s,\"path\":",
           repName(st.rep).c_str(), st.hop, st.parent ? repName(st.parent).c_str() : "", st.parentRssi,
           (unsigned long)st.alertId, st.buzzing ? "true" : "false", (unsigned long)st.uptime, st.bodies, st.neighbors,
           st.gasMv, st.gasFlags & 1 ? "true" : "false", st.gasFlags & 2 ? "true" : "false", st.gasFlags & 4 ? "true" : "false");
  String s = String(js) + pathJson(path, pathLen) + airJson(st.airT, st.airH);
  // all gas channels (ch 1 repeated, so the hub can treat every channel the same way)
  s += ",\"gas\":[";
  const uint16_t mvs[3] = {st.gasMv, st.gas2Mv, st.gas3Mv};
  const uint8_t  fls[3] = {st.gasFlags, st.gasFlags2, st.gasFlags3};
  for (int c = 0; c < 3; c++) {
    if (c && mvs[c] == 0xFFFF) continue;
    char g[110];
    snprintf(g, sizeof(g), "%s{\"ch\":%d,\"mv\":%u,\"warm\":%s,\"alarm\":%s,\"missing\":%s}", c ? "," : "", c + 1, mvs[c],
             fls[c] & 1 ? "true" : "false", fls[c] & 2 ? "true" : "false", fls[c] & 4 ? "true" : "false");
    s += g;
  }
  char x[96];
  snprintf(x, sizeof(x), "],\"sos\":%s,\"disp\":%s,\"gcode\":%u,\"gid\":%lu}", st.repFlags & 1 ? "true" : "false",
           st.repFlags & 2 ? "true" : "false", st.guideCode, (unsigned long)st.guideId);
  s += x;
  for (int i = 0; i < nStatuses; i++)                         // keep only the newest per repeater
    if (hubStatuses[i].indexOf("\"id\":\"" + repName(st.rep) + "\"") >= 0) { hubStatuses[i] = s; return; }
  if (nStatuses < 16) hubStatuses[nStatuses++] = s;
}

// ------------------------- uplink ------------------------------------
void sendUp(uint8_t kind, const void* inner, uint8_t innerLen, int8_t bodyRssi, const uint8_t* path, uint8_t pathLen) {
  uint8_t buf[200];
  MsUpHdr h = {};
  h.magic[0] = 'M'; h.magic[1] = 'S'; h.ver = MS_VER; h.type = MS_UP;
  h.senderHop = myHop; h.kind = kind; h.bodyRssi = bodyRssi;
  h.pathLen = pathLen > 8 ? 8 : pathLen;
  memcpy(h.path, path, h.pathLen);
  if (sizeof(h) + innerLen > sizeof(buf)) return;
  memcpy(buf, &h, sizeof(h));
  memcpy(buf + sizeof(h), inner, innerLen);
  radioSend(buf, sizeof(h) + innerLen);
}

void onUp(const uint8_t* pl, uint8_t n) {
  if (n < sizeof(MsUpHdr)) return;
  MsUpHdr h;
  memcpy(&h, pl, sizeof(h));
  const uint8_t* inner = pl + sizeof(h);
  uint8_t innerLen = n - sizeof(h);
  if (!IS_GATEWAY && (myHop == 255 || myHop >= h.senderHop)) return;   // only move towards the main repeater
  if (alreadySeen(fnv(inner, innerLen))) return;

  uint8_t path[8];
  uint8_t len = h.pathLen > 8 ? 8 : h.pathLen;
  memcpy(path, h.path, len);
  if (len < 8) path[len++] = REPEATER_NO;

  if (IS_GATEWAY) {
    if (h.kind == UP_TELEM && innerLen >= 30) {
      MsTelem t; copyTelem(t, inner, innerLen);
      queueTelemetryForHub(t, h.bodyRssi, path, len);
    } else if (h.kind == UP_STATUS && innerLen >= MS_STATUS_V2_LEN) {
      MsStatus st = {};                                      // older repeaters send fewer fields
      st.airT = 0x7FFF; st.airH = 0xFFFF; st.gas2Mv = st.gas3Mv = 0xFFFF;
      memcpy(&st, inner, innerLen < sizeof(st) ? innerLen : sizeof(st));
      queueStatusForHub(st, path, len);
    }
  } else {
    sendUp(h.kind, inner, innerLen, h.bodyRssi, path, len);          // pass it on
  }
}

MsStatus myStatus() {
  MsStatus st = {};
  st.rep = REPEATER_NO; st.hop = myHop; st.parent = parent; st.parentRssi = parentRssi;
  st.alertId = alertId; st.buzzing = alertLevel; st.uptime = millis() / 1000;
  st.statusSeq = ++statusSeq; st.bodies = bodiesHeard; st.neighbors = neighborCount(millis());
  st.gasMv = gasMv; st.gasFlags = gasFlags;
  st.airT = airT; st.airH = airH;
  st.gas2Mv = GAS_CHANNELS >= 2 ? gasMvX[1] : 0xFFFF; st.gasFlags2 = gasFlagsX[1];
  st.gas3Mv = GAS_CHANNELS >= 3 ? gasMvX[2] : 0xFFFF; st.gasFlags3 = gasFlagsX[2];
  st.repFlags = (sosActive ? 1 : 0) | (displayOk ? 2 : 0);
  st.guideCode = myCode; st.guideId = guideId;
  return st;
}

// a body packet heard by this repeater (over the radio, or from the phone test page)
void processBody(const MsTelem& t, int8_t rssi) {
  if (alreadySeen(fnv((const uint8_t*)&t, sizeof(MsTelem)))) return;
  bodiesHeard++;
  uint8_t path[1] = {REPEATER_NO};
  if (IS_GATEWAY) queueTelemetryForHub(t, rssi, path, 1);
  else if (myHop != 255) sendUp(UP_TELEM, &t, sizeof(MsTelem), rssi, path, 1);
  char node[11] = {0}; memcpy(node, t.node, 10);
  Serial.printf("Body %s #%lu rssi %d flags 0x%02X%s %s\n", node, (unsigned long)t.seq, rssi, t.flags,
                t.flags & BF_TEST ? " (phone test)" : "",
                IS_GATEWAY || myHop != 255 ? "" : "(no route to main repeater yet!)");
}

void handleRadio(uint32_t now) {
  RxPacket p;
  while (xQueueReceive(rxQueue, &p, 0) == pdTRUE) {
    uint8_t type = p.data[3];
    if (type == MS_BEACON && p.len >= sizeof(MsBeacon)) {
      MsBeacon b; memcpy(&b, p.data, sizeof(b));
      if (b.rep != REPEATER_NO) {
        onBeacon(b, p.rssi, now);
        if (!IS_GATEWAY && p.len > sizeof(MsBeacon)) onGuideBlock(p.data + sizeof(MsBeacon), p.len - sizeof(MsBeacon));
      }
    } else if (type == MS_UP) {
      onUp(p.data, p.len);
    } else if (type == MS_TELEM && p.len >= 30) {
      MsTelem t;
      copyTelem(t, p.data, p.len);
      processBody(t, p.rssi);
    }
  }
}

void sendBeacon() {
  MsBeacon b = {};
  b.magic[0] = 'M'; b.magic[1] = 'S'; b.ver = MS_VER; b.type = MS_BEACON;
  b.rep = REPEATER_NO; b.hop = myHop; b.espCh = channel;
  b.alertId = alertId; b.level = alertLevel;
  strncpy(b.target, alertTarget, sizeof(b.target));
  uint8_t buf[250];
  size_t n = sizeof(b);
  memcpy(buf, &b, n);
  if (guideId) {                                             // + the evacuation guide for the whole chain
    MsGuideHdr h = {{'G', 'D'}, guideId, guideEvac, guideN};
    memcpy(buf + n, &h, sizeof(h)); n += sizeof(h);
    memcpy(buf + n, guideTab, guideN * sizeof(GuideEntry)); n += guideN * sizeof(GuideEntry);
  }
  radioSend(buf, n);
}

// ------------------------- hub (main repeater only) ------------------
long jsonInt(const String& s, const char* key, long def) {
  int k = s.indexOf(key);
  if (k < 0) return def;
  k = s.indexOf(':', k);
  return k < 0 ? def : s.substring(k + 1).toInt();
}
String jsonStr(const String& s, const char* key) {
  int k = s.indexOf(key);
  if (k < 0) return "";
  k = s.indexOf('"', s.indexOf(':', k));
  int e = s.indexOf('"', k + 1);
  return (k < 0 || e < 0) ? "" : s.substring(k + 1, e);
}

// ---- hub auto-find: the phone hotspot gives the laptop a new IP now and then ----
String   hubUrl;                 // the URL in use (starts as HUB_URL)
uint8_t  hubFailRun = 0;         // failed posts in a row
int      findStep = -1;          // -1 = not searching, else index of the next address to try
uint16_t hubPort() { int a = hubUrl.indexOf(':', 7), b = hubUrl.indexOf('/', 7); return a > 0 ? hubUrl.substring(a + 1, b).toInt() : 80; }
String   hubPath() { int b = hubUrl.indexOf('/', 7); return b > 0 ? hubUrl.substring(b) : "/"; }
uint8_t  hubLastOctet() { int b = hubUrl.indexOf(':', 7); String h = hubUrl.substring(7, b); return h.substring(h.lastIndexOf('.') + 1).toInt(); }

// one address per call, so ESP-NOW keeps running while it searches (~30 s for a whole /24 network)
void hubFindStep() {
  if (findStep < 0 || WiFi.status() != WL_CONNECTED) return;
  IPAddress me = WiFi.localIP();
  uint8_t first = hubLastOctet();
  int host = findStep == 0 ? first : findStep;               // try the old last number first (it usually stays)
  findStep++;
  if (findStep > 254) { findStep = 0; Serial.println("Hub not found on this network - searching again (is admin_hub.py running? firewall?)"); }
  if (host == 0 || (findStep > 1 && host == first) || host == me[3] || host == 255) return;
  IPAddress ip(me[0], me[1], me[2], host);
  NetworkClient c;
  if (c.connect(ip, hubPort(), 120)) {
    c.stop();
    hubUrl = "http://" + ip.toString() + ":" + String(hubPort()) + hubPath();
    Serial.printf("Found something on port %u at %s -> using hub %s\n", hubPort(), ip.toString().c_str(), hubUrl.c_str());
    findStep = -1; hubFailRun = 0;
  }
}

void postToHub() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (hubUrl.length() == 0) hubUrl = HUB_URL;
  if (findStep >= 0) return;                                  // searching for the laptop
  MsStatus me = myStatus();
  uint8_t mePath[1] = {REPEATER_NO};
  queueStatusForHub(me, mePath, 1);

  String body = "{\"repeater\":\"" + repName(REPEATER_NO) + "\",\"gateway\":true,\"packets\":[";
  for (int i = 0; i < nPackets; i++) { if (i) body += ","; body += hubPackets[i]; }
  body += "],\"statuses\":[";
  for (int i = 0; i < nStatuses; i++) { if (i) body += ","; body += hubStatuses[i]; }
  body += "],\"alert_id\":" + String(alertId) + ",\"buzzing\":" + String(alertLevel ? "true" : "false")
        + ",\"radio_rx\":" + String(rxCount) + ",\"tx_fail\":" + String(txFail)
        + ",\"wifi_rssi\":" + String(WiFi.RSSI()) + ",\"esp_ch\":" + String(channel)
        + ",\"ip\":\"" + WiFi.localIP().toString() + "\""
        + ",\"uptime\":" + String(millis() / 1000) + "}";

  HTTPClient http;
  http.setTimeout(1500);
  http.begin(hubUrl);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  String resp = code == 200 ? http.getString() : "";
  http.end();
  hubPosts++;
  lastHubCode = code;
  if (code != 200) {
    hubErrors++;
    Serial.printf("hub error %d at %s (is admin_hub.py running? is it the laptop's IP?)\n", code, hubUrl.c_str());
#if HUB_AUTOFIND
    if (++hubFailRun >= 3 && code < 0) {                      // no answer at all: the laptop probably got a new IP
      Serial.printf("Searching %u.%u.%u.x for admin_hub on port %u ...\n", WiFi.localIP()[0], WiFi.localIP()[1],
                    WiFi.localIP()[2], hubPort());
      findStep = 0;
    }
#endif
    return;
  }
  hubFailRun = 0;
  lastHubOk = millis();
  nPackets = 0; nStatuses = 0;
  int a = resp.indexOf("\"alert\"");
  if (a >= 0) {
    String al = resp.substring(a, resp.indexOf('}', a) + 1);
    String tgt = jsonStr(al, "\"target\"");
    adoptAlert(jsonInt(al, "\"id\"", alertId), jsonInt(al, "\"level\"", alertLevel), tgt.c_str());
  }
  // evacuation guide: "guide":{"id":123,"evac":1,"g":[[2,1,85],[3,2,40]]}
  int gpos = resp.indexOf("\"guide\"");
  if (gpos >= 0) {
    String gs = resp.substring(gpos);
    uint32_t id = (uint32_t)jsonInt(gs, "\"id\"", 0);
    if (id && id != guideId) {
      uint8_t evac = (uint8_t)jsonInt(gs, "\"evac\"", 0);
      GuideEntry e[GUIDE_MAX];
      uint8_t n = 0;
      int k = gs.indexOf("\"g\"");
      k = k < 0 ? -1 : gs.indexOf('[', k);
      if (k >= 0) {
        long v[3]; int nv = 0, depth = 0; long cur = 0; bool num = false;
        for (int i = k; i < (int)gs.length() && n < GUIDE_MAX; i++) {
          char c = gs[i];
          if (c >= '0' && c <= '9') { cur = cur * 10 + (c - '0'); num = true; continue; }
          if (num) { if (nv < 3) v[nv++] = cur; cur = 0; num = false; }
          if (c == '[') depth++;
          else if (c == ']') {
            if (depth == 2 && nv == 3) { e[n].rep = v[0]; e[n].code = v[1]; e[n].dist = v[2] > 65535 ? 65535 : v[2]; n++; }
            nv = 0;
            if (--depth == 0) break;
          }
        }
      }
      adoptGuide(id, evac, n, e);
    }
  }
}

// ------------------------- phone test page -----------------------------
#if TEST_PAGE
WebServer web(80);
bool     apUp = false;
uint8_t  apChannel = 0;
uint16_t fakeBoot = 0;
uint32_t fakeSeq = 0, fakeSent = 0;

// page source as plain string lines (the Arduino IDE cannot preprocess C++ raw strings)
const char TEST_HTML[] =
  "<!doctype html><html><head><meta charset=\"utf-8\">\n"
  "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Repeater test</title>\n"
  "<style>\n"
  ":root{--bg:#0e1316;--card:#172025;--line:#2b373d;--ink:#e8eef0;--mut:#93a5ab;--ok:#35c47c;--warn:#f0b429;--bad:#ff4d4f;--acc:#4c9bf0}\n"
  "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui,sans-serif;padding:14px;display:grid;gap:12px}\n"
  "h1{font-size:20px;margin:0}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;gap:10px}\n"
  ".row{display:flex;justify-content:space-between;gap:8px;font-size:14px}.row span:first-child{color:var(--mut)}\n"
  "b.ok{color:var(--ok)}b.bad{color:var(--bad)}b.warn{color:var(--warn)}\n"
  "label{display:grid;gap:4px;font-size:13px;color:var(--mut)}input[type=text]{font:inherit;padding:10px;border-radius:8px;border:1px solid var(--line);background:#0b1013;color:var(--ink)}\n"
  "input[type=range]{width:100%}.val{color:var(--ink);font-weight:700}\n"
  ".sc{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.sc button{font:inherit;font-size:14px;padding:12px 4px;border-radius:9px;border:1px solid var(--line);background:#0b1013;color:var(--ink)}\n"
  ".sc button.on{background:var(--acc);border-color:var(--acc);color:#fff}\n"
  ".big{font:inherit;font-weight:700;padding:14px;border-radius:10px;border:0;background:var(--ok);color:#062414}.big.off{background:#3a4448;color:var(--ink)}\n"
  ".led{display:flex;align-items:center;gap:12px;font-weight:700}.led i{width:26px;height:26px;border-radius:50%;background:#3a1416;border:2px solid #5a1f24}\n"
  ".led.on i{background:var(--bad);box-shadow:0 0 18px var(--bad);animation:p .6s infinite alternate}@keyframes p{to{opacity:.4}}\n"
  "small{color:var(--mut)}\n"
  "</style></head><body>\n"
  "<h1 id=\"title\">Repeater test</h1>\n"
  "<div class=\"card\">\n"
  " <div class=\"row\"><span>Role</span><b id=\"role\">-</b></div>\n"
  " <div class=\"row\"><span>Route to admin</span><b id=\"route\">-</b></div>\n"
  " <div class=\"row\"><span>Admin link</span><b id=\"hub\">-</b></div>\n"
  " <div class=\"row\"><span>Radio channel</span><b id=\"ch\">-</b></div>\n"
  " <div class=\"row\"><span>Gas sensor</span><b id=\"gas\">-</b></div>\n"
  " <div class=\"row\"><span>Air (AHT)</span><b id=\"air\">-</b></div>\n"
  "</div>\n"
  "<div class=\"card\">\n"
  " <b>Fake worker (this phone acts as a body unit)</b>\n"
  " <label>Body ID<input type=\"text\" id=\"id\" value=\"PHONE-01\" maxlength=\"10\"></label>\n"
  " <label>Temperature <span class=\"val\" id=\"tv\"></span><input type=\"range\" id=\"t\" min=\"28\" max=\"42\" step=\"0.1\" value=\"33.5\"></label>\n"
  " <label>Humidity <span class=\"val\" id=\"hv\"></span><input type=\"range\" id=\"h\" min=\"20\" max=\"100\" step=\"1\" value=\"60\"></label>\n"
  " <label>Heart rate <span class=\"val\" id=\"bv\"></span><input type=\"range\" id=\"b\" min=\"30\" max=\"190\" step=\"1\" value=\"78\"></label>\n"
  " <div class=\"sc\" id=\"sc\">\n"
  "  <button data-s=\"0\" class=\"on\">Normal</button><button data-s=\"1\">Fall</button><button data-s=\"2\">No movement</button>\n"
  "  <button data-s=\"3\">SOS</button><button data-s=\"4\">Hard impact</button><button data-s=\"5\">Sensor fault</button>\n"
  " </div>\n"
  " <button class=\"big\" id=\"go\">Sending every second - tap to stop</button>\n"
  " <div class=\"row\"><span>Packets sent from this phone</span><b id=\"sent\">0</b></div>\n"
  " <div class=\"led\" id=\"led\"><i></i><span id=\"ledt\">Alert LED off</span></div>\n"
  " <small>Open the admin page on the laptop: this worker appears on the Live tab tagged PHONE TEST.\n"
  " Press ALERT there and the red light above turns on, exactly like a body unit's LED.</small>\n"
  "</div>\n"
  "<div class=\"card\">\n"
  " <b>Walk on the admin map</b>\n"
  " <small>Pretend to walk: the red dot on the admin Map tab moves. Start next to the main repeater, facing into the mine.</small>\n"
  " <div class=\"row\"><span>Steps</span><b id=\"stv\">0</b></div>\n"
  " <div class=\"row\"><span>Turned</span><b id=\"hdv\">0&deg;</b></div>\n"
  " <div class=\"sc\" id=\"walk\">\n"
  "  <button data-t=\"-90\">&#8630; 90&deg;</button><button data-n=\"1\">1 step</button><button data-t=\"90\">90&deg; &#8631;</button>\n"
  "  <button data-t=\"-30\">&#8630; 30&deg;</button><button data-n=\"5\">5 steps</button><button data-t=\"30\">30&deg; &#8631;</button>\n"
  " </div>\n"
  " <button class=\"big off\" id=\"auto\">Auto walk: off</button>\n"
  " <label>Height (pressure sensor) <span class=\"val\" id=\"zv\"></span><input type=\"range\" id=\"z\" min=\"-60\" max=\"10\" step=\"1\" value=\"0\"></label>\n"
  "</div>\n"
  "<script>\n"
  "const $=s=>document.querySelector(s);let sc=0,on=true,busy=false,st=0,hd=0,aw=false;\n"
  "const wshow=()=>{$('#stv').textContent=st;$('#hdv').innerHTML=((hd%360+540)%360-180)+'&deg;';$('#zv').textContent=$('#z').value+' m';};\n"
  "$('#walk').onclick=e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.n)st+=+b.dataset.n;if(b.dataset.t)hd+=+b.dataset.t;wshow();send();};\n"
  "$('#auto').onclick=()=>{aw=!aw;$('#auto').className='big'+(aw?'':' off');$('#auto').textContent='Auto walk: '+(aw?'ON (1-2 steps/s)':'off');};\n"
  "$('#z').oninput=wshow;wshow();\n"
  "$('#sc').onclick=e=>{const b=e.target.closest('button');if(!b)return;sc=+b.dataset.s;\n"
  " document.querySelectorAll('#sc button').forEach(x=>x.classList.toggle('on',x===b));send();};\n"
  "$('#go').onclick=()=>{on=!on;$('#go').className='big'+(on?'':' off');$('#go').textContent=on?'Sending every second - tap to stop':'Stopped - tap to start';};\n"
  "const show=()=>{$('#tv').textContent=(+$('#t').value).toFixed(1)+' °C';$('#hv').textContent=$('#h').value+' %';$('#bv').textContent=$('#b').value+' bpm';};\n"
  "$('#t').oninput=show;$('#h').oninput=show;$('#b').oninput=show;show();\n"
  "const ago=ms=>ms<0?'never':ms<1500?'just now':Math.round(ms/1000)+' s ago';\n"
  "function paint(d){\n"
  " $('#title').textContent=d.rep+' test page';\n"
  " $('#role').textContent=d.gateway?'Main repeater (WiFi to admin)':'Tunnel repeater';\n"
  " $('#route').innerHTML=d.gateway?'<b class=\"ok\">direct</b>':(d.hop<255?'<b class=\"ok\">'+d.hop+' hop(s) via '+d.parent+'</b>':'<b class=\"bad\">no route yet</b>');\n"
  " if(d.gateway){const ok=d.hub_age>=0&&d.hub_age<3000;\n"
  "  $('#hub').innerHTML='<b class=\"'+(ok?'ok':'bad')+'\">'+(ok?'OK, last post '+ago(d.hub_age):'NOT reaching admin (code '+d.hub_code+')')+'</b>';}\n"
  " else $('#hub').innerHTML='<b class=\"warn\">through '+(d.parent||'?')+'</b>';\n"
  " $('#ch').textContent=d.ch;\n"
  " $('#gas').textContent=d.gas_missing?'not connected':(d.gas_mv+' mV'+(d.gas_warm?' (warming up)':''));\n"
  " $('#air').innerHTML=d.air_t==null?'not connected':d.air_t.toFixed(1)+' &deg;C &middot; '+d.air_h.toFixed(0)+' % RH';\n"
  " if(d.sent!==undefined)$('#sent').textContent=d.sent;\n"
  " $('#led').className='led'+(d.led?' on':'');$('#ledt').textContent=d.led?'ALERT - LED ON':'Alert LED off';\n"
  "}\n"
  "async function send(){if(busy)return;busy=true;\n"
  " if(aw&&on){st+=1+(Math.random()<.5);wshow();}\n"
  " const q=new URLSearchParams({id:$('#id').value.trim().toUpperCase()||'PHONE-01',t:$('#t').value,h:$('#h').value,s:sc,st:st,hd:Math.round(hd*10),al:$('#z').value*10,hr:$('#b').value});\n"
  " try{paint(await (await fetch('/fake?'+q)).json());}catch(e){$('#hub').innerHTML='<b class=\"bad\">phone lost the repeater</b>';}busy=false;}\n"
  "async function status(){try{paint(await (await fetch('/status?id='+encodeURIComponent($('#id').value.trim().toUpperCase()))).json());}catch(e){}}\n"
  "setInterval(()=>{on?send():status();},1000);send();\n"
  "</script></body></html>\n";

bool alertFor(const String& id) {
  return alertLevel && (strcmp(alertTarget, "*") == 0 || id.equalsIgnoreCase(alertTarget));
}

String statusJson(const String& id) {
  char js[420];
  int32_t hubAge = lastHubOk ? (int32_t)(millis() - lastHubOk) : -1;
  snprintf(js, sizeof(js),
           "{\"rep\":\"%s\",\"gateway\":%s,\"hop\":%u,\"parent\":\"%s\",\"ch\":%u,\"hub_age\":%ld,\"hub_code\":%d,"
           "\"gas_mv\":%u,\"gas_warm\":%s,\"gas_missing\":%s,\"led\":%s,\"sent\":%lu",
           repName(REPEATER_NO).c_str(), IS_GATEWAY ? "true" : "false", myHop, parent ? repName(parent).c_str() : "",
           channel, (long)hubAge, lastHubCode, gasMv, gasFlags & 1 ? "true" : "false", gasFlags & 4 ? "true" : "false",
           alertFor(id) ? "true" : "false", (unsigned long)fakeSent);
  return String(js) + airJson(airT, airH) + "}";
}

void handleFake() {
  String id = web.arg("id");
  id.toUpperCase();
  if (!id.length()) id = "PHONE-01";
  float tC = web.arg("t").toFloat(), hum = web.arg("h").toFloat();
  int sc = web.arg("s").toInt();
  uint32_t now = millis();

  MsTelem t = {};
  t.magic[0] = 'M'; t.magic[1] = 'S'; t.ver = MS_VER; t.type = MS_TELEM;
  strncpy(t.node, id.c_str(), sizeof(t.node));
  t.boot = fakeBoot;
  t.seq = ++fakeSeq;
  t.tObj = t.tAmb = (int16_t)(tC * 100);
  t.hum = (uint16_t)(hum * 100);
  float ph = now / 1000.0f * 6.0f;
  if (sc == 1 || sc == 2) {                         // lying still on the side
    t.ax = 980; t.ay = 20; t.az = 50;
  } else {                                          // walking
    t.ax = (int16_t)(150 * sinf(ph)); t.ay = (int16_t)(80 * cosf(ph / 2));
    t.az = (int16_t)(1000 + 250 * fabsf(sinf(ph)));
    t.gx = (int16_t)(300 * sinf(ph)); t.gy = (int16_t)(120 * cosf(ph / 3)); t.gz = (int16_t)(esp_random() % 100) - 50;
  }
  uint16_t f = BF_TEST;
  if (sc == 1) f |= BF_FALL;
  if (sc == 2) f |= BF_NOMOTION;
  if (sc == 3) f |= BF_SOS;
  if (sc == 4) f |= BF_IMPACT;
  if (sc == 5) f |= BF_MPU_FAULT;
  if (alertFor(id)) f |= BF_ALERT_LED;               // the phone "LED" is on -> confirm it like a body does
  t.flags = f;
  t.uptime = now / 1000;
  t.nearRep = REPEATER_NO;
  t.nearRssi = -40;
  t.steps = (uint16_t)web.arg("st").toInt();
  long hd = web.arg("hd").toInt() % 3600;                  // keep it inside the int16 range
  t.head = web.hasArg("hd") ? (int16_t)hd : 0x7FFF;
  t.alt = web.hasArg("al") ? (int16_t)web.arg("al").toInt() : 0x7FFF;
  t.hr = (uint8_t)constrain(web.arg("hr").toInt(), 0, 250);
  t.spo2 = t.hr ? 97 : 0;
  processBody(t, -40);
  fakeSent++;
  web.send(200, "application/json", statusJson(id));
}

void testPageBegin() {
  fakeBoot = (uint16_t)(esp_random() & 0xFFFF) | 1;
  web.on("/", []() { web.send_P(200, "text/html", TEST_HTML); });
  web.on("/fake", handleFake);
  web.on("/status", []() { String id = web.arg("id"); id.toUpperCase(); web.send(200, "application/json", statusJson(id)); });
  web.onNotFound([]() { web.sendHeader("Location", "/"); web.send(302, "text/plain", ""); });
  web.begin();
}

// tunnel repeaters: own test WiFi, on the chain's channel, only while the chain is found
void testApUpdate() {
  if (IS_GATEWAY) return;
  bool want = myHop != 255;
  if (want && (!apUp || apChannel != channel)) {
    String ssid = "MINE-" + repName(REPEATER_NO);
    WiFi.softAP(ssid.c_str(), TEST_AP_PASS, channel, 0, 2);
    apUp = true;
    apChannel = channel;
    Serial.printf("Test WiFi \"%s\" (password %s) on channel %u -> open http://192.168.4.1/\n",
                  ssid.c_str(), TEST_AP_PASS, channel);
  } else if (!want && apUp) {
    WiFi.softAPdisconnect(false);                   // channel search needs the radio free
    apUp = false;
  }
}
#endif

// main repeater: show which WiFi networks this board can see, to find out why it can't connect
void wifiDiagnose() {
  Serial.println("Scanning for WiFi networks (2.4 GHz only - an ESP32 cannot see 5 GHz)...");
  WiFi.disconnect();                                   // a scan fails while a connection attempt is running
  delay(200);
  int n = WiFi.scanNetworks();
  if (n < 0) { delay(500); n = WiFi.scanNetworks(); }
  if (n < 0) Serial.printf("  scan failed (code %d)\n", n);
  bool found = false;
  for (int i = 0; i < n; i++) {
    bool mine = WiFi.SSID(i) == WIFI_SSID;
    found |= mine;
    Serial.printf("  %s \"%s\"  signal %d dBm  channel %d\n", mine ? ">>" : "  ",
                  WiFi.SSID(i).c_str(), (int)WiFi.RSSI(i), (int)WiFi.channel(i));
  }
  if (n == 0) Serial.println("  (no networks at all - keep the board away from metal and retry)");
  Serial.printf("  %d network(s) found\n", n < 0 ? 0 : n);
  if (found) Serial.printf("\"%s\" IS visible -> the password is wrong, or the hotspot blocks new devices / uses WPA3-only\n", WIFI_SSID);
  else Serial.printf("\"%s\" NOT visible -> hotspot off, set to 5 GHz, or the name differs (capitals/spaces)\n", WIFI_SSID);
  WiFi.scanDelete();
  WiFi.begin(WIFI_SSID, WIFI_PASS);                    // keep trying
}

// main repeater: report when WiFi comes up or drops after start-up
void wifiWatch() {
  static bool was = false;
  static uint32_t downSince = 0;
  bool up = WiFi.status() == WL_CONNECTED;
  if (up && !was) {
    channel = WiFi.channel();
    Serial.printf("WiFi connected  IP %s  channel %u\n", WiFi.localIP().toString().c_str(), channel);
#if TEST_PAGE
    Serial.printf("Phone test page: join \"%s\" on the phone, open http://%s/\n", WIFI_SSID, WiFi.localIP().toString().c_str());
#endif
    downSince = 0;
  } else if (!up && was) {
    Serial.println("WiFi lost - reconnecting...");
  }
  if (!up) {
    if (!downSince) downSince = millis();
    if (millis() - downSince > 30000) {                // still down after 30 s: retry from scratch
      downSince = millis();
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASS);
      Serial.println("WiFi still not connected - retrying");
    }
  }
  was = up;
}

// ------------------------- buzzer ------------------------------------
bool buzzerIsOn = false;
void buzzerBegin() {
#if BUZZER_PASSIVE
  ledcAttach(BUZZER_PIN, BUZZER_FREQ, 8);
  ledcWriteTone(BUZZER_PIN, 0);
#else
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, BUZZER_ACTIVE_LOW ? HIGH : LOW);
#endif
}
void buzzerSet(bool on) {
  if (on == buzzerIsOn) return;
  buzzerIsOn = on;
#if BUZZER_PASSIVE
  ledcWriteTone(BUZZER_PIN, on ? BUZZER_FREQ : 0);
#else
  digitalWrite(BUZZER_PIN, (on != (bool)BUZZER_ACTIVE_LOW) ? HIGH : LOW);
#endif
}
void beep(uint16_t ms) { buzzerSet(true); delay(ms); buzzerSet(false); }

// ------------------------- LED matrix exit sign (MAX7219, 8 x 32) -----------
// Own driver (no library): 3 wires, bit-banged. The picture is kept in fb[] - one byte per column,
// bit 0 = top row - and only sent to the matrix when it changes, so the radio is never held up.
const Glyph FONT[] = {
  {'0', 5, {0x3E, 0x51, 0x49, 0x45, 0x3E}},
  {'1', 5, {0x00, 0x42, 0x7F, 0x40, 0x00}},
  {'2', 5, {0x42, 0x61, 0x51, 0x49, 0x46}},
  {'3', 5, {0x21, 0x41, 0x45, 0x4B, 0x31}},
  {'4', 5, {0x18, 0x14, 0x12, 0x7F, 0x10}},
  {'5', 5, {0x27, 0x45, 0x45, 0x45, 0x39}},
  {'6', 5, {0x3C, 0x4A, 0x49, 0x49, 0x30}},
  {'7', 5, {0x01, 0x71, 0x09, 0x05, 0x03}},
  {'8', 5, {0x36, 0x49, 0x49, 0x49, 0x36}},
  {'9', 5, {0x06, 0x49, 0x49, 0x29, 0x1E}},
  {'A', 5, {0x7E, 0x09, 0x09, 0x09, 0x7E}},
  {'B', 5, {0x7F, 0x49, 0x49, 0x49, 0x36}},
  {'C', 5, {0x3E, 0x41, 0x41, 0x41, 0x22}},
  {'D', 5, {0x7F, 0x41, 0x41, 0x22, 0x1C}},
  {'E', 5, {0x7F, 0x49, 0x49, 0x49, 0x41}},
  {'F', 5, {0x7F, 0x09, 0x09, 0x09, 0x01}},
  {'G', 5, {0x3E, 0x41, 0x49, 0x49, 0x7A}},
  {'H', 5, {0x7F, 0x08, 0x08, 0x08, 0x7F}},
  {'I', 5, {0x00, 0x41, 0x7F, 0x41, 0x00}},
  {'J', 5, {0x20, 0x40, 0x41, 0x3F, 0x01}},
  {'K', 5, {0x7F, 0x08, 0x14, 0x22, 0x41}},
  {'L', 5, {0x7F, 0x40, 0x40, 0x40, 0x40}},
  {'M', 5, {0x7F, 0x02, 0x0C, 0x02, 0x7F}},
  {'N', 5, {0x7F, 0x04, 0x08, 0x10, 0x7F}},
  {'O', 5, {0x3E, 0x41, 0x41, 0x41, 0x3E}},
  {'P', 5, {0x7F, 0x09, 0x09, 0x09, 0x06}},
  {'Q', 5, {0x3E, 0x41, 0x51, 0x21, 0x5E}},
  {'R', 5, {0x7F, 0x09, 0x19, 0x29, 0x46}},
  {'S', 5, {0x46, 0x49, 0x49, 0x49, 0x31}},
  {'T', 5, {0x01, 0x01, 0x7F, 0x01, 0x01}},
  {'U', 5, {0x3F, 0x40, 0x40, 0x40, 0x3F}},
  {'V', 5, {0x1F, 0x20, 0x40, 0x20, 0x1F}},
  {'W', 5, {0x3F, 0x40, 0x38, 0x40, 0x3F}},
  {'X', 5, {0x63, 0x14, 0x08, 0x14, 0x63}},
  {'Y', 5, {0x03, 0x04, 0x78, 0x04, 0x03}},
  {'Z', 5, {0x61, 0x51, 0x49, 0x45, 0x43}},
  {'m', 5, {0x7C, 0x04, 0x78, 0x04, 0x78}},
  {'k', 5, {0x7F, 0x10, 0x28, 0x44, 0x00}},
  {'%', 5, {0x23, 0x13, 0x08, 0x64, 0x62}},
  {'!', 1, {0x5F, 0x00, 0x00, 0x00, 0x00}},
  {'.', 1, {0x40, 0x00, 0x00, 0x00, 0x00}},
  {'-', 3, {0x08, 0x08, 0x08, 0x00, 0x00}},
  {':', 1, {0x22, 0x00, 0x00, 0x00, 0x00}},
  {' ', 2, {0x00, 0x00, 0x00, 0x00, 0x00}},
  {'>', 4, {0x41, 0x22, 0x14, 0x08, 0x00}},
  {'<', 4, {0x08, 0x14, 0x22, 0x41, 0x00}},
  {'*', 5, {0x2A, 0x1C, 0x3E, 0x1C, 0x2A}},

};
const uint8_t ARROW_L[8] = {0x08, 0x1C, 0x3E, 0x7F, 0x1C, 0x1C, 0x1C, 0x1C};   // left-pointing arrow, 8 columns
const uint8_t ARROW_U[8] = {0x08, 0x0C, 0x0E, 0xFF, 0xFF, 0x0E, 0x0C, 0x08};   // up-pointing arrow
const uint8_t CROSS[8]   = {0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81};
#define MX_COLS (MATRIX_MODULES * 8)
uint8_t fb[MX_COLS], fbSent[MX_COLS];
uint8_t mxBright = 255;

void mxSendAll(uint8_t reg, const uint8_t* perModule) {     // perModule[0] = left-most block
#if DISPLAY_ENABLED
  digitalWrite(MX_CS, LOW);
  for (int i = 0; i < MATRIX_MODULES; i++) {
    int m = MATRIX_REVERSE ? MATRIX_MODULES - 1 - i : i;      // the first block sent ends up furthest from DIN
    shiftOut(MX_DIN, MX_CLK, MSBFIRST, reg);
    shiftOut(MX_DIN, MX_CLK, MSBFIRST, perModule[m]);
  }
  digitalWrite(MX_CS, HIGH);
#endif
}
void mxReg(uint8_t reg, uint8_t v) { uint8_t d[MATRIX_MODULES]; memset(d, v, sizeof(d)); mxSendAll(reg, d); }

void mxBegin() {
#if DISPLAY_ENABLED
  pinMode(MX_DIN, OUTPUT); pinMode(MX_CLK, OUTPUT); pinMode(MX_CS, OUTPUT);
  digitalWrite(MX_CS, HIGH);
  mxReg(0x0F, 0);      // display test off
  mxReg(0x09, 0);      // no BCD decode
  mxReg(0x0B, 7);      // scan all 8 rows
  mxReg(0x0A, 2);      // brightness 0..15
  mxReg(0x0C, 1);      // wake up
  memset(fbSent, 0xAA, sizeof(fbSent));
  displayOk = true;    // the MAX7219 cannot be read back; "fitted" = enabled in the config
#endif
}

void mxShow(uint8_t bright) {                // send fb[] if anything changed
#if DISPLAY_ENABLED
  if (bright != mxBright) { mxBright = bright; mxReg(0x0A, bright); }
  if (!memcmp(fb, fbSent, sizeof(fb))) return;
  memcpy(fbSent, fb, sizeof(fb));
  uint8_t d[MATRIX_MODULES];
  for (int r = 0; r < 8; r++) {              // FC-16: register = row;  generic: register = column
    for (int m = 0; m < MATRIX_MODULES; m++) {
      uint8_t v = 0;
      for (int c = 0; c < 8; c++) {
        int col = m * 8 + c;
        int src = MATRIX_FLIP_X ? MX_COLS - 1 - col : col;
#if MATRIX_TYPE == 0
        int row = MATRIX_FLIP_Y ? 7 - r : r;
        if (fb[src] >> row & 1) v |= 0x80 >> c;
#else
        uint8_t colBits = fb[m * 8 + (MATRIX_FLIP_X ? 7 - r : r)];
        int bit = MATRIX_FLIP_Y ? 7 - c : c;
        if (colBits >> bit & 1) v |= 1 << c;
#endif
      }
      d[m] = v;
    }
    mxSendAll(r + 1, d);
  }
#endif
}

const Glyph* glyph(char c) {
  for (const Glyph& g : FONT) if (g.c == c) return &g;
  return &FONT[0];
}
int textWidth(const char* t) { int w = 0; for (; *t; t++) w += glyph(*t)->w + 1; return w ? w - 1 : 0; }
void drawText(int x, const char* t) {
  for (; *t; t++) {
    const Glyph* g = glyph(*t);
    for (int i = 0; i < g->w; i++) if (x + i >= 0 && x + i < MX_COLS) fb[x + i] |= g->col[i];
    x += g->w + 1;
  }
}
void drawCentered(const char* t) { drawText((MX_COLS - textWidth(t)) / 2, t); }
void drawIcon(int x, const uint8_t* ic, bool mirror) {
  for (int i = 0; i < 8; i++) if (x + i >= 0 && x + i < MX_COLS) fb[x + i] |= ic[mirror ? 7 - i : i];
}
void distText(char* b, size_t n, uint16_t m) {
  if (m >= 1000) snprintf(b, n, "%u.%uk", m / 1000, (m % 1000) / 100); else snprintf(b, n, "%um", m);
}

// what the sign shows, most important first
void renderDisplay(uint32_t now) {
#if DISPLAY_ENABLED
  static uint32_t last = 0;
  if (now - last < 60) return;
  last = now;
  memset(fb, 0, sizeof(fb));
  bool blink = (now / 400) % 2;
  uint8_t bright = 15;
  uint8_t dir = myCode & 0x0F;
  char b[12];
  if (sosActive) {
    if (blink) drawCentered("SOS");
  } else if (guideEvac && dir != G_NONE) {
    bool phaseB = (now / 1500) % 2;                          // 1.5 s arrow + distance, 1.5 s animation
    if (dir == G_HERE) {
      if (blink || phaseB) drawCentered("EXIT");
    } else if (dir == G_NOWAY) {
      if (phaseB) drawCentered("NO GO"); else { drawIcon(0, CROSS, false); drawIcon(MX_COLS - 8, CROSS, false); drawText(11, "!!"); }
    } else if ((myCode & G_DANGER) && phaseB && blink) {
      drawCentered("DANGR");
    } else if (!phaseB) {
      distText(b, sizeof(b), myDist);
      if (dir == G_LEFT)  { drawIcon(0, ARROW_L, false); drawText(MX_COLS - textWidth(b), b); }
      if (dir == G_RIGHT) { drawText(0, b); drawIcon(MX_COLS - 8, ARROW_L, true); }
      if (dir == G_UP)    { drawIcon(0, ARROW_U, false); drawText(MX_COLS - textWidth(b), b); }
    } else {                                                 // running chevrons in the walking direction
      int sh = (now / 80) % 8;
      for (int x = -8; x < MX_COLS + 8; x += 8) {
        if (dir == G_LEFT)  drawText(x - sh + 8, "<");
        if (dir == G_RIGHT) drawText(x + sh, ">");
        if (dir == G_UP)    drawIcon(x + 0, ARROW_U, false);
      }
      if (dir == G_UP && (now / 200) % 2) memset(fb, 0, sizeof(fb));
    }
  } else if (anyGasAlarm()) {
    if (blink) drawCentered("GAS!");
  } else if (alertLevel) {
    if (blink) drawCentered(guideEvac ? "EVAC" : "ALERT");
  } else {                                                   // normal: quiet, dim, cycles name / air
    bright = 1;
    int phase = (now / 3000) % 3;
    if (phase == 1 && airT != 0x7FFF) snprintf(b, sizeof(b), "%dC", (airT + 50) / 100);
    else if (phase == 2 && airH != 0xFFFF) snprintf(b, sizeof(b), "%u%%", (airH + 50) / 100);
    else snprintf(b, sizeof(b), "R%02u", REPEATER_NO);
    drawCentered(b);
    if (!IS_GATEWAY && myHop == 255 && blink) fb[MX_COLS - 1] = 0x80;   // dot = no route to the main repeater yet
  }
  mxShow(bright);
#endif
}

void displayTest() {                         // Serial 'd': shows every picture once
#if DISPLAY_ENABLED
  const char* words[] = {"MINE", "SAFE", "R" , "EXIT", "GAS!", "SOS"};
  for (const char* w : words) { memset(fb, 0, sizeof(fb)); drawCentered(w); mxShow(15); delay(600); }
  memset(fb, 0, sizeof(fb)); drawIcon(0, ARROW_L, false); drawText(14, "85m"); mxShow(15); delay(900);
  memset(fb, 0, sizeof(fb)); drawText(0, "120m"); drawIcon(MX_COLS - 8, ARROW_L, true); mxShow(15); delay(900);
  memset(fb, 0, sizeof(fb)); drawIcon(0, ARROW_U, false); drawText(14, "40m"); mxShow(15); delay(900);
  memset(fb, 0xFF, sizeof(fb)); mxShow(15); delay(600);
#endif
}

// ------------------------- SOS button --------------------------------
void sosUpdate(uint32_t now) {
#if SOS_ENABLED
  static uint32_t downAt = 0;
  static bool fired = false;
  bool down = digitalRead(SOS_PIN) == LOW;
  if (down && !downAt) { downAt = now | 1; fired = false; }
  if (!down) downAt = 0;
  if (down && !fired && now - downAt > 1500) {               // hold 1.5 s: no accidental bumps
    fired = true;
    sosActive = !sosActive;
    statusNow = true;
    Serial.printf("SOS at this repeater %s\n", sosActive ? "ON" : "off");
  }
#endif
}

// ------------------------- setup / loop ------------------------------
void setup() {
#if defined(ARDUINO_XIAO_ESP32C6)
  // XIAO ESP32-C6 RF switch (Seeed wiki): GPIO3 LOW enables it, GPIO14 LOW = built-in ceramic antenna.
  // Set here as well, because older ESP32 board packages don't do it at start-up.
  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);
  delay(100);
  pinMode(14, OUTPUT);
  digitalWrite(14, USE_EXTERNAL_ANTENNA ? HIGH : LOW);
#endif
  Serial.begin(115200);
  delay(1000);
  buzzerBegin();
#if GAS_ENABLED
  analogSetPinAttenuation(GAS_PIN, ADC_11db);
#endif
#if AHT_ENABLED
  Wire.begin(AHT_SDA, AHT_SCL);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  esp_log_level_set("i2c.master", ESP_LOG_NONE);   // no I2C error flood if the AHT is unplugged
  esp_log_level_set("i2c", ESP_LOG_NONE);
  delay(40);                            // AHT needs ~40 ms after power-on
  Serial.printf("AHT air sensor on SDA GPIO%d / SCL GPIO%d: %s\n", AHT_SDA, AHT_SCL,
                ahtInit() ? "found" : "NOT found (check wiring) - will keep looking");
#endif
#if GAS_ENABLED
  for (uint8_t c = 1; c < GAS_CHANNELS && c < 3; c++) analogSetPinAttenuation(GAS_PINS[c], ADC_11db);
#endif
#if SOS_ENABLED
  pinMode(SOS_PIN, INPUT_PULLUP);
#endif
#if DISPLAY_ENABLED
  mxBegin();
  memset(fb, 0, sizeof(fb)); { char b[8]; snprintf(b, sizeof(b), "R%02u", REPEATER_NO); drawCentered(b); } mxShow(8);
  Serial.printf("LED matrix: DIN GPIO%d, CS GPIO%d, CLK GPIO%d (type %d) - type d + Enter for a display test\n",
                MX_DIN, MX_CS, MX_CLK, MATRIX_TYPE);
#endif
  Serial.printf("Buzzer test on GPIO%d (%s%s): 3 beeps\n", BUZZER_PIN, BUZZER_PASSIVE ? "passive, tone" : "active",
                BUZZER_ACTIVE_LOW ? ", active-LOW" : "");
  for (int i = 0; i < 3; i++) { beep(150); delay(150); }

  if (IS_GATEWAY) {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(250);
    channel = WiFi.status() == WL_CONNECTED ? WiFi.channel() : 1;   // the whole chain uses the hotspot's channel
    Serial.printf("\n%s MAIN repeater  WiFi %s  IP %s  channel %u\n", repName(REPEATER_NO).c_str(),
                  WiFi.status() == WL_CONNECTED ? "connected" : "NOT connected (still trying in the background)",
                  WiFi.localIP().toString().c_str(), channel);
    if (WiFi.status() != WL_CONNECTED) wifiDiagnose();
  } else {
    WiFi.mode(TEST_PAGE ? WIFI_AP_STA : WIFI_STA);
    WiFi.disconnect();
    setChannel(1);
    Serial.printf("\n%s tunnel repeater - looking for the chain\n", repName(REPEATER_NO).c_str());
  }
  esp_wifi_set_ps(WIFI_PS_NONE);          // keep the receiver awake
  Serial.printf("ESP-NOW %s   buzzer GPIO%d   gas %s (%d channel%s)\n", radioBegin() ? "OK" : "FAILED", BUZZER_PIN,
                GAS_ENABLED ? ("GPIO" + String(GAS_PIN) + " (warming up 60 s)").c_str() : "off", GAS_CHANNELS, GAS_CHANNELS > 1 ? "s" : "");
#if TEST_PAGE
  testPageBegin();
  if (IS_GATEWAY && WiFi.status() == WL_CONNECTED)
    Serial.printf("Phone test page: join \"%s\" on the phone, open http://%s/\n",
                  WIFI_SSID, WiFi.localIP().toString().c_str());
#endif
}

void loop() {
  static uint32_t nextBeacon = 0, nextStatus = 5000, lastPost = 0, lastRoute = 0, lastStatusAt = 0;
  uint32_t now = millis();

  handleRadio(now);
  readGas(now);
  readAir(now);
  sosUpdate(now);
  renderDisplay(now);
  channelSearch(now);
  if (now - lastRoute > 1000) { lastRoute = now; recomputeRoute(now); }

  bool routed = IS_GATEWAY || myHop != 255;
  if (routed && (beaconNow || now >= nextBeacon)) {           // beacons: routing + channel + alert for bodies
    beaconNow = false;
    sendBeacon();
    nextBeacon = now + BEACON_MS + esp_random() % 200;
  }
  if (!IS_GATEWAY && routed && (now >= nextStatus || (statusNow && now - lastStatusAt > 1000))) {
    MsStatus st = myStatus();
    uint8_t path[1] = {REPEATER_NO};
    sendUp(UP_STATUS, &st, sizeof(st), 0, path, 1);
    statusNow = false;
    lastStatusAt = now;
    nextStatus = now + STATUS_MS + esp_random() % 1000;
  }
  if (IS_GATEWAY && now - lastPost >= POST_MS) {
    lastPost = now;
    wifiWatch();
    if (WiFi.status() == WL_CONNECTED && WiFi.channel() != channel) {   // hotspot changed channel
      channel = WiFi.channel();
      Serial.printf("Hotspot moved to channel %u - the chain will follow\n", channel);
    }
    postToHub();
  }
  if (IS_GATEWAY) hubFindStep();
#if TEST_PAGE
  testApUpdate();
  web.handleClient();
#endif

  // Serial Monitor: type  b  + Enter = 1 second buzzer test,  a  + Enter = AHT air reading (checks wiring without the admin)
  static uint32_t testUntil = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'b' || c == 'B') { testUntil = now + 1000; Serial.println("Buzzer test 1 s"); }
    if (c == 'd' || c == 'D') { Serial.println("Display test"); displayTest(); }
    if (c == 's' || c == 'S') { sosActive = !sosActive; statusNow = true; Serial.printf("SOS %s\n", sosActive ? "ON" : "off"); }
    if (c == 'a' || c == 'A') {
      if (airT == 0x7FFF) Serial.println("AHT: no reading (sensor not found)");
      else Serial.printf("AHT: air %.2f C, humidity %.2f %%RH\n", airT / 100.0f, airH / 100.0f);
    }
  }
  // buzzer patterns: evacuation = 3 short beeps every 1.5 s, alert = 300 ms on / 200 ms off,
  // local gas alarm = fast beeping, SOS at this repeater = short chirp every 2 s (helps rescuers find it)
  uint32_t e = now % 1500;
  bool evacBuzz = guideEvac && alertLevel && e < 600 && (e % 200) < 120;
  bool buzz = now < testUntil || (anyGasAlarm() && (now % 200) < 100) || evacBuzz
              || (!guideEvac && alertLevel && (now % 500) < 300) || (sosActive && (now % 2000) < 80);
  buzzerSet(buzz);
  delay(2);
}
