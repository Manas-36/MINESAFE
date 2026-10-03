// =====================================================================
//  Miner Safety System - BODY NODE (worn by the worker)
//  Boards: ESP32-S3 (N16R8) or Seeed XIAO ESP32-C6, Arduino ESP32 core 3.x
//          Tools -> Board: "ESP32S3 Dev Module"  or  "XIAO_ESP32C6"
//          Tools -> USB CDC On Boot: Enabled
//  Radio : ESP-NOW only (no WiFi network, no password) -> nearest repeater(s)
//  No extra libraries needed - every sensor driver is inside this file.
//
//  SENSORS (all optional - whatever is connected is found at power-on and listed
//  on the Serial Monitor; a missing sensor is reported to the admin page)
//    MPU6050 (GY-521 / HW-123)  : steps + turning (map), fall, hard impact, no movement
//    BMP180  (GY-68 / HW-596)   : height change (depth on the map), air temperature
//    DS18B20 waterproof probe   : body (skin) temperature
//    MAX30100 / MAX30102 board  : heart rate + SpO2 (estimate)
//    HW-827 pulse sensor        : heart rate (used only if no MAX3010x is found)
//
//  WIRING                         ESP32-S3        XIAO ESP32-C6
//    I2C SDA  (MPU6050, BMP180, MAX30100 - all in parallel)
//                                 GPIO8           D4
//    I2C SCL  (same three)        GPIO9           D5
//    VCC / VIN of those boards -> 3V3             GND -> GND
//    DS18B20  red  -> 3V3,  black -> GND,  yellow/white (data) -> pin below
//             + 4.7k resistor between data and 3V3 (needed!)
//                                 GPIO7           D3
//    HW-827   +  -> 3V3,  -  -> GND,  S ->     GPIO1           D0
//    SOS button  one leg -> pin, other leg -> GND
//                                 GPIO5           D8
//    Red LED (+) via 220 ohm -> pin, LED (-) -> GND
//                                 GPIO4           D10
//
//  WEAR IT: chest strap / belt, upright, then switch on and stand still for 3 s while
//  the red LED is on (the gyro learns its zero). The worker starts at the hub on the map.
//
//  BUTTON: press = SOS on / off.  If a FALL or NO MOVEMENT alarm is active, a press
//          means "I am OK" and clears it.
//  LED:    solid = ALERT from the admin   fast blink = SOS / fall alarm
//          short blink every 2 s = searching for a repeater   off = all normal
// =====================================================================

#include <WiFi.h>
#include <Wire.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "esp_random.h"
#include "driver/gpio.h"

// ------------------------- CONFIG ------------------------------------
const char* BODY_ID = "BODY-01";      // must match the "Body ESP code" on the admin page

#define USE_EXTERNAL_ANTENNA 0        // XIAO ESP32-C6 only: 1 = antenna on the u.FL socket (fit it first!)

#if CONFIG_IDF_TARGET_ESP32C6         // Seeed XIAO ESP32-C6
  #define I2C_SDA      22             // D4
  #define I2C_SCL      23             // D5
  #define DS18B20_PIN  21             // D3
  #define PULSE_PIN    0              // D0 (HW-827 analog)
  #define BUTTON_PIN   19             // D8
  #define LED_PIN      18             // D10
#else                                 // ESP32-S3
  #define I2C_SDA      8
  #define I2C_SCL      9
  #define DS18B20_PIN  7
  #define PULSE_PIN    1
  #define BUTTON_PIN   5
  #define LED_PIN      4
#endif
#define USE_HW827          1          // 1 = use the HW-827 analog pulse sensor when no MAX3010x is found

#define SEND_EVERY_MS      1000
#define LOST_MS            8000       // no beacon this long -> search channels
#define SCAN_DWELL_MS      1300       // listen this long per channel (beacons come every second)

