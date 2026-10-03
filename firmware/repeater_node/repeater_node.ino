// =====================================================================
//  Miner Safety System - REPEATER NODE (chain / mesh) - ESP-NOW version
//  Boards: ESP32-S3 or ESP32-C6 (any mix), Arduino ESP32 core 3.x
//          Tools -> Board: "ESP32S3 Dev Module" or "ESP32C6 Dev Module"
//          Tools -> USB CDC On Boot: Enabled
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
//  WIRING (pins are picked automatically for S3 / C6 - see PIN SETUP below)
//                      ESP32-S3      ESP32-C6    (Seeed XIAO ESP32-C6 pin label)
//    Buzzer (+)        GPIO5         GPIO18 (D10) buzzer(-) -> GND  (active 3.3 V buzzer;
//                                                use an NPN transistor for a louder 5 V one)
//    Status LED        GPIO6         GPIO19 (D8) -> 220 ohm -> LED -> GND (optional)
//    Gas sensor AO     GPIO4         GPIO2  (D2) through a divider: AO -> 10k -> pin,
//                                                pin -> 20k -> GND. Sensor VCC -> 5V, GND -> GND.
//
//  GAS
//    MQ-2 / MQ-4 / MQ-7 module. Heater warm-up 60 s. Reading sent to the admin in
//    mV; the admin page sets the alarm level and alerts everyone automatically.
//    No sensor connected -> reported as "no sensor" (that is fine for testing).
//    Fail-safe: above GAS_LOCAL_ALARM_MV this repeater beeps fast by itself.
//
//  SETUP FOR EACH BOARD
//    Main repeater (near the admin laptop):  IS_GATEWAY 1, REPEATER_NO 1
//    Repeaters in the tunnel:                IS_GATEWAY 0, REPEATER_NO 2, 3, 4 ... (all different)
// =====================================================================

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "esp_random.h"

// ------------------------- CONFIG ------------------------------------
#define IS_GATEWAY    1                 // 1 = main repeater (WiFi to admin). 0 = repeater in the tunnel
const uint8_t REPEATER_NO = 1;          // unique number 1..99  -> shown as REP-01, REP-02 ...

const char* WIFI_SSID = "YOUR_HOTSPOT";   // only used by the main repeater
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* HUB_URL   = "http://192.168.1.100:5000/api/telemetry";   // laptop IP running admin_hub.py

#define TEST_PAGE     1                 // 1 = serve the phone test page, 0 = off
#define USE_EXTERNAL_ANTENNA 0          // Seeed XIAO ESP32-C6 only: 1 = use the u.FL antenna socket
                                        // (fit the antenna first!), 0 = built-in antenna
const char* TEST_AP_PASS = "minesafe";  // password of the tunnel repeaters' test WiFi (8+ chars)

// ---- PIN SETUP (chosen automatically from the board you select in Tools) ----
#if CONFIG_IDF_TARGET_ESP32C6
  #define BUZZER_PIN  18
  #define LED_PIN     19
  #define GAS_PIN     2
#else                                   // ESP32-S3 (and others)
  #define BUZZER_PIN  5
  #define LED_PIN     6
  #define GAS_PIN     4
#endif
#define GAS_DIVIDER        1.5f         // 10k + 20k divider: sensor mV = pin mV x 1.5
#define GAS_WARMUP_MS      60000
#define GAS_LOCAL_ALARM_MV 2500
#define GAS_EVENT_STEP_MV  300

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
};
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
uint32_t bodiesHeard = 0, ledOffAt = 0, lastBeaconHeard = 0, lastHop = 0;
uint32_t lastHubOk = 0, hubPosts = 0, hubErrors = 0;
int      lastHubCode = 0;
uint16_t statusSeq = 0;
uint16_t gasMv = 0;
uint8_t  gasFlags = 1;
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
  memcpy(&t, data, len < (int)sizeof(MsTelem) ? len : sizeof(MsTelem));
}

