// =====================================================================
//  Miner Safety System - BODY NODE, button + LED version (no sensors yet)
//  Boards: ESP32-S3 (N16R8) or Seeed XIAO ESP32-C6, Arduino ESP32 core 3.x
//          Tools -> Board: "ESP32S3 Dev Module"  or  "XIAO_ESP32C6"
//          Tools -> USB CDC On Boot: Enabled
//  Radio : ESP-NOW only (no WiFi network, no password) -> nearest repeater(s)
//
//  WIRING                     ESP32-S3     XIAO ESP32-C6
//    SOS button  one leg  ->  GPIO5        D8      other leg -> GND (no resistor needed)
//    Red LED (+) via 220 ohm  GPIO4        D10     LED (-) -> GND
//
//  WHAT IT DOES
//    - Finds the repeater chain by itself (listens on channels 1..13 for repeater
//      beacons, then stays on that channel). Searches again if it loses them.
//    - Every second sends: body ID + boot ID + serial number + status flags +
//      nearest repeater. Every repeater in range relays it to the admin page.
//    - BUTTON: press once = SOS ON  (admin page shows DANGER "SOS button pressed")
//              press again = SOS OFF
//    - LED:    solid ON      = ALERT from the admin (sent through the repeaters)
//              fast blinking = your SOS is active
//              short blink every 2 s = searching for a repeater
//              off           = connected, all normal
//
//  NO SENSORS YET: until the MPU6050 / AHT25 are fitted, the unit reports fixed
//  placeholder readings (36.5 C, standing still) so the admin page shows it as SAFE.
//  Set PLACEHOLDER_READINGS to 0 later when real sensors are added.
// =====================================================================

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "esp_random.h"

// ------------------------- CONFIG ------------------------------------
const char* BODY_ID = "BODY-01";      // must match the "Body ESP code" on the admin page

#if CONFIG_IDF_TARGET_ESP32C6
  #define BUTTON_PIN   19             // XIAO ESP32-C6: D8
  #define LED_PIN      18             // XIAO ESP32-C6: D10
#else
  #define BUTTON_PIN   5              // ESP32-S3
  #define LED_PIN      4              // ESP32-S3
#endif

#define PLACEHOLDER_READINGS 1        // 1 = send fixed 36.5 C / standing still until sensors exist
#define SEND_EVERY_MS        1000
#define LOST_MS              8000     // no beacon this long -> search channels
#define SCAN_DWELL_MS        1300     // listen this long per channel (beacons come every second)
// ---------------------------------------------------------------------

// ===== shared packet format (same as repeater_node.ino) ================
#define MS_VER 3
enum : uint8_t { MS_TELEM = 1, MS_BEACON = 10 };
enum : uint16_t { BF_FALL = 1, BF_NOMOTION = 2, BF_IMPACT = 4, BF_SOS = 8, BF_MPU_FAULT = 16,
                  BF_TEMP_FAULT = 32, BF_ALERT_LED = 64, BF_TEST = 128 };

struct __attribute__((packed)) MsTelem {        // body -> repeaters
  char     magic[2];
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
struct __attribute__((packed)) MsBeacon {       // repeater -> everyone
  char     magic[2];
  uint8_t  ver, type;
  uint8_t  rep, hop, espCh;
  uint32_t alertId;
  uint8_t  level;
  char     target[10];
};
struct BeaconRx { MsBeacon b; int8_t rssi; };
// (types live up here: the Arduino IDE declares every function at the top of the sketch)
// =====================================================================

// ------------------------- radio -------------------------------------
const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
QueueHandle_t rxQueue;
uint8_t  channel = 1;
bool     locked = false;
uint32_t lastBeaconAt = 0, lastHopAt = 0, txFail = 0;

void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (len < (int)sizeof(MsBeacon) || data[0] != 'M' || data[1] != 'S' || data[2] != MS_VER || data[3] != MS_BEACON) return;
  BeaconRx r;
  memcpy(&r.b, data, sizeof(MsBeacon));
  r.rssi = info->rx_ctrl ? info->rx_ctrl->rssi : -100;
  xQueueSend(rxQueue, &r, 0);
}

void setChannel(uint8_t ch) {
  channel = ch;
  esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
}