// motion tuning (body worn on chest / belt)
#define STEP_THRESH_G      0.11f      // acceleration bump that counts as a step
#define STEP_MIN_MS        280        // fastest walking: ~3.5 steps per second
#define IMPACT_G           3.0f       // hard knock / fall impact
#define FREEFALL_G         0.40f      // below this = falling
#define FALL_TILT_DEG      55.0f      // lying down after an impact = fall
#define NOMOTION_MS        30000      // completely still this long = "no movement" alarm
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
  int16_t  tObj, tAmb;    // 0.01 C  (body probe, air)
  int16_t  ax, ay, az;    // milli-g
  int16_t  gx, gy, gz;    // 0.1 deg/s
  uint16_t flags;
  uint32_t uptime;
  uint8_t  nearRep;
  int8_t   nearRssi;
  uint16_t hum;           // 0.01 % RH (0xFFFF = none)
  uint16_t steps;         // step counter since power-on (for the admin map)
  int16_t  head;          // heading from the gyro, 0.1 deg, 0 = direction at power-on (0x7FFF = none)
  int16_t  alt;           // height from the pressure sensor, dm, relative to power-on (0x7FFF = none)
  uint8_t  hr;            // heart rate, beats per minute (0 = none)
  uint8_t  spo2;          // blood oxygen %, estimate (0 = none)
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
// heart beat finder: works on any pulse waveform (MAX3010x light, HW-827 voltage)
struct Beat {
  float sign = 1, minAmp = 20;
  float dc = 0, lp = 0, hi = 0, lo = 0;
  bool armed = false;
  uint32_t lastBeat = 0;
  uint16_t ibi[6] = {0};
  uint8_t n = 0, bpm = 0;
};
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

