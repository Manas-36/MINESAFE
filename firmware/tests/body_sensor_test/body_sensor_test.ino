// =====================================================================
//  MineSafe - BODY UNIT SENSOR TEST (no radio, no libraries)
//  Checks every body-unit part one by one and prints live readings.
//  Run this before flashing body_node.ino.
//
//  Board : ESP32-C6-WROOM-1 DevKit  -> Tools -> Board: "ESP32C6 Dev Module"
//          (also works on the ESP32-S3 body unit and the XIAO ESP32-C6)
//          Tools -> USB CDC On Boot: "Enabled" if the cable is in the USB socket,
//                                    "Disabled" if it is in the UART/COM socket.
//          Serial Monitor 115200.
//
//  WIRING (ESP32-C6-WROOM-1 DevKit)          [ESP32-S3 body unit]
//    MPU6050  VCC 3V3, GND, SDA GPIO6, SCL GPIO7       [SDA 8, SCL 9]
//    BMP180   same 4 wires as the MPU6050 (shared I2C bus)
//    MAX3010x same 4 wires (optional)
//    DS18B20  red 3V3, black GND, yellow GPIO10       [GPIO7]
//             + 4.7k resistor between yellow and 3V3
//    HW-827   + 3V3, - GND, S GPIO2                    [GPIO4]
//    Button   GPIO18 -> button -> GND                  [GPIO5]
//    LED      GPIO19 -> 220R -> LED long leg, short leg GND   [GPIO6]
//
//  SERIAL COMMANDS: s = check all again, f = find which pins the sensors are really on,
//                   l = LED on/off, q = quiet (stop live lines)
// =====================================================================
#include <Wire.h>
#include "driver/gpio.h"
#include "esp_log.h"

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

#if CONFIG_IDF_TARGET_ESP32C6 && !defined(ARDUINO_XIAO_ESP32C6)
  #define BOARD_NAME "ESP32-C6-WROOM-1 DevKit"
  #define I2C_SDA 6
  #define I2C_SCL 7
  #define DS_PIN 10
  #define PULSE_PIN 2
  #define BUTTON_PIN 18
  #define LED_PIN 19
#elif CONFIG_IDF_TARGET_ESP32C6
  #define BOARD_NAME "XIAO ESP32-C6"
  #define I2C_SDA 22
  #define I2C_SCL 23
  #define DS_PIN 21
  #define PULSE_PIN 0
  #define BUTTON_PIN 19
  #define LED_PIN 18
#else
  #define BOARD_NAME "ESP32-S3"
  #define I2C_SDA 8
  #define I2C_SCL 9
  #define DS_PIN 7
  #define PULSE_PIN 4
  #define BUTTON_PIN 5
  #define LED_PIN 6
#endif

// ------------------------- I2C helpers ------------------------------
bool present(uint8_t a) { Wire.beginTransmission(a); return Wire.endTransmission() == 0; }
bool wr8(uint8_t a, uint8_t r, uint8_t v) { Wire.beginTransmission(a); Wire.write(r); Wire.write(v); return Wire.endTransmission() == 0; }
bool rdN(uint8_t a, uint8_t r, uint8_t* b, uint8_t n) {
  Wire.beginTransmission(a); Wire.write(r);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(a, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) b[i] = Wire.read();
  return true;
}
int rd8(uint8_t a, uint8_t r) { uint8_t v; return rdN(a, r, &v, 1) ? v : -1; }

// ------------------------- MPU6050 -----------------------------------
uint8_t mpuA = 0;
bool mpuBegin() {
  for (uint8_t a : {0x68, 0x69}) {
    int who = rd8(a, 0x75);
    if (who < 0) continue;
    mpuA = a;
    wr8(a, 0x6B, 0x00);                  // wake up
    wr8(a, 0x1C, 0x00);                  // +-2 g
    wr8(a, 0x1B, 0x00);                  // +-250 deg/s
    Serial.printf("  [PASS] MPU6050 at 0x%02X (WHO_AM_I 0x%02X%s)\n", a, who,
                  (who == 0x68 || who == 0x69) ? "" : " - clone chip, still fine");
    return true;
  }
  Serial.println("  [FAIL] MPU6050 not found -> check SDA/SCL, 3V3, GND; AD0 low = 0x68");
  return false;
}
bool mpuRead(float& ax, float& ay, float& az, float& gx, float& gy, float& gz) {
  uint8_t b[14];
  if (!rdN(mpuA, 0x3B, b, 14)) return false;
  auto s = [&](int i) { return (int16_t)(b[i] << 8 | b[i + 1]); };
  ax = s(0) / 16384.0f; ay = s(2) / 16384.0f; az = s(4) / 16384.0f;
  gx = s(8) / 131.0f;   gy = s(10) / 131.0f;  gz = s(12) / 131.0f;
  return true;
}