// ------------------------- gas ---------------------------------------
void readGas(uint32_t now) {
  static uint32_t last = 0;
  static uint16_t lastReported = 0;
  if (now - last < 500) return;
  last = now;
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(GAS_PIN);
  gasMv = (uint16_t)(sum / 16 * GAS_DIVIDER);
  uint8_t f = 0;
  if (now < GAS_WARMUP_MS) f |= 1;
  if (gasMv < 30) f |= 4;                                   // ~0 V: sensor not connected
  if (!(f & 5) && gasMv >= GAS_LOCAL_ALARM_MV) f |= 2;
  if ((f & 2) != (gasFlags & 2) || (!(f & 1) && gasMv > lastReported + GAS_EVENT_STEP_MV)) {
    statusNow = true;
    lastReported = gasMv;
  }
  if (gasMv + GAS_EVENT_STEP_MV < lastReported) lastReported = gasMv;
  gasFlags = f;
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
  char js[320];
  snprintf(js, sizeof(js),
           "{\"node\":\"%s\",\"seq\":%lu,\"bt\":%u,\"to\":%d,\"ta\":%d,\"ax\":%d,\"ay\":%d,\"az\":%d,"
           "\"gx\":%d,\"gy\":%d,\"gz\":%d,\"fl\":%u,\"up\":%lu,\"rssi\":%d,\"near\":\"%s\",\"near_rssi\":%d,\"hu\":%u,\"path\":",
           node, (unsigned long)t.seq, t.boot, t.tObj, t.tAmb, t.ax, t.ay, t.az, t.gx, t.gy, t.gz,
           t.flags, (unsigned long)t.uptime, bodyRssi, t.nearRep ? repName(t.nearRep).c_str() : "", t.nearRssi, t.hum);
  String s = String(js) + pathJson(path, pathLen) + "}";
  if (nPackets == MAX_BUFFER) { for (int i = 1; i < MAX_BUFFER; i++) hubPackets[i - 1] = hubPackets[i]; nPackets--; }
  hubPackets[nPackets++] = s;
}

void queueStatusForHub(const MsStatus& st, const uint8_t* path, uint8_t pathLen) {
  char js[340];
  snprintf(js, sizeof(js),
           "{\"id\":\"%s\",\"hop\":%u,\"parent\":\"%s\",\"prssi\":%d,\"alert_id\":%lu,\"buzzing\":%s,"
           "\"up\":%lu,\"bodies\":%u,\"nbrs\":%u,\"gas_mv\":%u,\"gas_warm\":%s,\"gas_alarm\":%s,\"gas_missing\":%s,\"path\":",
           repName(st.rep).c_str(), st.hop, st.parent ? repName(st.parent).c_str() : "", st.parentRssi,
           (unsigned long)st.alertId, st.buzzing ? "true" : "false", (unsigned long)st.uptime, st.bodies, st.neighbors,
           st.gasMv, st.gasFlags & 1 ? "true" : "false", st.gasFlags & 2 ? "true" : "false", st.gasFlags & 4 ? "true" : "false");
  String s = String(js) + pathJson(path, pathLen) + "}";
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
    } else if (h.kind == UP_STATUS && innerLen >= sizeof(MsStatus)) {
      MsStatus st; memcpy(&st, inner, sizeof(st));
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
  return st;
}