// ------------------------- I2C helpers --------------------------------
bool i2cPresent(uint8_t a) { Wire.beginTransmission(a); return Wire.endTransmission() == 0; }
bool wr8(uint8_t a, uint8_t reg, uint8_t v) {
  Wire.beginTransmission(a); Wire.write(reg); Wire.write(v); return Wire.endTransmission() == 0;
}
bool rdN(uint8_t a, uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(a); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(a, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}
int rd8(uint8_t a, uint8_t reg) { uint8_t v; return rdN(a, reg, &v, 1) ? v : -1; }

// ------------------------- MPU6050: motion -----------------------------
uint8_t  mpuAddr = 0;
bool     mpuOk = false;
float    gBias[3] = {0, 0, 0};              // gyro zero, deg/s
float    grav[3] = {0, 0, 1}, refUp[3] = {0, 0, 1};
float    ax_g, ay_g, az_g, gx_d, gy_d, gz_d, amag = 1;
float    heading = 0;                        // deg, clockwise seen from above, 0 = at power-on
uint16_t steps = 0;
float    stepLp = 1, stepBase = 1;
bool     stepArmed = true;
uint32_t lastStepAt = 0, lastMotionAt = 0, stillSince = 0, mpuErrAt = 0;
uint32_t freefallStart = 0, freefallAt = 0, impactAt = 0, impactFlagUntil = 0;
bool     fallActive = false, noMotion = false;
uint32_t fallSince = 0, uprightSince = 0;

bool mpuBegin() {
  for (uint8_t a : {0x68, 0x69}) {
    int who = rd8(a, 0x75);
    if (who < 0 || who == 0x00 || who == 0xFF) continue;
    mpuAddr = a;
    wr8(a, 0x6B, 0x80); delay(100);          // reset
    wr8(a, 0x6B, 0x01);                       // wake, PLL clock
    wr8(a, 0x1A, 0x03);                       // 44 Hz low-pass
    wr8(a, 0x19, 0x09);                       // 100 Hz sample rate
    wr8(a, 0x1B, 0x08);                       // gyro +-500 deg/s
    wr8(a, 0x1C, 0x10);                       // accel +-8 g
    Serial.printf("  MPU6050 at 0x%02X (WHO_AM_I 0x%02X)\n", a, who);
    return true;
  }
  return false;
}

bool mpuRead() {
  uint8_t b[14];
  if (!rdN(mpuAddr, 0x3B, b, 14)) return false;
  auto s16 = [&](int i) { return (int16_t)((b[i] << 8) | b[i + 1]); };
  ax_g = s16(0) / 4096.0f; ay_g = s16(2) / 4096.0f; az_g = s16(4) / 4096.0f;
  gx_d = s16(8) / 65.5f - gBias[0]; gy_d = s16(10) / 65.5f - gBias[1]; gz_d = s16(12) / 65.5f - gBias[2];
  amag = sqrtf(ax_g * ax_g + ay_g * ay_g + az_g * az_g);
  return true;
}

// stand still at power-on: learn the gyro zero and which way is "up" (upright)
void mpuCalibrate() {
  for (int attempt = 0; attempt < 3; attempt++) {
    float sg[3] = {0, 0, 0}, sa[3] = {0, 0, 0}, peak = 0;
    int n = 0;
    float b0[3] = {gBias[0], gBias[1], gBias[2]};
    gBias[0] = gBias[1] = gBias[2] = 0;
    uint32_t t0 = millis();
    while (millis() - t0 < 2000) {
      if (mpuRead()) {
        sg[0] += gx_d; sg[1] += gy_d; sg[2] += gz_d;
        sa[0] += ax_g; sa[1] += ay_g; sa[2] += az_g;
        peak = max(peak, fabsf(amag - 1.0f));
        n++;
      }
      delay(10);
    }
    if (n > 50 && peak < 0.15f) {
      for (int i = 0; i < 3; i++) { gBias[i] = sg[i] / n; grav[i] = refUp[i] = sa[i] / n; }
      float m = sqrtf(refUp[0] * refUp[0] + refUp[1] * refUp[1] + refUp[2] * refUp[2]);
      for (int i = 0; i < 3; i++) { refUp[i] /= m; grav[i] /= m; }
      Serial.printf("  Gyro zero learned (%.1f %.1f %.1f deg/s)\n", gBias[0], gBias[1], gBias[2]);
      return;
    }
    for (int i = 0; i < 3; i++) gBias[i] = b0[i];
    Serial.println("  Moving during calibration - keep still...");
  }
  Serial.println("  Calibration skipped (kept moving) - zero is learned later when still");
}

float tiltFromUpright() {
  float m = sqrtf(grav[0] * grav[0] + grav[1] * grav[1] + grav[2] * grav[2]);
  if (m < 0.1f) return 0;
  float d = (grav[0] * refUp[0] + grav[1] * refUp[1] + grav[2] * refUp[2]) / m;
  return acosf(constrain(d, -1.0f, 1.0f)) * 57.2958f;
}

// called 100 times a second
void motionUpdate(uint32_t now, float dt) {
  if (!mpuRead()) {
    if (now - mpuErrAt > 5000) { mpuErrAt = now; Serial.println("MPU6050 read failed"); }
    return;
  }
  // gravity direction (slow average of the accelerometer)
  float acc[3] = {ax_g, ay_g, az_g};
  for (int i = 0; i < 3; i++) grav[i] += (acc[i] - grav[i]) * 0.03f;
  float gm = sqrtf(grav[0] * grav[0] + grav[1] * grav[1] + grav[2] * grav[2]);
  float up[3] = {grav[0] / gm, grav[1] / gm, grav[2] / gm};

  // heading: rotation around the vertical axis (works whichever way the unit is mounted)
  float yawRate = gx_d * up[0] + gy_d * up[1] + gz_d * up[2];   // + = turning left (counter-clockwise)
  heading -= yawRate * dt;                                       // + = turning right (clockwise)
  if (heading > 180) heading -= 360;
  if (heading < -180) heading += 360;

  // learn the gyro zero again whenever the worker stands perfectly still (stops slow drift)
  float gyroMag = sqrtf(gx_d * gx_d + gy_d * gy_d + gz_d * gz_d);
  bool still = gyroMag < 4.0f && fabsf(amag - 1.0f) < 0.06f;
  if (still) {
    if (!stillSince) stillSince = now;
    if (now - stillSince > 1500) {
      gBias[0] += gx_d * 0.01f; gBias[1] += gy_d * 0.01f; gBias[2] += gz_d * 0.01f;
    }
  } else stillSince = 0;
  if (gyroMag > 15.0f || fabsf(amag - 1.0f) > 0.08f) lastMotionAt = now;

  // steps: each footfall is a bump in total acceleration
  stepLp += (amag - stepLp) * 0.25f;
  stepBase += (amag - stepBase) * 0.02f;
  float d = stepLp - stepBase;
  if (!stepArmed && d < 0.0f) stepArmed = true;
  if (stepArmed && d > STEP_THRESH_G && now - lastStepAt > STEP_MIN_MS && !fallActive) {
    stepArmed = false;
    lastStepAt = now;
    steps++;
  }

  // fall: free fall and/or hard impact, then lying down
  if (amag < FREEFALL_G) {
    if (!freefallStart) freefallStart = now;
    if (now - freefallStart > 80) freefallAt = now;
  } else freefallStart = 0;
  if (amag > IMPACT_G) {
    impactAt = now;
    impactFlagUntil = now + 10000;
  }
  if (!fallActive && impactAt && now - impactAt > 2000 && now - impactAt < 2100) {
    bool afterFreefall = freefallAt && impactAt - freefallAt < 1500;
    if (afterFreefall || tiltFromUpright() > FALL_TILT_DEG) {
      fallActive = true;
      fallSince = now;
      Serial.printf("\n*** FALL DETECTED (tilt %.0f deg%s) ***\n\n", tiltFromUpright(), afterFreefall ? ", free fall" : "");
    }
  }
  if (fallActive) {                                   // clears once the worker is up and moving again
    if (tiltFromUpright() < 35.0f && now - lastMotionAt < 1000) { if (!uprightSince) uprightSince = now; }
    else uprightSince = 0;
    if (uprightSince && now - uprightSince > 3000 && now - fallSince > 15000) {
      fallActive = false;
      Serial.println("Fall alarm cleared - worker is up again");
    }
  }
  bool nm = now - lastMotionAt > NOMOTION_MS;
  if (nm != noMotion) {
    noMotion = nm;
    Serial.println(nm ? "\n*** NO MOVEMENT ***\n" : "Movement again");
  }
}

// ------------------------- BMP180: height + air temperature -----------
bool     bmpOk = false;
int16_t  AC1, AC2, AC3, B1c, B2c, MB, MC, MD;
uint16_t AC4, AC5, AC6;
int32_t  bmpUT = 0;
uint8_t  bmpState = 0;
uint32_t bmpAt = 0;
float    bmpTemp = NAN, bmpP0 = 0, bmpAlt = 0;
int      bmpN = 0;
const uint8_t BMP_OSS = 3;

bool bmpBegin() {
  if (rd8(0x77, 0xD0) != 0x55) return false;
  uint8_t c[22];
  if (!rdN(0x77, 0xAA, c, 22)) return false;
  auto s = [&](int i) { return (int16_t)((c[i] << 8) | c[i + 1]); };
  AC1 = s(0); AC2 = s(2); AC3 = s(4); AC4 = (uint16_t)s(6); AC5 = (uint16_t)s(8); AC6 = (uint16_t)s(10);
  B1c = s(12); B2c = s(14); MB = s(16); MC = s(18); MD = s(20);
  Serial.println("  BMP180 at 0x77");
  return true;
}

// Bosch datasheet formulas -> temperature (C) and pressure (Pa)
void bmpCompute(int32_t UT, int32_t UP, float& tC, int32_t& pPa) {
  int32_t X1 = ((UT - (int32_t)AC6) * (int32_t)AC5) >> 15;
  int32_t X2 = ((int32_t)MC << 11) / (X1 + MD);
  int32_t B5 = X1 + X2;
  tC = ((B5 + 8) >> 4) / 10.0f;
  int32_t B6 = B5 - 4000;
  X1 = ((int32_t)B2c * ((B6 * B6) >> 12)) >> 11;
  X2 = ((int32_t)AC2 * B6) >> 11;
  int32_t X3 = X1 + X2;
  int32_t B3 = ((((int32_t)AC1 * 4 + X3) << BMP_OSS) + 2) / 4;
  X1 = ((int32_t)AC3 * B6) >> 13;
  X2 = ((int32_t)B1c * ((B6 * B6) >> 12)) >> 16;
  X3 = ((X1 + X2) + 2) >> 2;
  uint32_t B4 = ((uint32_t)AC4 * (uint32_t)(X3 + 32768)) >> 15;
  uint32_t B7 = ((uint32_t)UP - B3) * (uint32_t)(50000UL >> BMP_OSS);
  int32_t p = B7 < 0x80000000UL ? (int32_t)((B7 * 2) / B4) : (int32_t)((B7 / B4) * 2);
  X1 = (p >> 8) * (p >> 8);
  X1 = (X1 * 3038) >> 16;
  X2 = (-7357 * p) >> 16;
  pPa = p + ((X1 + X2 + 3791) >> 4);
}

// non-blocking: one reading every 100 ms
void bmpUpdate(uint32_t now) {
  if (!bmpOk) return;
  uint8_t b[3];
  switch (bmpState) {
    case 0:
      if (now - bmpAt < 100) return;
      bmpAt = now; wr8(0x77, 0xF4, 0x2E); bmpState = 1; break;           // start temperature
    case 1:
      if (now - bmpAt < 6) return;
      if (rdN(0x77, 0xF6, b, 2)) bmpUT = (b[0] << 8) | b[1];
      wr8(0x77, 0xF4, 0x34 + (BMP_OSS << 6)); bmpAt = now; bmpState = 2; break;   // start pressure
    case 2: {
      if (now - bmpAt < 27) return;
      bmpState = 0;
      if (!rdN(0x77, 0xF6, b, 3)) return;
      int32_t UP = (((int32_t)b[0] << 16) | ((int32_t)b[1] << 8) | b[2]) >> (8 - BMP_OSS);
      float t; int32_t p;
      bmpCompute(bmpUT, UP, t, p);
      if (p < 30000 || p > 120000) return;                             // bad reading
      bmpTemp = t;
      if (bmpN < 20) { bmpP0 += (p - bmpP0) / (++bmpN); return; }      // first 2 s = height zero
      float alt = 44330.0f * (1.0f - powf(p / bmpP0, 0.190295f));
      bmpAlt += (alt - bmpAlt) * 0.1f;
      break;
    }
  }
}

// ------------------------- DS18B20: body temperature --------------------
// 1-Wire done by hand (no library). Needs a 4.7k resistor from data to 3V3.
portMUX_TYPE owMux = portMUX_INITIALIZER_UNLOCKED;
bool     dsOk = false;
float    dsTemp = NAN;
uint32_t dsAt = 0, dsGood = 0;
uint8_t  dsState = 0;
const gpio_num_t OW = (gpio_num_t)DS18B20_PIN;

bool owReset() {
  gpio_set_level(OW, 0);
  delayMicroseconds(480);
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 1);
  delayMicroseconds(70);
  bool present = gpio_get_level(OW) == 0;
  portEXIT_CRITICAL(&owMux);
  delayMicroseconds(410);
  return present;
}
void owWriteBit(bool v) {
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 0);
  delayMicroseconds(v ? 6 : 60);
  gpio_set_level(OW, 1);
  delayMicroseconds(v ? 64 : 10);
  portEXIT_CRITICAL(&owMux);
}
bool owReadBit() {
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 0);
  delayMicroseconds(3);
  gpio_set_level(OW, 1);
  delayMicroseconds(10);
  bool v = gpio_get_level(OW);
  portEXIT_CRITICAL(&owMux);
  delayMicroseconds(53);
  return v;
}
void owWrite(uint8_t b) { for (int i = 0; i < 8; i++) owWriteBit(b >> i & 1); }
uint8_t owRead() { uint8_t b = 0; for (int i = 0; i < 8; i++) b |= owReadBit() << i; return b; }
uint8_t crc8(const uint8_t* d, int n) {
  uint8_t c = 0;
  while (n--) { uint8_t x = *d++; for (int i = 0; i < 8; i++) { uint8_t m = (c ^ x) & 1; c >>= 1; if (m) c ^= 0x8C; x >>= 1; } }
  return c;
}