// ------------------------- BMP180 ------------------------------------
int16_t AC1, AC2, AC3, B1c, B2c, MB, MC, MD; uint16_t AC4, AC5, AC6;
bool bmpBegin() {
  int id = rd8(0x77, 0xD0);
  if (id != 0x55) {
    if (id == 0x58 || id == 0x60) Serial.printf("  [INFO] chip id 0x%02X at 0x77 is a BMP280/BME280, not a BMP180\n", id);
    else Serial.println("  [FAIL] BMP180 not found at 0x77");
    return false;
  }
  uint8_t c[22];
  if (!rdN(0x77, 0xAA, c, 22)) return false;
  auto s = [&](int i) { return (int16_t)((c[i] << 8) | c[i + 1]); };
  AC1 = s(0); AC2 = s(2); AC3 = s(4); AC4 = s(6); AC5 = s(8); AC6 = s(10);
  B1c = s(12); B2c = s(14); MB = s(16); MC = s(18); MD = s(20);
  Serial.println("  [PASS] BMP180 at 0x77");
  return true;
}
bool bmpRead(float& tC, float& hPa) {
  uint8_t b[3];
  if (!wr8(0x77, 0xF4, 0x2E)) return false; delay(5);
  if (!rdN(0x77, 0xF6, b, 2)) return false;
  int32_t UT = b[0] << 8 | b[1];
  if (!wr8(0x77, 0xF4, 0x34)) return false; delay(8);         // oss 0
  if (!rdN(0x77, 0xF6, b, 3)) return false;
  int32_t UP = ((b[0] << 16) | (b[1] << 8) | b[2]) >> 8;
  int32_t X1 = ((UT - AC6) * AC5) >> 15, X2 = ((int32_t)MC << 11) / (X1 + MD), B5 = X1 + X2;
  tC = ((B5 + 8) >> 4) / 10.0f;
  int32_t B6 = B5 - 4000;
  X1 = (B2c * ((B6 * B6) >> 12)) >> 11; X2 = (AC2 * B6) >> 11;
  int32_t B3 = (((int32_t)AC1 * 4 + X1 + X2) + 2) / 4;
  X1 = (AC3 * B6) >> 13; X2 = (B1c * ((B6 * B6) >> 12)) >> 16;
  int32_t X3 = ((X1 + X2) + 2) >> 2;
  uint32_t B4 = ((uint32_t)AC4 * (uint32_t)(X3 + 32768)) >> 15;
  uint32_t B7 = ((uint32_t)UP - B3) * 50000UL;
  int32_t p = B7 < 0x80000000UL ? (B7 * 2) / B4 : (B7 / B4) * 2;
  X1 = (p >> 8) * (p >> 8); X1 = (X1 * 3038) >> 16; X2 = (-7357 * p) >> 16;
  hPa = (p + ((X1 + X2 + 3791) >> 4)) / 100.0f;
  return true;
}