// a body packet heard by this repeater (over the radio, or from the phone test page)
void processBody(const MsTelem& t, int8_t rssi) {
  if (alreadySeen(fnv((const uint8_t*)&t, sizeof(MsTelem)))) return;
  bodiesHeard++;
  digitalWrite(LED_PIN, HIGH);
  ledOffAt = millis() + 30;
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
      if (b.rep != REPEATER_NO) onBeacon(b, p.rssi, now);
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
  radioSend(&b, sizeof(b));
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

void postToHub() {
  if (WiFi.status() != WL_CONNECTED) return;
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
  http.begin(HUB_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  String resp = code == 200 ? http.getString() : "";
  http.end();
  hubPosts++;
  lastHubCode = code;
  if (code != 200) {
    hubErrors++;
    Serial.printf("hub error %d (is admin_hub.py running? is HUB_URL the laptop's IP?)\n", code);
    return;
  }
  lastHubOk = millis();
  nPackets = 0; nStatuses = 0;
  int a = resp.indexOf("\"alert\"");
  if (a < 0) return;
  String al = resp.substring(a);
  String tgt = jsonStr(al, "\"target\"");
  adoptAlert(jsonInt(al, "\"id\"", alertId), jsonInt(al, "\"level\"", alertLevel), tgt.c_str());
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
  "</div>\n"
  "<div class=\"card\">\n"
  " <b>Fake worker (this phone acts as a body unit)</b>\n"
  " <label>Body ID<input type=\"text\" id=\"id\" value=\"PHONE-01\" maxlength=\"10\"></label>\n"
  " <label>Temperature <span class=\"val\" id=\"tv\"></span><input type=\"range\" id=\"t\" min=\"28\" max=\"42\" step=\"0.1\" value=\"33.5\"></label>\n"
  " <label>Humidity <span class=\"val\" id=\"hv\"></span><input type=\"range\" id=\"h\" min=\"20\" max=\"100\" step=\"1\" value=\"60\"></label>\n"
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
  "<script>\n"
  "const $=s=>document.querySelector(s);let sc=0,on=true,busy=false;\n"
  "$('#sc').onclick=e=>{const b=e.target.closest('button');if(!b)return;sc=+b.dataset.s;\n"
  " document.querySelectorAll('#sc button').forEach(x=>x.classList.toggle('on',x===b));send();};\n"
  "$('#go').onclick=()=>{on=!on;$('#go').className='big'+(on?'':' off');$('#go').textContent=on?'Sending every second - tap to stop':'Stopped - tap to start';};\n"
  "const show=()=>{$('#tv').textContent=(+$('#t').value).toFixed(1)+' °C';$('#hv').textContent=$('#h').value+' %';};\n"
  "$('#t').oninput=show;$('#h').oninput=show;show();\n"
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
  " if(d.sent!==undefined)$('#sent').textContent=d.sent;\n"
  " $('#led').className='led'+(d.led?' on':'');$('#ledt').textContent=d.led?'ALERT - LED ON':'Alert LED off';\n"
  "}\n"
  "async function send(){if(busy)return;busy=true;\n"
  " const q=new URLSearchParams({id:$('#id').value.trim().toUpperCase()||'PHONE-01',t:$('#t').value,h:$('#h').value,s:sc});\n"
  " try{paint(await (await fetch('/fake?'+q)).json());}catch(e){$('#hub').innerHTML='<b class=\"bad\">phone lost the repeater</b>';}busy=false;}\n"
  "async function status(){try{paint(await (await fetch('/status?id='+encodeURIComponent($('#id').value.trim().toUpperCase()))).json());}catch(e){}}\n"
  "setInterval(()=>{on?send():status();},1000);send();\n"
  "</script></body></html>\n";

bool alertFor(const String& id) {
  return alertLevel && (strcmp(alertTarget, "*") == 0 || id.equalsIgnoreCase(alertTarget));
}

String statusJson(const String& id) {
  char js[360];
  int32_t hubAge = lastHubOk ? (int32_t)(millis() - lastHubOk) : -1;
  snprintf(js, sizeof(js),
           "{\"rep\":\"%s\",\"gateway\":%s,\"hop\":%u,\"parent\":\"%s\",\"ch\":%u,\"hub_age\":%ld,\"hub_code\":%d,"
           "\"gas_mv\":%u,\"gas_warm\":%s,\"gas_missing\":%s,\"led\":%s,\"sent\":%lu}",
           repName(REPEATER_NO).c_str(), IS_GATEWAY ? "true" : "false", myHop, parent ? repName(parent).c_str() : "",
           channel, (long)hubAge, lastHubCode, gasMv, gasFlags & 1 ? "true" : "false", gasFlags & 4 ? "true" : "false",
           alertFor(id) ? "true" : "false", (unsigned long)fakeSent);
  return js;
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
                  WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.channel(i));
  }
  if (n == 0) Serial.println("  (no networks at all - antenna problem: check USE_EXTERNAL_ANTENNA)");
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

// ------------------------- setup / loop ------------------------------
void setup() {
#if defined(ARDUINO_XIAO_ESP32C6)
  // XIAO ESP32-C6 has an RF switch in front of the antenna: GPIO3 LOW turns it on,
  // GPIO14 picks the antenna (LOW = built-in, HIGH = u.FL socket). Older ESP32 board
  // packages don't set this, and then the board hears almost nothing.
  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);
  delay(100);
  pinMode(14, OUTPUT);
  digitalWrite(14, USE_EXTERNAL_ANTENNA ? HIGH : LOW);
#endif
  Serial.begin(115200);
  delay(1000);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  analogSetPinAttenuation(GAS_PIN, ADC_11db);
  digitalWrite(BUZZER_PIN, HIGH); delay(150); digitalWrite(BUZZER_PIN, LOW);   // buzzer test

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
  Serial.printf("ESP-NOW %s   buzzer GPIO%d  LED GPIO%d  gas GPIO%d\n", radioBegin() ? "OK" : "FAILED",
                BUZZER_PIN, LED_PIN, GAS_PIN);
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
  channelSearch(now);
  readGas(now);
  if (ledOffAt && now > ledOffAt) { digitalWrite(LED_PIN, LOW); ledOffAt = 0; }
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
#if TEST_PAGE
  testApUpdate();
  web.handleClient();
#endif

  // buzzer: 300/200 ms while the alert is active; fast 100/100 if this repeater's own gas is high
  bool buzz = (alertLevel && (now % 500) < 300) || ((gasFlags & 2) && (now % 200) < 100);
  digitalWrite(BUZZER_PIN, buzz ? HIGH : LOW);
  delay(2);
}