bool dsBegin() {
  pinMode(DS18B20_PIN, OUTPUT_OPEN_DRAIN | PULLUP);    // internal pull-up helps, the 4.7k is still needed
  gpio_set_level(OW, 1);
  delay(2);
  return owReset();
}

// non-blocking: start a conversion, read it 800 ms later
void dsUpdate(uint32_t now) {
  if (!dsOk) return;
  if (dsState == 0 && now - dsAt > 200) {
    if (owReset()) { owWrite(0xCC); owWrite(0x44); dsState = 1; }
    dsAt = now;
  } else if (dsState == 1 && now - dsAt > 800) {
    dsState = 0; dsAt = now;
    uint8_t s[9];
    if (!owReset()) return;
    owWrite(0xCC); owWrite(0xBE);
    for (int i = 0; i < 9; i++) s[i] = owRead();
    if (crc8(s, 8) != s[8] || (s[0] == 0xFF && s[1] == 0xFF)) return;
    float t = (int16_t)((s[1] << 8) | s[0]) / 16.0f;
    if (t == 85.0f || t < -40 || t > 100) return;             // 85 = power-on value, not a reading
    dsTemp = t;
    dsGood = now;
  }
}

// ------------------------- heart rate -----------------------------------
uint8_t  maxType = 0;                 // 0 none, 1 MAX30100, 2 MAX30102/30105
bool     pulseAnalog = false;
Beat     beat;
float    irDc = 0, redDc = 0, irAc2 = 0, redAc2 = 0, spo2Est = 0;
bool     finger = false;
uint32_t hrAt = 0;
const uint8_t MAXA = 0x57;