// ------------------------- MAX30100 / MAX30102 -----------------------
uint8_t maxType = 0;
bool maxBegin() {
  int id = rd8(0x57, 0xFF);
  if (id == 0x15) {
    wr8(0x57, 0x09, 0x40); delay(10);
    wr8(0x57, 0x08, 0x30); wr8(0x57, 0x0A, 0x27);
    wr8(0x57, 0x0C, 0x24); wr8(0x57, 0x0D, 0x24);
    wr8(0x57, 0x04, 0); wr8(0x57, 0x05, 0); wr8(0x57, 0x06, 0);
    wr8(0x57, 0x09, 0x03);
    maxType = 2;
  } else if (id == 0x11) {
    wr8(0x57, 0x06, 0x40); delay(10);
    wr8(0x57, 0x02, 0); wr8(0x57, 0x03, 0); wr8(0x57, 0x04, 0);
    wr8(0x57, 0x06, 0x03); wr8(0x57, 0x07, 0x47); wr8(0x57, 0x09, 0x77);
    maxType = 1;
  } else {
    Serial.println("  [ -- ] no MAX3010x at 0x57 (optional - the HW-827 is used instead)");
    return false;
  }
  Serial.printf("  [PASS] %s at 0x57\n", maxType == 2 ? "MAX30102" : "MAX30100");
  return true;
}
bool maxRead(uint32_t& ir, uint32_t& red) {
  uint8_t b[6];
  if (maxType == 2) {
    if (!rdN(0x57, 0x07, b, 6)) return false;
    red = ((b[0] << 16) | (b[1] << 8) | b[2]) & 0x3FFFF;
    ir  = ((b[3] << 16) | (b[4] << 8) | b[5]) & 0x3FFFF;
  } else {
    if (!rdN(0x57, 0x05, b, 4)) return false;
    ir = b[0] << 8 | b[1]; red = b[2] << 8 | b[3];
  }
  return true;
}

// ------------------------- DS18B20 (1-Wire by hand) -------------------
portMUX_TYPE owMux = portMUX_INITIALIZER_UNLOCKED;
const gpio_num_t OW = (gpio_num_t)DS_PIN;
bool owReset() {
  gpio_set_level(OW, 0); delayMicroseconds(480);
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 1); delayMicroseconds(70);
  bool p = gpio_get_level(OW) == 0;
  portEXIT_CRITICAL(&owMux);
  delayMicroseconds(410);
  return p;
}
void owWriteBit(bool v) {
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 0); delayMicroseconds(v ? 6 : 60);
  gpio_set_level(OW, 1); delayMicroseconds(v ? 64 : 10);
  portEXIT_CRITICAL(&owMux);
}
bool owReadBit() {
  portENTER_CRITICAL(&owMux);
  gpio_set_level(OW, 0); delayMicroseconds(3);
  gpio_set_level(OW, 1); delayMicroseconds(10);
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
  pinMode(DS_PIN, OUTPUT_OPEN_DRAIN | PULLUP);
  gpio_set_level(OW, 1); delay(2);
  if (owReset()) { Serial.printf("  [PASS] DS18B20 answers on GPIO%d\n", DS_PIN); return true; }
  Serial.printf("  [FAIL] DS18B20 no answer on GPIO%d -> yellow wire, 4.7k to 3V3, red 3V3, black GND\n", DS_PIN);
  return false;
}
uint32_t dsStart = 0; bool dsBusy = false; float dsTemp = NAN;
void dsTick(uint32_t now) {
  if (!dsBusy) {
    if (owReset()) { owWrite(0xCC); owWrite(0x44); dsBusy = true; dsStart = now; } else dsTemp = NAN;
  } else if (now - dsStart > 800) {
    dsBusy = false;
    uint8_t s[9];
    if (!owReset()) { dsTemp = NAN; return; }
    owWrite(0xCC); owWrite(0xBE);
    for (int i = 0; i < 9; i++) s[i] = owRead();
    if (crc8(s, 8) != s[8]) { dsTemp = NAN; return; }
    int16_t raw = s[1] << 8 | s[0];
    float t = raw / 16.0f;
    dsTemp = (t == 85.0f) ? NAN : t;   // 85.0 = power-on value, not a real reading
  }
}

// ------------------------- state -------------------------------------
bool mpuOk, bmpOk, maxOk, dsOk, ledOn, quiet;
uint16_t pMin = 4095, pMax = 0;
uint32_t pressCount = 0;
bool lastBtn = false;