bool radioBegin() {
  rxQueue = xQueueCreate(16, sizeof(BeaconRx));
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_ps(WIFI_PS_NONE);                 // keep the receiver awake
  setChannel(1);
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(onEspNowRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = 0;                              // = the channel we are on
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  return esp_now_add_peer(&peer) == ESP_OK;
}

// while no repeater is heard, step through channels 1..13
void channelSearch(uint32_t now) {
  if (locked && now - lastBeaconAt > LOST_MS) {
    locked = false;
    Serial.println("Lost the repeaters - searching channels...");
  }
  if (!locked && now - lastHopAt > SCAN_DWELL_MS) {
    lastHopAt = now;
    setChannel(channel % 13 + 1);
  }
}

// ------------------------- state -------------------------------------
uint16_t bootId;
uint32_t seqNo = 0;
bool     alertOn = false, sosOn = false;
uint32_t lastAlertId = 0;
uint8_t  nearRep = 0;
int8_t   nearRssi = -127;
uint32_t nearAt = 0;

void handleBeacons(uint32_t now) {
  BeaconRx r;
  while (xQueueReceive(rxQueue, &r, 0) == pdTRUE) {
    if (r.b.hop >= 255) continue;                           // repeater without a route
    if (!locked) Serial.printf("Connected: repeater REP-%02u found on channel %u\n", r.b.rep, channel);
    locked = true;
    lastBeaconAt = now;
    if (r.b.espCh && r.b.espCh != channel) setChannel(r.b.espCh);

    // nearest repeater = strongest beacon heard in the last 4 s
    if (r.b.rep == nearRep || r.rssi > nearRssi || now - nearAt > 4000) {
      if (r.b.rep != nearRep) Serial.printf("Nearest repeater: REP-%02u (%d dBm)\n", r.b.rep, r.rssi);
      nearRep = r.b.rep; nearRssi = r.rssi; nearAt = now;
    }

    // the admin's alert: for everyone ("*") or for this body ID
    if (r.b.alertId < lastAlertId) continue;                // older alert from a slow repeater
    lastAlertId = r.b.alertId;
    char target[11] = {0};
    memcpy(target, r.b.target, 10);
    bool want = r.b.level && (strcmp(target, "*") == 0 || strcasecmp(target, BODY_ID) == 0);
    if (want != alertOn) {
      alertOn = want;
      Serial.println(alertOn ? "\n*** ALERT FROM ADMIN - LEAVE THE AREA / FOLLOW INSTRUCTIONS ***\n"
                             : "Alert cleared by admin");
    }
  }
}

void sendTelemetry(uint32_t now) {
  MsTelem t = {};
  t.magic[0] = 'M'; t.magic[1] = 'S'; t.ver = MS_VER; t.type = MS_TELEM;
  strncpy(t.node, BODY_ID, sizeof(t.node));
  t.boot = bootId;
  t.seq = ++seqNo;
  uint16_t f = 0;
#if PLACEHOLDER_READINGS
  t.tObj = t.tAmb = 3650;                       // 36.50 C placeholder
  t.az = 1000;                                  // 1 g, standing still
#else
  f |= BF_MPU_FAULT | BF_TEMP_FAULT;            // no sensors and no placeholders -> admin shows sensor fault
#endif
  t.hum = 0xFFFF;                               // no humidity sensor
  if (sosOn) f |= BF_SOS;
  if (alertOn) f |= BF_ALERT_LED;               // tells the admin our LED is on
  t.flags = f;
  t.uptime = now / 1000;
  bool fresh = nearRep && now - nearAt < 4000;
  t.nearRep = fresh ? nearRep : 0;
  t.nearRssi = fresh ? nearRssi : -127;
  if (esp_now_send(BROADCAST, (const uint8_t*)&t, sizeof(t)) != ESP_OK) txFail++;
  Serial.printf("#%lu ch%u %s near=REP-%02u(%d dBm)  SOS=%s  ALERT=%s\n", (unsigned long)t.seq, channel,
                locked ? "connected" : "(searching)", t.nearRep, t.nearRssi,
                sosOn ? "ON" : "off", alertOn ? "ON" : "off");
}

// press = toggle SOS (debounced); returns true when the state changed
bool handleButton(uint32_t now) {
  static bool stable = false, last = false;
  static uint32_t changedAt = 0;
  bool pressed = digitalRead(BUTTON_PIN) == LOW;
  if (pressed != last) { last = pressed; changedAt = now; }
  if (now - changedAt > 40 && pressed != stable) {
    stable = pressed;
    if (pressed) {
      sosOn = !sosOn;
      Serial.println(sosOn ? "\n>>> SOS SENT - admin will see DANGER <<<\n" : "SOS cancelled");
      return true;
    }
  }
  return false;
}

void updateLed(uint32_t now) {
  bool on;
  if (alertOn)      on = true;                              // admin alert: solid
  else if (sosOn)   on = (now % 250) < 125;                 // SOS active: fast blink
  else if (!locked) on = (now % 2000) < 80;                 // searching: short blink
  else              on = false;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// ------------------------- setup / loop ------------------------------
void setup() {
#if defined(ARDUINO_XIAO_ESP32C6)
  // XIAO ESP32-C6 RF switch (Seeed wiki): GPIO3 LOW enables it, GPIO14 LOW = built-in antenna
  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);
  delay(100);
  pinMode(14, OUTPUT);
  digitalWrite(14, LOW);
#endif
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, HIGH); delay(300); digitalWrite(LED_PIN, LOW);   // LED test
  delay(1000);

  bootId = (uint16_t)(esp_random() & 0xFFFF) | 1;
  bool ok = radioBegin();
  Serial.printf("\nBody node %s  ESP-NOW %s  button GPIO%d  LED GPIO%d\n", BODY_ID, ok ? "OK" : "FAILED",
                BUTTON_PIN, LED_PIN);
  Serial.println("Searching for a repeater...");
}

void loop() {
  static uint32_t lastSend = 0;
  uint32_t now = millis();

  handleBeacons(now);
  channelSearch(now);
  bool changed = handleButton(now);
  updateLed(now);

  if (changed || now - lastSend >= SEND_EVERY_MS) {         // every second, and at once on SOS
    lastSend = now;
    sendTelemetry(now);
  }
  delay(2);
}