void beatReset() { Beat b; b.sign = beat.sign; b.minAmp = beat.minAmp; beat = b; }

void beatAdd(float x, uint32_t now) {
  Beat& B = beat;
  if (B.dc == 0) { B.dc = x; B.hi = B.lo = 0; }
  B.dc += (x - B.dc) * 0.02f;
  float ac = (x - B.dc) * B.sign;
  B.lp += (ac - B.lp) * 0.4f;
  float range = B.hi - B.lo;
  B.hi = max(B.lp, B.hi - range * 0.01f);
  B.lo = min(B.lp, B.lo + range * 0.01f);
  range = B.hi - B.lo;
  if (!B.armed && B.lp < B.lo + range * 0.3f) B.armed = true;
  if (B.armed && B.lp > B.lo + range * 0.6f && range > B.minAmp && now - B.lastBeat > 300) {
    B.armed = false;
    uint32_t ibi = now - B.lastBeat;
    B.lastBeat = now;
    if (ibi >= 300 && ibi <= 1700) {                          // 35..200 bpm
      memmove(B.ibi, B.ibi + 1, sizeof(B.ibi) - sizeof(B.ibi[0]));
      B.ibi[5] = ibi;
      if (B.n < 6) B.n++;
      if (B.n >= 4) {                                          // median of the last beats, only if steady
        uint16_t s[6]; uint8_t k = 0;
        for (int i = 6 - B.n; i < 6; i++) s[k++] = B.ibi[i];
        for (int i = 0; i < k; i++) for (int j = i + 1; j < k; j++) if (s[j] < s[i]) { uint16_t t = s[i]; s[i] = s[j]; s[j] = t; }
        uint16_t med = s[k / 2];
        if (s[k - 1] - s[0] < med * 0.35f) B.bpm = (uint8_t)(60000UL / med);
      }
    }
  }
  if (now - B.lastBeat > 3000) { B.bpm = 0; B.n = 0; }
}