// Pull-up check: a powered sensor module pulls SDA/SCL (and the DS18B20 4.7k pulls its data line)
// up to 3V3. With the ESP's weak pull-DOWN on, a connected + powered line still reads HIGH,
// a loose or unpowered line reads LOW. This tells us WHERE the wiring is broken.
bool lineHigh(int pin) {
  pinMode(pin, INPUT_PULLDOWN);
  delay(5);
  bool h = digitalRead(pin);
  pinMode(pin, INPUT);
  return h;
}
void lineCheck() {
  Wire.end();
  bool sda = lineHigh(I2C_SDA), scl = lineHigh(I2C_SCL), ds = lineHigh(DS_PIN);
  Serial.printf("Wire check (HIGH = wire reaches a powered sensor):  SDA GPIO%d %s | SCL GPIO%d %s | DS18B20 GPIO%d %s\n",
                I2C_SDA, sda ? "HIGH ok" : "LOW <- broken", I2C_SCL, scl ? "HIGH ok" : "LOW <- broken",
                DS_PIN, ds ? "HIGH ok" : "LOW <- broken");
  if (!sda && !scl && !ds)
    Serial.println("  -> ALL LOW: the sensors get no 3V3/GND (breadboard rail gap? wire on 5V/GPIO instead of 3V3?)\n"
                   "     or the wires are on other pins. Type f to search every pin for the sensors.");
  else if (!sda || !scl)
    Serial.println("  -> one I2C line LOW: that wire is loose or on the wrong pin (type f to find it)");
}

// f: try every free GPIO pair as SDA/SCL and every pin for the DS18B20, report where the parts really are
const int FREE_PINS[] =
#if CONFIG_IDF_TARGET_ESP32C6 && !defined(ARDUINO_XIAO_ESP32C6)
  {0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 15, 18, 19, 20, 21, 22, 23};
#elif CONFIG_IDF_TARGET_ESP32C6
  {0, 1, 2, 18, 19, 20, 21, 22, 23};
#else
  {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 38, 39, 40, 41, 42, 47, 48};
#endif
void findPins() {
  Serial.println("\nSearching every pin pair for I2C sensors (takes ~20 s)...");
  Wire.end();
  int hits = 0;
  for (int a : FREE_PINS) for (int b : FREE_PINS) {
    if (a == b || a == BUTTON_PIN || b == BUTTON_PIN || a == LED_PIN || b == LED_PIN) continue;
    if (!Wire.begin(a, b, 100000)) continue;
    Wire.setTimeOut(5);
    String found;
    for (uint8_t ad : {0x57, 0x68, 0x69, 0x77}) if (present(ad)) found += String(" 0x") + String(ad, HEX);
    Wire.end();
    if (found.length()) { Serial.printf("  FOUND:%s  with SDA = GPIO%d, SCL = GPIO%d\n", found.c_str(), a, b); hits++; }
  }
  if (!hits) Serial.println("  no I2C sensor on any pin pair -> the sensors are NOT POWERED (check 3V3 + GND with a meter)");
  Serial.println("Searching every pin for the DS18B20...");
  bool dsHit = false;
  for (int p : FREE_PINS) {
    if (p == BUTTON_PIN || p == LED_PIN) continue;
    pinMode(p, OUTPUT_OPEN_DRAIN | PULLUP);
    gpio_num_t g = (gpio_num_t)p;
    gpio_set_level(g, 0); delayMicroseconds(480);
    gpio_set_level(g, 1); delayMicroseconds(70);
    bool pres = gpio_get_level(g) == 0;
    delayMicroseconds(410);
    pinMode(p, INPUT);
    if (pres) { Serial.printf("  FOUND: DS18B20 answers on GPIO%d\n", p); dsHit = true; }
  }
  if (!dsHit) Serial.println("  DS18B20 not found on any pin -> check its 3V3/GND and the 4.7k resistor");
  Serial.println("Done. Move the wires to the pins in the WIRING list (or tell Claude which pins were found).\n");
  checkAll();
}

void checkAll() {
  Serial.printf("\n==== MineSafe body sensor test - %s ====\n", BOARD_NAME);
  Serial.printf("I2C SDA GPIO%d  SCL GPIO%d | DS18B20 GPIO%d | HW-827 GPIO%d | button GPIO%d | LED GPIO%d\n",
                I2C_SDA, I2C_SCL, DS_PIN, PULSE_PIN, BUTTON_PIN, LED_PIN);
  lineCheck();
  Wire.end();
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  Serial.print("I2C scan:");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) if (present(a)) {
    const char* nm = a == 0x68 || a == 0x69 ? "MPU6050" : a == 0x77 ? "BMP180" : a == 0x57 ? "MAX3010x" : "?";
    Serial.printf("  0x%02X(%s)", a, nm); n++;
  }
  Serial.println(n ? "" : "  NOTHING -> SDA/SCL swapped? 3V3 and GND connected?");
  mpuOk = mpuBegin();
  bmpOk = bmpBegin();
  maxOk = maxBegin();
  dsOk  = dsBegin();
  int mv = analogReadMilliVolts(PULSE_PIN);
  Serial.printf("  [INFO] HW-827 on GPIO%d reads %d mV now (about 1500-1700 mV at rest is normal;\n"
                "         0 mV or 3300 mV = not connected). Put a finger on it and watch 'swing'.\n", PULSE_PIN, mv);
  Serial.println("  [INFO] Press the button: 'btn' changes to DOWN. LED blinks every second (l = on/off).");
  Serial.println("Live line every second:  accel(g) | gyro(deg/s) | BMP C hPa | skin C | pulse mV swing | IR | btn\n");
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 4000) delay(10);
  delay(300);
  esp_log_level_set("i2c.master", ESP_LOG_NONE);
  esp_log_level_set("i2c", ESP_LOG_NONE);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  analogSetPinAttenuation(PULSE_PIN, ADC_11db);
  checkAll();
}

void loop() {
  static uint32_t lastLine = 0, lastPulse = 0;
  uint32_t now = millis();

  if (Serial.available()) {
    char c = Serial.read();
    if (c == 's') checkAll();
    if (c == 'f') findPins();
    if (c == 'l') { ledOn = !ledOn; Serial.printf("LED forced %s\n", ledOn ? "ON" : "blinking"); }
    if (c == 'q') { quiet = !quiet; Serial.println(quiet ? "quiet" : "live"); }
  }
  bool btn = digitalRead(BUTTON_PIN) == LOW;
  if (btn && !lastBtn) { pressCount++; Serial.printf(">> button pressed (%lu)\n", (unsigned long)pressCount); }
  lastBtn = btn;
  digitalWrite(LED_PIN, ledOn || (now / 500) % 2);

  if (now - lastPulse >= 10) {
    lastPulse = now;
    uint16_t v = analogReadMilliVolts(PULSE_PIN);
    if (v < pMin) pMin = v;
    if (v > pMax) pMax = v;
  }
  if (dsOk) dsTick(now);

  if (now - lastLine >= 1000) {
    lastLine = now;
    if (quiet) { pMin = 4095; pMax = 0; return; }
    char l[220]; int k = 0;
    float ax, ay, az, gx, gy, gz;
    if (mpuOk && mpuRead(ax, ay, az, gx, gy, gz))
      k += snprintf(l + k, sizeof(l) - k, "a %+.2f %+.2f %+.2f |g%+6.1f%+6.1f%+6.1f ", ax, ay, az, gx, gy, gz);
    else k += snprintf(l + k, sizeof(l) - k, "MPU --                                  ");
    float t, p;
    if (bmpOk && bmpRead(t, p)) k += snprintf(l + k, sizeof(l) - k, "| %.1fC %.1fhPa ", t, p);
    else k += snprintf(l + k, sizeof(l) - k, "| BMP --          ");
    if (dsOk && !isnan(dsTemp)) k += snprintf(l + k, sizeof(l) - k, "| skin %.2fC ", dsTemp);
    else k += snprintf(l + k, sizeof(l) - k, "| skin --     ");
    k += snprintf(l + k, sizeof(l) - k, "| pulse %4u-%4umV swing %3d ", pMin, pMax, pMax - pMin);
    uint32_t ir, red;
    if (maxOk && maxRead(ir, red)) k += snprintf(l + k, sizeof(l) - k, "| IR %lu ", (unsigned long)ir);
    k += snprintf(l + k, sizeof(l) - k, "| btn %s", btn ? "DOWN" : "up");
    Serial.println(l);
    pMin = 4095; pMax = 0;
  }
}