bool maxBegin() {
  int id = rd8(MAXA, 0xFF);
  if (id == 0x11) {                                           // MAX30100
    wr8(MAXA, 0x06, 0x40); delay(10);                         // reset
    wr8(MAXA, 0x02, 0); wr8(MAXA, 0x03, 0); wr8(MAXA, 0x04, 0);
    wr8(MAXA, 0x06, 0x03);                                    // SpO2 mode (red + IR)
    wr8(MAXA, 0x07, 0x40 | (0x01 << 2) | 0x03);               // hi-res, 100 samples/s, 1600 us
    wr8(MAXA, 0x09, 0x77);                                    // red 24 mA, IR 24 mA
    maxType = 1;
  } else if (id == 0x15) {                                    // MAX30102 / MAX30105
    wr8(MAXA, 0x09, 0x40); delay(10);                         // reset
    wr8(MAXA, 0x08, 0x30);                                    // average 2 samples, FIFO roll-over
    wr8(MAXA, 0x0A, 0x27);                                    // 4096 nA range, 100 samples/s, 18 bit
    wr8(MAXA, 0x0C, 0x24); wr8(MAXA, 0x0D, 0x24);             // red / IR ~7 mA
    wr8(MAXA, 0x04, 0); wr8(MAXA, 0x05, 0); wr8(MAXA, 0x06, 0);
    wr8(MAXA, 0x09, 0x03);                                    // SpO2 mode
    maxType = 2;
  } else return false;
  beat.sign = -1;                                             // more blood = less light back
  beat.minAmp = maxType == 1 ? 15 : 40;
  Serial.printf("  %s pulse oximeter at 0x57\n", maxType == 1 ? "MAX30100" : "MAX30102");
  return true;
}

void hrSample(float ir, float red, uint32_t now) {
  finger = ir > (maxType == 1 ? 6000 : 30000);
  if (!finger) { if (beat.bpm || beat.n) beatReset(); spo2Est = 0; irDc = redDc = 0; return; }
  beatAdd(ir, now);
  if (irDc == 0) { irDc = ir; redDc = red; }
  irDc += (ir - irDc) * 0.02f; redDc += (red - redDc) * 0.02f;
  float ai = ir - irDc, ar = red - redDc;
  irAc2 += (ai * ai - irAc2) * 0.05f; redAc2 += (ar * ar - redAc2) * 0.05f;
  if (beat.bpm && irAc2 > 0 && irDc > 0 && redDc > 0) {
    float R = (sqrtf(redAc2) / redDc) / (sqrtf(irAc2) / irDc);
    float s = constrain(110.0f - 25.0f * R, 70.0f, 100.0f);
    spo2Est = spo2Est ? spo2Est + (s - spo2Est) * 0.1f : s;
  }
}

void hrUpdate(uint32_t now) {
  if (maxType) {
    if (now - hrAt < 20) return;
    hrAt = now;
    uint8_t wrReg = maxType == 1 ? 0x02 : 0x04, rdReg = maxType == 1 ? 0x04 : 0x06, dataReg = maxType == 1 ? 0x05 : 0x07;
    int w = rd8(MAXA, wrReg), r = rd8(MAXA, rdReg);
    if (w < 0 || r < 0) return;
    int n = (w - r) & (maxType == 1 ? 15 : 31);
    uint8_t per = maxType == 1 ? 4 : 6;
    while (n-- > 0) {
      uint8_t b[6];
      if (!rdN(MAXA, dataReg, b, per)) return;
      float ir, red;
      if (maxType == 1) { ir = (b[0] << 8) | b[1]; red = (b[2] << 8) | b[3]; }
      else { red = (((uint32_t)b[0] << 16) | (b[1] << 8) | b[2]) & 0x3FFFF; ir = (((uint32_t)b[3] << 16) | (b[4] << 8) | b[5]) & 0x3FFFF; }
      hrSample(ir, red, now);
    }
  } else if (pulseAnalog) {
    if (now - hrAt < 20) return;                              // 50 samples per second
    hrAt = now;
    float mv = analogReadMilliVolts(PULSE_PIN);
    finger = mv > 200 && mv < 3200;                           // pin floating near 0 or stuck high = no sensor/finger
    if (finger) beatAdd(mv, now); else if (beat.bpm) beatReset();
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
    if (r.b.rep == nearRep || r.rssi > nearRssi || now - nearAt > 4000) {
      if (r.b.rep != nearRep) Serial.printf("Nearest repeater: REP-%02u (%d dBm)\n", r.b.rep, r.rssi);
      nearRep = r.b.rep; nearRssi = r.rssi; nearAt = now;
    }
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
  bool dsFresh = dsOk && dsGood && now - dsGood < 5000;
  t.tObj = dsFresh ? (int16_t)(dsTemp * 100) : 0;
  t.tAmb = !isnan(bmpTemp) ? (int16_t)(bmpTemp * 100) : t.tObj;
  if (!dsFresh) f |= BF_TEMP_FAULT;
  if (mpuOk) {
    t.ax = (int16_t)(ax_g * 1000); t.ay = (int16_t)(ay_g * 1000); t.az = (int16_t)(az_g * 1000);
    t.gx = (int16_t)(gx_d * 10); t.gy = (int16_t)(gy_d * 10); t.gz = (int16_t)(gz_d * 10);
    t.steps = steps;
    t.head = (int16_t)lroundf(heading * 10);
    if (fallActive) f |= BF_FALL;
    if (noMotion) f |= BF_NOMOTION;
    if (now < impactFlagUntil) f |= BF_IMPACT;
  } else {
    f |= BF_MPU_FAULT;
    t.head = 0x7FFF;
  }
  t.alt = bmpOk && bmpN >= 20 ? (int16_t)lroundf(bmpAlt * 10) : 0x7FFF;
  t.hum = 0xFFFF;                                            // no humidity sensor
  t.hr = beat.bpm;
  t.spo2 = beat.bpm && spo2Est ? (uint8_t)lroundf(spo2Est) : 0;
  if (sosOn) f |= BF_SOS;
  if (alertOn) f |= BF_ALERT_LED;
  t.flags = f;
  t.uptime = now / 1000;
  bool fresh = nearRep && now - nearAt < 4000;
  t.nearRep = fresh ? nearRep : 0;
  t.nearRssi = fresh ? nearRssi : -127;
  if (esp_now_send(BROADCAST, (const uint8_t*)&t, sizeof(t)) != ESP_OK) txFail++;

  char tb[8] = "-", hb[12] = "-";
  if (dsFresh) snprintf(tb, sizeof(tb), "%.1fC", dsTemp);
  if (beat.bpm) snprintf(hb, sizeof(hb), "%u bpm", beat.bpm); else if ((maxType || pulseAnalog) && !finger) strcpy(hb, "no finger");
  Serial.printf("#%lu ch%u %s REP-%02u(%d) | body %s | steps %u head %.0f tilt %.0f | h %.1fm | HR %s%s | SOS %s ALERT %s%s%s\n",
                (unsigned long)t.seq, channel, locked ? "ok" : "searching", t.nearRep, t.nearRssi, tb, steps, heading,
                mpuOk ? tiltFromUpright() : 0.0f, bmpOk ? bmpAlt : 0.0f, hb,
                t.spo2 ? (" SpO2 " + String(t.spo2) + "%").c_str() : "",
                sosOn ? "ON" : "off", alertOn ? "ON" : "off",
                fallActive ? " FALL" : "", noMotion ? " NO-MOVE" : "");
}

// press = toggle SOS (debounced); with a fall / no-movement alarm active, press = "I am OK"
bool handleButton(uint32_t now) {
  static bool stable = false, last = false;
  static uint32_t changedAt = 0;
  bool pressed = digitalRead(BUTTON_PIN) == LOW;
  if (pressed != last) { last = pressed; changedAt = now; }
  if (now - changedAt > 40 && pressed != stable) {
    stable = pressed;
    if (pressed) {
      if (fallActive || noMotion) {
        fallActive = false; noMotion = false; lastMotionAt = now; impactFlagUntil = 0;
        Serial.println("Button: worker says I AM OK - fall / no-movement alarm cleared");
      } else {
        sosOn = !sosOn;
        Serial.println(sosOn ? "\n>>> SOS SENT - admin will see DANGER <<<\n" : "SOS cancelled");
      }
      return true;
    }
  }
  return false;
}

void updateLed(uint32_t now) {
  bool on;
  if (alertOn)                     on = true;                  // admin alert: solid
  else if (sosOn || fallActive)    on = (now % 250) < 125;     // SOS / fall: fast blink
  else if (!locked)                on = (now % 2000) < 80;     // searching: short blink
  else                             on = false;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// ------------------------- setup / loop ------------------------------
void setup() {
#if defined(ARDUINO_XIAO_ESP32C6)
  // XIAO ESP32-C6 RF switch (Seeed wiki): GPIO3 LOW enables it, GPIO14 LOW = built-in, HIGH = u.FL antenna
  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);
  delay(100);
  pinMode(14, OUTPUT);
  digitalWrite(14, USE_EXTERNAL_ANTENNA ? HIGH : LOW);
#endif
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, HIGH);                                 // LED on = keep still, calibrating
  delay(1500);
  Serial.printf("\nBody node %s - finding sensors (I2C SDA GPIO%d, SCL GPIO%d)\n", BODY_ID, I2C_SDA, I2C_SCL);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  Serial.print("  I2C devices found:");
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) if (i2cPresent(a)) { Serial.printf(" 0x%02X", a); found++; }
  Serial.println(found ? "" : " none (check SDA/SCL/3V3/GND)");

  mpuOk = mpuBegin();
  if (mpuOk) mpuCalibrate(); else Serial.println("  MPU6050 NOT found -> no steps / fall detection");
  bmpOk = bmpBegin();
  if (!bmpOk) Serial.println("  BMP180 NOT found -> no height");
  dsOk = dsBegin();
  Serial.println(dsOk ? "  DS18B20 probe found" : "  DS18B20 NOT found -> no body temperature (4.7k pull-up fitted?)");
  if (!maxBegin()) {
#if USE_HW827
    analogSetPinAttenuation(PULSE_PIN, ADC_11db);
    pulseAnalog = true;
    beat.sign = 1; beat.minAmp = 25;
    Serial.printf("  No MAX3010x -> heart rate from HW-827 on GPIO%d\n", PULSE_PIN);
#else
    Serial.println("  No heart-rate sensor");
#endif
  }
  digitalWrite(LED_PIN, LOW);
  lastMotionAt = millis();

  bootId = (uint16_t)(esp_random() & 0xFFFF) | 1;
  bool ok = radioBegin();
  Serial.printf("ESP-NOW %s  button GPIO%d  LED GPIO%d%s\n", ok ? "OK" : "FAILED", BUTTON_PIN, LED_PIN,
                USE_EXTERNAL_ANTENNA ? "  external antenna" : "");
  Serial.println("Searching for a repeater...");
}

void loop() {
  static uint32_t lastSend = 0, lastMotionUs = 0;
  uint32_t now = millis();

  handleBeacons(now);
  channelSearch(now);
  uint32_t us = micros();
  if (mpuOk && us - lastMotionUs >= 10000) {                 // 100 Hz
    float dt = lastMotionUs ? (us - lastMotionUs) / 1e6f : 0.01f;
    lastMotionUs = us;
    motionUpdate(now, min(dt, 0.05f));
  }
  bmpUpdate(now);
  dsUpdate(now);
  hrUpdate(now);
  bool changed = handleButton(now);
  updateLed(now);

  if (changed || now - lastSend >= SEND_EVERY_MS) {         // every second, and at once on SOS
    lastSend = now;
    sendTelemetry(now);
  }
  delay(1);
}
